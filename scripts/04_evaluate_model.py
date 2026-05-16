"""
scripts/04_evaluate_model.py

Evaluates and compares base FashionCLIP vs the fine-tuned model.

Metrics (per category):
  Recall@1, Recall@5, Recall@10, NDCG@10, MAP@10
  Silhouette score, intra/inter-category distances

Usage:
    python scripts/04_evaluate_model.py
    python scripts/04_evaluate_model.py --samples 150 --output eval_results.json
"""

import argparse
import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path
from pathlib import Path

import torch
from transformers import CLIPModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ai_engine" / "training"))

from evaluation_metrics import RetrievalEvaluator, EmbeddingSpaceAnalyzer, TrainingTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("evaluate_model")

BASE_MODEL      = "patrickjohncyh/fashion-clip"
FINETUNED_PATH  = ROOT / "models" / "fine_tuned_clip"
METADATA_PATH   = ROOT / "data" / "metadata.json"
IMAGES_DIR      = ROOT / "data" / "raw_images"
CATEGORIES      = ["Tops", "Bottoms", "Dresses", "Footwear", "Outerwear", "Accessories", "Underwear"]
GENDERS         = ["Men", "Women", "Kids", "Unisex"]


# ── Model wrapper ─────────────────────────────────────────────────────────────

class CLIPImageEncoder(torch.nn.Module):
    def __init__(self, clip_model: CLIPModel):
        super().__init__()
        self.vision_model = clip_model.vision_model
        self.visual_projection = clip_model.visual_projection

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        outputs = self.vision_model(pixel_values=pixel_values)
        return self.visual_projection(outputs.pooler_output)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_eval_sample(metadata_path: Path, images_dir: Path, samples_per_category: int,
                     seed: int = 42, originals_only: bool = True):
    random.seed(seed)
    with open(metadata_path, encoding="utf-8") as f:
        metadata = json.load(f)

    skipped_aug = 0
    by_category = defaultdict(list)
    for key, item in metadata.items():
        cat = item.get("category", "")
        if cat not in CATEGORIES:
            continue
        # Exclude augmented images from evaluation — they're derived from training data
        if originals_only and "_aug" in key:
            skipped_aug += 1
            continue
        img_path = images_dir / item["filename"]
        if img_path.exists():
            by_category[cat].append((str(img_path), cat, item.get("gender", "Unknown")))

    if originals_only and skipped_aug:
        logger.info("Excluded %d augmented images (evaluating on originals only)", skipped_aug)

    image_paths, cat_labels, gen_labels = [], [], []
    for cat in CATEGORIES:
        pool = by_category[cat]
        chosen = random.sample(pool, min(samples_per_category, len(pool)))
        for path, c, g in chosen:
            image_paths.append(path)
            cat_labels.append(c)
            gen_labels.append(g)

    logger.info("Eval sample: %d images across %d categories", len(image_paths), len(by_category))
    for cat in CATEGORIES:
        n = sum(1 for l in cat_labels if l == cat)
        logger.info("  %-15s %d images", cat, n)

    return image_paths, cat_labels, gen_labels


# ── Evaluation ────────────────────────────────────────────────────────────────

def load_encoder(model_path: str, device: str) -> CLIPImageEncoder:
    logger.info("Loading model: %s", model_path)
    clip = CLIPModel.from_pretrained(model_path)
    model = CLIPImageEncoder(clip).to(device)
    model.eval()
    return model


def run_evaluation(model, image_paths, cat_labels, gen_labels, device, categories):
    evaluator = RetrievalEvaluator(categories=categories, genders=GENDERS)
    metrics = evaluator.evaluate_all(model, image_paths, cat_labels, device=device)

    # Gender×category recall
    from tqdm import tqdm
    import torch.nn.functional as F
    from torchvision import transforms

    t = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    from PIL import Image
    embeddings = []
    with torch.no_grad():
        for path in tqdm(image_paths, desc="  Embedding", leave=False):
            try:
                img = Image.open(path).convert("RGB")
                tensor = t(img).unsqueeze(0).to(device)
                emb = model(tensor).cpu()
            except Exception:
                emb = torch.zeros(1, 512)
            embeddings.append(emb)
    embeddings = torch.cat(embeddings, dim=0)

    metrics["gender_category_recall@10"] = evaluator.gender_category_recall(
        embeddings, cat_labels, gen_labels, k=10
    )

    # Embedding space analysis
    analyzer = EmbeddingSpaceAnalyzer(categories=categories)
    metrics["silhouette"] = analyzer.silhouette_score(embeddings, cat_labels)
    metrics["intra_distances"] = analyzer.intra_category_distances(embeddings, cat_labels)
    metrics["embedding_variance"] = analyzer.embedding_variance(embeddings, cat_labels)

    return metrics, embeddings


# ── Confusion matrix ──────────────────────────────────────────────────────────

def plot_confusion_matrix(embeddings: torch.Tensor, labels: list, categories: list,
                          title: str, output_path: str):
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import torch.nn.functional as F
    except ImportError:
        logger.warning("pip install matplotlib to generate confusion matrices")
        return

    emb_norm = F.normalize(embeddings, dim=1)
    sims = torch.mm(emb_norm, emb_norm.t())

    # Exclude self-match by setting diagonal to -1
    sims.fill_diagonal_(-1.0)

    top1_indices = sims.argmax(dim=1).tolist()
    true_labels  = labels
    pred_labels  = [labels[i] for i in top1_indices]

    # Build matrix
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    n_cats = len(categories)
    matrix = np.zeros((n_cats, n_cats), dtype=int)
    for true, pred in zip(true_labels, pred_labels):
        if true in cat_to_idx and pred in cat_to_idx:
            matrix[cat_to_idx[true]][cat_to_idx[pred]] += 1

    # Normalise rows to percentages
    row_sums = matrix.sum(axis=1, keepdims=True)
    matrix_pct = np.where(row_sums > 0, matrix / row_sums * 100, 0)

    _, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix_pct, interpolation="nearest", cmap="Blues", vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label="% of queries")

    ax.set_xticks(range(n_cats))
    ax.set_yticks(range(n_cats))
    ax.set_xticklabels(categories, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(categories, fontsize=10)
    ax.set_xlabel("Retrieved Category (Top-1)", fontsize=12)
    ax.set_ylabel("Query Category (True)", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

    for i in range(n_cats):
        for j in range(n_cats):
            val = matrix_pct[i, j]
            color = "white" if val > 55 else "black"
            ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold" if i == j else "normal")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Confusion matrix saved to %s", output_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100,
                        help="Images per category to evaluate (default: 100)")
    parser.add_argument("--output", type=str, default="eval_results.json",
                        help="Path to save JSON results")
    parser.add_argument("--include-augmented", action="store_true",
                        help="Include augmented images in evaluation (not recommended — biases results)")
    parser.add_argument("--confusion-matrix", action="store_true",
                        help="Generate confusion matrix PNG files for both models")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Device: %s", device)

    originals_only = not args.include_augmented
    if originals_only:
        logger.info("Evaluating on ORIGINAL images only (augmented excluded)")
    else:
        logger.info("Evaluating on ALL images including augmented")

    image_paths, cat_labels, gen_labels = load_eval_sample(
        METADATA_PATH, IMAGES_DIR, args.samples, originals_only=originals_only
    )

    # ── Base model ────────────────────────────────────────────────────────────
    logger.info("\n--- Evaluating BASE FashionCLIP ---")
    base_model = load_encoder(BASE_MODEL, device)
    base_metrics, base_emb = run_evaluation(
        base_model, image_paths, cat_labels, gen_labels, device, CATEGORIES
    )
    del base_model
    if device == "cuda":
        torch.cuda.empty_cache()

    # ── Fine-tuned model ──────────────────────────────────────────────────────
    if not FINETUNED_PATH.exists():
        logger.error("Fine-tuned model not found at %s — run scripts/03_export_finetuned_clip.py first", FINETUNED_PATH)
        sys.exit(1)

    logger.info("\n--- Evaluating FINE-TUNED model ---")
    ft_model = load_encoder(str(FINETUNED_PATH), device)
    ft_metrics, ft_emb = run_evaluation(
        ft_model, image_paths, cat_labels, gen_labels, device, CATEGORIES
    )
    del ft_model
    if device == "cuda":
        torch.cuda.empty_cache()

    # ── Comparison report ─────────────────────────────────────────────────────
    tracker = TrainingTracker(categories=CATEGORIES)
    print("\n" + tracker.generate_comparison_report(base_metrics, ft_metrics))

    print("\nEMBEDDING SPACE (Fine-Tuned):")
    print(f"  Silhouette score : {ft_metrics['silhouette']:.4f}  (base: {base_metrics['silhouette']:.4f})  [higher = better separated]")
    print("\n  Intra-category distances (lower = tighter clusters):")
    for cat in CATEGORIES:
        b = base_metrics["intra_distances"].get(cat, 0)
        f = ft_metrics["intra_distances"].get(cat, 0)
        print(f"    {cat:<15} base={b:.4f}  fine-tuned={f:.4f}")

    print("\nMAP@10:")
    print(f"  Base      : {base_metrics['map@10'].get('map@10', 0):.4f}")
    print(f"  Fine-Tuned: {ft_metrics['map@10'].get('map@10', 0):.4f}")

    # ── Confusion matrices ────────────────────────────────────────────────────
    if args.confusion_matrix:
        logger.info("\nGenerating confusion matrices...")
        plot_confusion_matrix(base_emb, cat_labels, CATEGORIES,
                              title="Confusion Matrix — Base FashionCLIP (Top-1 Retrieval)",
                              output_path="confusion_matrix_base.png")
        plot_confusion_matrix(ft_emb, cat_labels, CATEGORIES,
                              title="Confusion Matrix — Fine-Tuned Model (Top-1 Retrieval)",
                              output_path="confusion_matrix_finetuned.png")

    # ── Save JSON ─────────────────────────────────────────────────────────────
    results = {"base": base_metrics, "fine_tuned": ft_metrics}
    for split in results.values():
        split.pop("gender_category_recall@10", None)  # not JSON-serialisable keys
        split.pop("intra_distances", None)
        split.pop("embedding_variance", None)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to %s", args.output)


if __name__ == "__main__":
    main()
