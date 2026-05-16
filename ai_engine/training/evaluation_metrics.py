"""
Evaluation Metrics for Fashion Retrieval Pipeline
==================================================

Classes:
  - RetrievalEvaluator: Recall@K, NDCG@K, MAP@K per category and gender×category
  - EmbeddingSpaceAnalyzer: Intra/inter distances, silhouette, variance
  - TrainingTracker: Loss curves, per-epoch metrics, baseline comparison
  - BatchAnalyzer: Verify batch balance, source coverage, weight stats
"""

import json
import numpy as np
import torch
import torch.nn.functional as F
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional


# ============================================================================
# 1. RETRIEVAL EVALUATOR
# ============================================================================

class RetrievalEvaluator:
    def __init__(self, categories: List[str], genders: List[str]):
        self.categories = categories
        self.genders = genders

    def compute_recall_at_k(self, query_emb, gallery_emb, query_labels, gallery_labels, k=10):
        similarities = torch.mm(
            F.normalize(query_emb, dim=1),
            F.normalize(gallery_emb, dim=1).t(),
        )
        top_k = torch.argsort(similarities, dim=1, descending=True)[:, :k]

        recall = {}
        for cat in self.categories:
            q_idx = [i for i, l in enumerate(query_labels) if l == cat]
            if not q_idx:
                continue

            hits = 0
            for qi in q_idx:
                gallery_cats = [gallery_labels[i] for i in top_k[qi].tolist()]
                hits += cat in gallery_cats

            recall[cat] = hits / len(q_idx)

        return recall

    def compute_ndcg_at_k(self, query_emb, gallery_emb, query_labels, gallery_labels, k=10):
        similarities = torch.mm(
            F.normalize(query_emb, dim=1),
            F.normalize(gallery_emb, dim=1).t(),
        )
        top_k = torch.argsort(similarities, dim=1, descending=True)[:, :k]

        ndcg = {}
        for cat in self.categories:
            q_idx = [i for i, l in enumerate(query_labels) if l == cat]
            if not q_idx:
                continue

            dcg_sum = 0.0
            for qi in q_idx:
                rels = [1 if gallery_labels[i] == cat else 0 for i in top_k[qi].tolist()]
                dcg = sum((2 ** r - 1) / np.log2(i + 2) for i, r in enumerate(rels))
                dcg_sum += dcg

            idcg = sum((2 ** 1 - 1) / np.log2(i + 2) for i in range(min(k, sum(1 for l in gallery_labels if l == cat))))
            ndcg[cat] = (dcg_sum / len(q_idx)) / idcg if idcg > 0 else 0.0

        return ndcg

    def compute_map_at_k(self, query_emb, gallery_emb, query_labels, gallery_labels, k=10):
        similarities = torch.mm(
            F.normalize(query_emb, dim=1),
            F.normalize(gallery_emb, dim=1).t(),
        )
        top_k = torch.argsort(similarities, dim=1, descending=True)[:, :k]

        ap_sum = 0.0
        for i, label in enumerate(query_labels):
            ranked = [gallery_labels[j] for j in top_k[i].tolist()]
            hits = 0
            precision_sum = 0.0
            for rank, rel_label in enumerate(ranked):
                if rel_label == label:
                    hits += 1
                    precision_sum += hits / (rank + 1)
            ap_sum += precision_sum / hits if hits > 0 else 0.0

        return {'map@' + str(k): ap_sum / len(query_labels)}

    def evaluate_all(
        self,
        model,
        image_paths: List[str],
        labels: List[str],
        device: str = 'cpu',
    ) -> Dict:
        model.eval()
        embeddings = []

        with torch.no_grad():
            for path in image_paths:
                try:
                    from PIL import Image
                    img = Image.open(path).convert('RGB')
                    from torchvision import transforms
                    t = transforms.Compose([
                        transforms.Resize((224, 224)),
                        transforms.ToTensor(),
                        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                    ])
                    tensor = t(img).unsqueeze(0).to(device)
                    emb = model(tensor).cpu()
                    embeddings.append(emb)
                except Exception:
                    embeddings.append(torch.zeros(1, 512))

        embeddings = torch.cat(embeddings, dim=0)

        results = {
            'recall@1': self.compute_recall_at_k(embeddings, embeddings, labels, labels, k=1),
            'recall@5': self.compute_recall_at_k(embeddings, embeddings, labels, labels, k=5),
            'recall@10': self.compute_recall_at_k(embeddings, embeddings, labels, labels, k=10),
            'ndcg@10': self.compute_ndcg_at_k(embeddings, embeddings, labels, labels, k=10),
            'map@10': self.compute_map_at_k(embeddings, embeddings, labels, labels, k=10),
        }

        return results

    def gender_category_recall(
        self,
        embeddings: torch.Tensor,
        labels_cat: List[str],
        labels_gen: List[str],
        k: int = 10,
    ) -> Dict[str, float]:
        sims = torch.mm(
            F.normalize(embeddings, dim=1),
            F.normalize(embeddings, dim=1).t(),
        )
        top_k = torch.argsort(sims, dim=1, descending=True)[:, :k]

        results = defaultdict(float)
        counts = defaultdict(int)

        for i in range(len(labels_cat)):
            cat, gen = labels_cat[i], labels_gen[i]
            ranked = [labels_cat[j] for j in top_k[i].tolist()]
            key = f'{cat}_{gen}'
            results[key] += cat in ranked
            counts[key] += 1

        return {k: v / counts[k] for k, v in results.items()}


# ============================================================================
# 2. EMBEDDING SPACE ANALYZER
# ============================================================================

class EmbeddingSpaceAnalyzer:
    def __init__(self, categories: List[str]):
        self.categories = categories

    def intra_category_distances(self, embeddings: torch.Tensor, labels: List[str]) -> Dict[str, float]:
        emb_norm = F.normalize(embeddings, dim=1)
        dists = 1 - torch.mm(emb_norm, emb_norm.t())

        results = {}
        for cat in self.categories:
            idx = [i for i, l in enumerate(labels) if l == cat]
            if len(idx) < 2:
                results[cat] = 0.0
                continue

            cat_dists = dists[idx][:, idx].clone()
            np.fill_diagonal(cat_dists.numpy(), 0)
            results[cat] = cat_dists.sum().item() / (len(idx) * (len(idx) - 1))

        return results

    def inter_category_distances(self, embeddings: torch.Tensor, labels: List[str]) -> Dict[Tuple[str, str], float]:
        emb_norm = F.normalize(embeddings, dim=1)
        dists = 1 - torch.mm(emb_norm, emb_norm.t())

        results = {}
        cat_idx = {cat: [i for i, l in enumerate(labels) if l == cat] for cat in self.categories}

        for i, cat1 in enumerate(self.categories):
            for cat2 in self.categories[i + 1:]:
                idx1, idx2 = cat_idx[cat1], cat_idx[cat2]
                if not idx1 or not idx2:
                    continue
                results[(cat1, cat2)] = dists[idx1][:, idx2].mean().item()

        return results

    def silhouette_score(self, embeddings: torch.Tensor, labels: List[str]) -> float:
        emb_norm = F.normalize(embeddings, dim=1)
        n = emb_norm.shape[0]
        dists = 1 - torch.mm(emb_norm, emb_norm.t())

        label_to_idx = defaultdict(list)
        for i, l in enumerate(labels):
            label_to_idx[l].append(i)

        scores = []
        for i in range(n):
            li = labels[i]
            same = label_to_idx[li]
            a = sum(dists[i, j].item() for j in same if j != i) / max(len(same) - 1, 1)

            b = float('inf')
            for cat, idxs in label_to_idx.items():
                if cat == li:
                    continue
                b_cat = sum(dists[i, j].item() for j in idxs) / max(len(idxs), 1)
                b = min(b, b_cat)

            s = (b - a) / max(a, b, 1e-8)
            scores.append(s)

        return float(np.mean(scores))

    def embedding_variance(self, embeddings: torch.Tensor, labels: List[str]) -> Dict[str, float]:
        emb_norm = F.normalize(embeddings, dim=1)
        results = {}
        for cat in self.categories:
            idx = [i for i, l in enumerate(labels) if l == cat]
            if not idx:
                results[cat] = 0.0
                continue
            results[cat] = emb_norm[idx].var(dim=0).mean().item()
        return results


# ============================================================================
# 3. TRAINING TRACKER
# ============================================================================

class TrainingTracker:
    def __init__(self, categories: List[str]):
        self.categories = categories
        self.loss_history = []
        self.composite_weight_history = []
        self.retrieval_history = []

    def log_epoch(self, epoch: int, loss: float, composite_stats: Dict, retrieval_metrics: Optional[Dict] = None):
        self.loss_history.append({'epoch': epoch, 'loss': loss})
        self.composite_weight_history.append(composite_stats)
        if retrieval_metrics:
            self.retrieval_history.append({'epoch': epoch, **retrieval_metrics})

    def get_best_epoch(self, metric='recall@5') -> int:
        if not self.retrieval_history:
            return 0
        best_epoch, best_val = 0, -1
        for record in self.retrieval_history:
            vals = [v for k, v in record.items() if k.startswith(metric)]
            if vals:
                avg = np.mean(list(vals[0].values()) if isinstance(vals[0], dict) else vals)
                if avg > best_val:
                    best_val, best_epoch = avg, record['epoch']
        return best_epoch

    def generate_comparison_report(self, baseline_metrics: Dict, proposed_metrics: Dict) -> str:
        lines = ["=" * 70, "RETRIEVAL QUALITY: BASE FashionCLIP vs FINE-TUNED", "=" * 70]

        for metric_name in ['recall@1', 'recall@5', 'recall@10']:
            lines.append(f"\n{metric_name.upper()}:")
            lines.append(f"{'Category':<15} {'Base':>10} {'Fine-Tuned':>12} {'Change':>10}")
            lines.append("-" * 52)

            baseline = baseline_metrics.get(metric_name, {})
            proposed = proposed_metrics.get(metric_name, {})

            for cat in self.categories:
                b = baseline.get(cat, 0.0)
                p = proposed.get(cat, 0.0)
                ch = ((p - b) / max(b, 0.001)) * 100
                sign = '+' if ch >= 0 else ''
                lines.append(f"{cat:<15} {b:>10.4f} {p:>12.4f} {sign}{ch:>9.1f}%")

            b_avg = np.mean(list(baseline.values())) if baseline else 0
            p_avg = np.mean(list(proposed.values())) if proposed else 0
            ch = ((p_avg - b_avg) / max(b_avg, 0.001)) * 100
            sign = '+' if ch >= 0 else ''
            lines.append(f"{'AVG':<15} {b_avg:>10.4f} {p_avg:>12.4f} {sign}{ch:>9.1f}%")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


# ============================================================================
# 4. BATCH ANALYZER
# ============================================================================

class BatchAnalyzer:
    def __init__(self):
        self.history = []

    def analyze_batch(self, batch_items: List[Dict]) -> Dict:
        cat_dist = Counter(item['category'] for item in batch_items)
        src_dist = Counter(item['source'] for item in batch_items)
        gen_dist = Counter(item['gender'] for item in batch_items)
        product_ids = [item['product_id'] for item in batch_items]
        multi_view_count = sum(1 for item in batch_items if len(item['all_images']) >= 2)
        rare_src_rate = sum(
            1 for src in src_dist.elements() if src in ['y', 'defacto', 'asili']
        ) / len(batch_items)

        return {
            'size': len(batch_items),
            'categories': dict(cat_dist),
            'sources': dict(src_dist),
            'genders': dict(gen_dist),
            'unique_products': len(set(product_ids)),
            'repeated_products': len(product_ids) - len(set(product_ids)),
            'multi_view_count': multi_view_count,
            'num_sources': len(src_dist),
            'rare_source_rate': rare_src_rate,
        }

    def detect_issues(self, epoch_stats: Dict) -> List[str]:
        issues = []
        if epoch_stats['avg_sources_per_batch'] < 2:
            issues.append(f"WARNING: Only {epoch_stats['avg_sources_per_batch']:.1f} sources/batch — may collapse")
        if epoch_stats['avg_repeated_products'] > 0.5:
            issues.append(f"WARNING: {epoch_stats['avg_repeated_products']:.1f} repeated products/batch")
        if not epoch_stats['all_categories_covered']:
            issues.append("ERROR: Not all 7 categories covered in epoch")
        return issues


if __name__ == '__main__':
    print("Evaluation metrics module loaded.")
    print("Classes: RetrievalEvaluator, EmbeddingSpaceAnalyzer, TrainingTracker, BatchAnalyzer")
