"""
Fashion Retrieval Training Pipeline
====================================
Production-ready contrastive learning for fashion embeddings.

Components:
  - TrainingConfig: Hyperparameters + seed
  - DatasetBuilder: Load data, compute all weight tables
  - CompositeWeightCalculator: category x gender x (1 + 0.3 x sub), cap at 4.0
  - WeightedBatchSampler: Category-balanced (4x7=28), soft source diversity
  - PositivePairGenerator: multi-view -> augmented -> fallback
  - SubcategoryHardNegativeSampler: subcategory -> category -> global random
  - RareCategoryAugmentation: Mild transforms for Dresses, Footwear, Underwear
  - FashionNTXentLoss: Weighted NT-Xent with composite weights
  - train_epoch(): Full training loop

Weights (sqrt inverse frequency, normalized):
  - Gender: Men=1.00, Women=1.92, Kids=1.74
  - Category: varies per count (Dresses highest ~7.55)
  - Subcategory: sqrt inverse per category, avg=1.0
  - Source: sqrt inverse, soft bias only (no quotas)

Composite formula: min(category_w * gender_w * (1 + 0.3 * sub_w), 4.0)
"""

import json
import math
import random
import os
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import time
import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# ============================================================================
# 0. SEEDING
# ============================================================================

def set_seed(seed: int = 42):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    if torch.cuda.is_available():
        torch.backends.cudnn.deterministic = True


# ============================================================================
# 1. CONFIGURATION
# ============================================================================

@dataclass
class TrainingConfig:
    jsonl_path: str = 'data/metadata.jsonl'
    image_base_path: str = 'data/raw_images'

    batch_size: int = 28
    categories_per_batch: int = 4
    num_hard_negatives: int = 5

    num_epochs: int = 50
    learning_rate: float = 1e-4
    warmup_epochs: int = 5
    weight_decay: float = 1e-4

    temperature: float = 0.07
    weighting_strategy: str = 'sqrt_inverse_frequency'
    composite_cap: float = 4.0

    rare_categories: set = field(default_factory=lambda: {'Dresses', 'Footwear', 'Underwear'})
    augmentation_prob: float = 0.7

    steps_per_epoch: int = 0      # 0 = auto-compute from dataset size after load
    accumulation_steps: int = 4   # gradient accumulation → effective batch = batch_size × accumulation_steps
    log_interval: int = 5
    eval_interval: int = 5
    save_interval: int = 5

    seed: int = 42
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

    def __post_init__(self):
        assert self.batch_size % 7 == 0, f"batch_size {self.batch_size} must be divisible by 7 categories"
        self.categories_per_batch = self.batch_size // 7


# ============================================================================
# 2. DATA PREPARATION
# ============================================================================

class DatasetBuilder:
    def __init__(self, jsonl_path: str, image_base_path: str = 'data/raw_images'):
        self.jsonl_path = jsonl_path
        self.image_base_path = image_base_path

        self.category_products: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.product_metadata: Dict[str, Dict] = {}
        self.category_counts: Dict[str, int] = defaultdict(int)

        self.subcategory_products: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.all_product_ids: List[str] = []

        self.categories: List[str] = []
        self.sources: List[str] = []
        self.subcategories: Dict[str, List[str]] = {}

        self.category_weights: Dict[str, float] = {}
        self.gender_weights: Dict[str, float] = {}
        self.subcategory_weights: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.source_weights: Dict[str, float] = {}

    def load(self) -> Tuple[Dict, Dict, Dict]:
        print(f"Loading data from {self.jsonl_path}...")
        records = [json.loads(l) for l in open(self.jsonl_path, encoding='utf-8')]
        print(f"  Loaded {len(records)} records")

        for record in records:
            product_id = record['product_id']
            category = record['category']
            subcategory = record.get('subcategory', 'Unknown')
            gender = record.get('gender', 'Men')
            source = record.get('source', 'unknown')
            filename = record.get('filename')

            self.category_products[category][product_id].append(filename)
            self.category_counts[category] += 1

            self.subcategory_products[category][subcategory].append(product_id)

            if product_id not in self.product_metadata:
                self.product_metadata[product_id] = {
                    'category': category,
                    'subcategory': subcategory,
                    'gender': gender,
                    'brand': record.get('brand'),
                    'price': record.get('price'),
                    'source': source,
                    'all_images': [],
                }
                self.all_product_ids.append(product_id)

            if filename not in self.product_metadata[product_id]['all_images']:
                self.product_metadata[product_id]['all_images'].append(filename)

            if source not in self.sources:
                self.sources.append(source)

        self.category_products = {cat: dict(prods) for cat, prods in self.category_products.items()}
        self.subcategory_products = {cat: dict(subs) for cat, subs in self.subcategory_products.items()}
        self.categories = sorted(self.category_products.keys())
        self.subcategories = {cat: sorted(subs.keys()) for cat, subs in self.subcategory_products.items()}

        self._compute_all_weights()
        self._build_product_lookup()

        print(f"  Categories: {self.categories}")
        print(f"  Sources: {sorted(self.sources)}")
        print(f"  Products: {len(self.all_product_ids)}")
        return self.category_products, self.product_metadata, self.category_counts

    def _build_product_lookup(self):
        self.product_by_id = {pid: self.product_metadata[pid] for pid in self.all_product_ids}

    def _compute_all_weights(self):
        total = sum(self.category_counts.values())
        n_cats = len(self.categories)

        cat_vals = {}
        for cat in self.categories:
            freq = self.category_counts[cat] / total
            cat_vals[cat] = math.sqrt(1.0 / freq)
        avg_cat = sum(cat_vals.values()) / n_cats
        self.category_weights = {c: v / avg_cat for c, v in cat_vals.items()}

        gender_counts = Counter(
            self.product_metadata[pid]['gender']
            for pid in self.all_product_ids
        )
        gen_vals = {}
        for gen, cnt in gender_counts.items():
            freq = cnt / len(self.all_product_ids)
            gen_vals[gen] = math.sqrt(1.0 / freq)
        min_gen = min(gen_vals.values())
        self.gender_weights = {g: v / min_gen for g, v in gen_vals.items()}

        for cat in self.categories:
            cat_total = self.category_counts[cat]
            sub_products = self.subcategory_products[cat]
            sub_vals = {}
            for sub, pids in sub_products.items():
                freq = len(pids) / cat_total
                sub_vals[sub] = math.sqrt(1.0 / freq) if freq > 0 else 1.0
            avg_sub = sum(sub_vals.values()) / len(sub_vals) if sub_vals else 1.0
            if avg_sub > 0:
                self.subcategory_weights[cat] = {s: v / avg_sub for s, v in sub_vals.items()}
            else:
                self.subcategory_weights[cat] = sub_vals

        source_counts = Counter(
            self.product_metadata[pid]['source']
            for pid in self.all_product_ids
        )
        src_vals = {}
        for src, cnt in source_counts.items():
            freq = cnt / len(self.all_product_ids)
            src_vals[src] = math.sqrt(1.0 / freq)
        avg_src = sum(src_vals.values()) / len(src_vals)
        self.source_weights = {s: v / avg_src for s, v in src_vals.items()}

        print("\nCategory Weights:")
        for cat in sorted(self.category_weights.keys()):
            print(f"  {cat:<15} {self.category_weights[cat]:.4f}")

        print("\nGender Weights:")
        for gen in sorted(self.gender_weights.keys()):
            print(f"  {gen:<10} {self.gender_weights[gen]:.4f}")

        print("\nSource Weights (soft smoothing):")
        for src in sorted(self.source_weights.keys()):
            print(f"  {src:<12} {self.source_weights[src]:.4f}")

    def print_statistics(self):
        total_images = sum(self.category_counts.values())
        print("\n" + "=" * 70)
        print("DATASET STATISTICS")
        print("=" * 70)
        print(f"{'Category':<15} {'Products':<10} {'Images':<10} {'%':<8} {'Ratio':<10} {'Weight':<10}")
        print("-" * 70)

        min_count = min(self.category_counts.values())
        for cat in sorted(self.categories):
            count = self.category_counts[cat]
            num_prods = len(self.category_products[cat])
            pct = 100 * count / total_images
            ratio = count / min_count
            print(f"{cat:<15} {num_prods:<10} {count:<10} {pct:<8.1f} {ratio:<10.1f} {self.category_weights.get(cat, 0):<10.4f}")

        print("-" * 70)
        print(f"{'TOTAL':<15} {len(self.all_product_ids):<10} {total_images:<10}")
        print("=" * 70 + "\n")

        multi_prods = sum(
            1 for pid in self.all_product_ids
            if len(self.product_metadata[pid]['all_images']) >= 2
        )
        print(f"Multi-view products: {multi_prods} / {len(self.all_product_ids)}")


# ============================================================================
# 3. COMPOSITE WEIGHT CALCULATOR
# ============================================================================

class CompositeWeightCalculator:
    def __init__(self, category_weights, gender_weights, subcategory_weights, cap=4.0):
        self.cat_w = category_weights
        self.gen_w = gender_weights
        self.sub_w = subcategory_weights
        self.cap = cap

    def compute(self, category, gender, subcategory):
        cw = self.cat_w.get(category, 1.0)
        gw = self.gen_w.get(gender, 1.0)
        sw = self.sub_w.get(category, {}).get(subcategory, 1.0)
        return min(cw * gw * (1 + 0.3 * sw), self.cap)

    def compute_batch(self, batch_items):
        return [self.compute(i['category'], i['gender'], i['subcategory']) for i in batch_items]


# ============================================================================
# 4. WEIGHTED BATCH SAMPLER
# ============================================================================

class WeightedBatchSampler:
    def __init__(self, category_products, product_metadata, categories_per_batch, source_weights, batch_size):
        self.categories_per_batch = categories_per_batch
        self.batch_size = batch_size
        self.categories = sorted(category_products.keys())
        self.n_cats = len(self.categories)

        self.category_product_lists = {
            cat: list(products.keys())
            for cat, products in category_products.items()
        }

        self.source_weights = source_weights
        self.product_metadata = product_metadata

        multi = sum(1 for pid, meta in self.product_metadata.items() if len(meta['all_images']) >= 2)
        print(f"  Multi-view products: {multi} / {len(self.product_metadata)}")

    def _weighted_product_select(self, product_ids):
        weights = np.array(
            [self.source_weights.get(self.product_metadata[pid]['source'], 1.0) for pid in product_ids],
            dtype=float,
        )
        weights /= weights.sum()
        return np.random.choice(len(product_ids), p=weights)

    def __iter__(self):
        while True:
            batch = []
            used_in_batch = set()

            for category in self.categories:
                cat_products = self.category_product_lists[category]

                for _ in range(self.categories_per_batch):
                    candidates = [p for p in cat_products if p not in used_in_batch] or cat_products
                    idx = self._weighted_product_select(candidates)
                    product_id = candidates[idx]
                    used_in_batch.add(product_id)

                    meta = self.product_metadata[product_id]
                    batch.append({
                        'product_id': product_id,
                        'category': category,
                        'subcategory': meta['subcategory'],
                        'gender': meta['gender'],
                        'source': meta['source'],
                        'all_images': meta['all_images'],
                        'anchor_image': None,
                        'positive_image': None,
                    })

            if len(batch) == self.batch_size:
                yield batch

    def __len__(self):
        return 10000


# ============================================================================
# 5. POSITIVE PAIR GENERATOR
# ============================================================================

class PositivePairGenerator:
    def __init__(self, use_multi_view=True, augmentation_prob=0.7):
        self.use_multi_view = use_multi_view
        self.augmentation_prob = augmentation_prob

    def generate(self, batch_item):
        images = batch_item['all_images']
        n = len(images)

        if n >= 2 and self.use_multi_view:
            idxs = random.sample(range(n), 2)
            batch_item['anchor_image'] = images[idxs[0]]
            batch_item['positive_image'] = images[idxs[1]]
            batch_item['pair_type'] = 'multi_view'
        else:
            single = random.choice(images)
            batch_item['anchor_image'] = single
            batch_item['positive_image'] = single
            batch_item['pair_type'] = 'single_image'

        return batch_item


# ============================================================================
# 6. SUBCATEGORY HARD NEGATIVE SAMPLER
# ============================================================================

class SubcategoryHardNegativeSampler:
    def __init__(self, category_products, product_metadata, subcategory_products, source_weights, num_hard_negatives=5):
        self.category_products = category_products
        self.product_metadata = product_metadata
        self.subcategory_products = subcategory_products
        self.source_weights = source_weights
        self.num_hard_negatives = num_hard_negatives

        self.cat_product_list = {cat: list(products.keys()) for cat, products in category_products.items()}
        self.all_product_ids = list(product_metadata.keys())

    def _weighted_sample(self, candidates, exclude, num):
        valid = [p for p in candidates if p not in exclude]
        if not valid:
            return []
        weights = np.array(
            [self.source_weights.get(self.product_metadata[pid]['source'], 1.0) for pid in valid],
            dtype=float,
        )
        weights /= weights.sum()
        num = min(num, len(valid))
        indices = np.random.choice(len(valid), size=num, p=weights, replace=False)
        return [valid[i] for i in indices]

    def sample(self, anchor_product_id, category, subcategory, num_negatives=None):
        if num_negatives is None:
            num_negatives = self.num_hard_negatives

        exclude = {anchor_product_id}
        result = []

        if subcategory in self.subcategory_products.get(category, {}):
            sub_pids = self.subcategory_products[category][subcategory]
            negs = self._weighted_sample(sub_pids, exclude, num_negatives - len(result))
            result.extend(negs)
            exclude.update(negs)

        if len(result) < num_negatives:
            negs = self._weighted_sample(self.cat_product_list.get(category, []), exclude, num_negatives - len(result))
            result.extend(negs)
            exclude.update(negs)

        if len(result) < num_negatives:
            negs = self._weighted_sample(self.all_product_ids, exclude, num_negatives - len(result))
            result.extend(negs)

        while len(result) < num_negatives:
            result.append(result[0] if result else anchor_product_id)

        return result[:num_negatives]

    def sample_batch(self, batch_items, num_negatives=None):
        return [self.sample(item['product_id'], item['category'], item['subcategory'], num_negatives) for item in batch_items]


# ============================================================================
# 7. AUGMENTATION
# ============================================================================

try:
    from torchvision import transforms
    from PIL import Image
    HAS_VISION = True
except ImportError:
    HAS_VISION = False


class RareCategoryAugmentation:
    def __init__(self, rare_categories, augmentation_prob=0.7):
        self.rare_categories = rare_categories
        self.augmentation_prob = augmentation_prob

        if HAS_VISION:
            self.aug_transform = transforms.Compose([
                transforms.RandomResizedCrop(224, scale=(0.85, 1.0), ratio=(0.9, 1.1)),
                transforms.RandomHorizontalFlip(p=0.3),
                transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.05),
                transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self.std_transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])

    def apply(self, image_path, category):
        if not HAS_VISION:
            return None
        try:
            img = Image.open(image_path).convert('RGB')
        except Exception:
            return None

        if category in self.rare_categories and random.random() < self.augmentation_prob:
            return self.aug_transform(img)
        return self.std_transform(img)


# ============================================================================
# 8. LOSS FUNCTION
# ============================================================================

class FashionNTXentLoss(nn.Module):
    def __init__(self, weight_calculator, temperature=0.07):
        super().__init__()
        self.weight_calc = weight_calculator
        self.temperature = temperature

    def forward(self, anchor_emb, positive_emb, hard_neg_emb, batch_items):
        B = anchor_emb.shape[0]
        device = anchor_emb.device

        anchor_emb = F.normalize(anchor_emb, dim=1)
        positive_emb = F.normalize(positive_emb, dim=1)
        hard_neg_emb = F.normalize(hard_neg_emb, dim=-1)

        pos_logits = torch.sum(anchor_emb * positive_emb, dim=1, keepdim=True) / self.temperature
        neg_logits = torch.bmm(anchor_emb.unsqueeze(1), hard_neg_emb.transpose(1, 2)).squeeze(1) / self.temperature

        logits = torch.cat([pos_logits, neg_logits], dim=1)
        labels = torch.zeros(B, dtype=torch.long, device=device)

        loss_per_sample = F.cross_entropy(logits, labels, reduction='none')

        weights = torch.tensor(
            [self.weight_calc.compute(i['category'], i['gender'], i['subcategory']) for i in batch_items],
            dtype=torch.float32,
            device=device,
        )

        return (loss_per_sample * weights).mean()


# ============================================================================
# 9. IMAGE LOADING + TRAINING LOOP
# ============================================================================

def load_batch_images(batch_items, image_base_path, augmentation, hard_neg_sampler, pair_gen, num_hard_negatives):
    anchors, positives, batch_indices = [], [], []

    for item in batch_items:
        pair_gen.generate(item)
        anchor_t = augmentation.apply(os.path.join(image_base_path, item['anchor_image']), item['category'])
        positive_t = augmentation.apply(os.path.join(image_base_path, item['positive_image']), item['category'])

        if anchor_t is not None and positive_t is not None:
            anchors.append(anchor_t)
            positives.append(positive_t)
            batch_indices.append(item)

    if not anchors:
        return None, None, None, None

    anchors_t = torch.stack(anchors)
    positives_t = torch.stack(positives)

    negs = hard_neg_sampler.sample_batch(batch_indices, num_hard_negatives)
    hard_neg_tensors = []
    for neg_pids, item in zip(negs, batch_indices):
        tensors = []
        for pid in neg_pids:
            neg_images = hard_neg_sampler.product_metadata[pid]['all_images']
            fn = random.choice(neg_images)
            t = augmentation.apply(os.path.join(image_base_path, fn), item['category'])
            tensors.append(t if t is not None else torch.zeros(3, 224, 224))

        while len(tensors) < num_hard_negatives:
            tensors.append(tensors[0])
        hard_neg_tensors.append(torch.stack(tensors[:num_hard_negatives]))

    return anchors_t, positives_t, batch_indices, torch.stack(hard_neg_tensors)


def train_epoch(model, batch_sampler, pair_gen, hard_neg_sampler, augmentation,
                criterion, optimizer, device, epoch, config, weight_calc):
    model.train()
    total_loss = 0.0
    batch_count = 0
    weights_log = []
    use_amp = device == 'cuda'
    scaler = torch.amp.GradScaler('cuda', enabled=use_amp)

    steps = config.steps_per_epoch if config.steps_per_epoch > 0 else 300
    total_images = steps * config.batch_size
    epoch_start = time.time()
    optimizer.zero_grad()

    bar = tqdm(total=steps, desc=f"Epoch {epoch}/{config.num_epochs}", unit="batch", leave=True) if tqdm else None

    for batch_idx, batch_items in enumerate(batch_sampler):
        if batch_idx >= steps:
            break

        anchors_t, positives_t, batch_indices, hard_neg_batch = load_batch_images(
            batch_items, config.image_base_path, augmentation,
            hard_neg_sampler, pair_gen, config.num_hard_negatives,
        )
        if anchors_t is None:
            if bar:
                bar.update(1)
            continue

        anchors_t = anchors_t.to(device)
        positives_t = positives_t.to(device)
        hard_neg_batch = hard_neg_batch.to(device)

        is_accumulation_step = (batch_idx + 1) % config.accumulation_steps != 0
        if not is_accumulation_step:
            optimizer.zero_grad()

        with torch.amp.autocast(device_type='cuda', enabled=use_amp):
            anchor_emb = model(anchors_t)
            positive_emb = model(positives_t)

            B, N, C, H, W = hard_neg_batch.shape
            hard_neg_emb = model(hard_neg_batch.view(B * N, C, H, W)).view(B, N, -1)

            loss = criterion(anchor_emb, positive_emb, hard_neg_emb, batch_indices)
            loss = loss / config.accumulation_steps

        scaler.scale(loss).backward()

        if not is_accumulation_step:
            scaler.step(optimizer)
            scaler.update()

        total_loss += loss.item() * config.accumulation_steps
        batch_count += 1
        weights_log.extend([
            weight_calc.compute(i['category'], i['gender'], i['subcategory'])
            for i in batch_indices
        ])

        images_done = batch_count * config.batch_size
        avg_loss = total_loss / batch_count
        w = np.array(weights_log[-100:])

        if bar:
            bar.set_postfix(
                imgs=f"{images_done}/{total_images}",
                loss=f"{avg_loss:.4f}",
                w=f"{w.min():.2f}/{w.max():.2f}/{w.mean():.2f}",
            )
            bar.update(1)

        if batch_count % config.log_interval == 0:
            elapsed = time.time() - epoch_start
            eta_s = int(elapsed / batch_count * (steps - batch_count))
            eta = str(datetime.timedelta(seconds=eta_s))
            pct = 100.0 * images_done / total_images
            print(
                f"  [Epoch {epoch}/{config.num_epochs} | Batch {batch_count}/{steps} | "
                f"Images {images_done}/{total_images} ({pct:.1f}%) | "
                f"Loss {avg_loss:.4f} | "
                f"W min={w.min():.2f} max={w.max():.2f} mean={w.mean():.2f} | "
                f"ETA {eta}]"
            )

    if bar:
        bar.close()

    avg_loss = total_loss / batch_count if batch_count > 0 else 0.0
    stats = {}
    if weights_log:
        w = np.array(weights_log)
        stats = {'min': float(w.min()), 'max': float(w.max()), 'mean': float(w.mean())}

    return avg_loss, stats
