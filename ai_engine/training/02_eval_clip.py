import logging
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import CLIPModel, CLIPProcessor
from dataset import ChicFinderTripletDataset
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_embeddings(model, dataloader, device):
    """Extracts embeddings for anchors and positives."""
    model.eval()
    anchors_list = []
    positives_list = []
    categories_list = []
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Extracting Embeddings", leave=False):
            anchor = batch["anchor"].to(device)
            positive = batch["positive"].to(device)
            if "anchor_category" in batch:
                categories_list.extend(batch["anchor_category"])
            
            # Extract and project
            a_out = model.vision_model(pixel_values=anchor).pooler_output
            p_out = model.vision_model(pixel_values=positive).pooler_output
            
            anchors_list.append(model.visual_projection(a_out))
            positives_list.append(model.visual_projection(p_out))
            
    return torch.cat(anchors_list), torch.cat(positives_list), categories_list

CM_OUTPUT_DIR = Path("models/eval_plots")
CM_TOP_N_CATEGORIES = 20  # more than this and per-cell labels become unreadable


def plot_confusion_matrix(true_labels, pred_labels, name):
    """
    Row-normalized (% of each true category) confusion matrix, restricted
    to the CM_TOP_N_CATEGORIES most frequent true categories -- the raw
    taxonomy has ~80 labels (see (C) DATASET-PLAN.md's still-open category
    fragmentation gap), which is unreadable in one matrix regardless of
    figure size. Categories are pre-normalized for casing/whitespace in
    dataset.py, but distinct labels for the same real category ("Tops" vs
    "T-Shirts") are NOT merged here -- that's the separate taxonomy
    unification task, not something to silently paper over in a plot.
    """
    top_categories = [c for c, _ in Counter(true_labels).most_common(CM_TOP_N_CATEGORIES)]
    top_set = set(top_categories)

    # Queries whose true category didn't make the cutoff are dropped from
    # the plot (not from the reported top-1/top-5 accuracy) rather than
    # bucketed into a misleading "Other" that would mix unrelated items.
    pairs = [(t, p) for t, p in zip(true_labels, pred_labels) if t in top_set]
    if not pairs:
        logger.warning(f"No categories with enough samples to plot for {name}; skipping confusion matrix.")
        return
    filtered_true, filtered_pred = zip(*pairs)
    # Predictions landing outside the top-N categories are still a real
    # outcome -- show them as one explicit column rather than dropping them,
    # which would silently inflate apparent accuracy.
    labels = top_categories + ["(other)"]
    pred_for_cm = [p if p in top_set else "(other)" for p in filtered_pred]

    cm = confusion_matrix(filtered_true, pred_for_cm, labels=labels)
    row_totals = cm.sum(axis=1, keepdims=True)
    cm_pct = np.divide(cm, row_totals, out=np.zeros_like(cm, dtype=float), where=row_totals != 0) * 100

    n = len(labels)
    fig_size = max(10, n * 0.6)
    plt.figure(figsize=(fig_size, fig_size * 0.85))
    # Blank annotations for near-zero cells instead of printing "0"
    # everywhere -- that's what made the previous version unreadable.
    annot = np.where(cm_pct >= 1, np.round(cm_pct).astype(int).astype(str), "")
    sns.heatmap(cm_pct, annot=annot, fmt='', xticklabels=labels, yticklabels=labels,
                cmap='Blues', vmin=0, vmax=100, cbar_kws={"label": "% of true category"},
                linewidths=0.5, linecolor="#eeeeee", annot_kws={"size": 9})
    plt.xlabel('Predicted Category')
    plt.ylabel('True Category')
    plt.title(f'Confusion Matrix ({name}) -- top {CM_TOP_N_CATEGORIES} categories by volume, row-normalized %')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()

    CM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CM_OUTPUT_DIR / f"confusion_matrix_{name.replace(' ', '_')}.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info(f"Saved confusion matrix -> {out_path}")


def calculate_accuracy(queries, gallery, categories=None, top_k=5, name="Model"):
    """Calculates how often the correct positive is in the top-K results."""
    # Normalize for cosine similarity
    queries = F.normalize(queries, dim=-1)
    gallery = F.normalize(gallery, dim=-1)

    # Compute similarity matrix (Queries x Gallery)
    # Correct match for query[i] is gallery[i]
    sim_matrix = torch.mm(queries, gallery.T)

    # Get top-k indices
    _, indices = sim_matrix.topk(top_k, dim=-1)

    # Check if the correct index (i) is in the top-k for each query i
    correct_top1 = 0
    correct_topk = 0
    num_queries = queries.size(0)

    for i in range(num_queries):
        if i == indices[i, 0]:
            correct_top1 += 1
        if i in indices[i]:
            correct_topk += 1

    if categories and len(categories) == num_queries:
        pred_indices = indices[:, 0].cpu().numpy()
        true_labels = [categories[i] for i in range(num_queries)]
        pred_labels = [categories[idx] for idx in pred_indices]
        plot_confusion_matrix(true_labels, pred_labels, name)

    return (correct_top1 / num_queries) * 100, (correct_topk / num_queries) * 100

def evaluate_model(model_path, processor_id, dataloader, device, name="Model"):
    logger.info(f"Evaluating {name}...")
    model = CLIPModel.from_pretrained(model_path).to(device)
    anchors, positives, categories = get_embeddings(model, dataloader, device)
    top1, topk = calculate_accuracy(anchors, positives, categories, name=name)
    return top1, topk

BASE_MODEL_ID = "patrickjohncyh/fashion-clip"


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained(BASE_MODEL_ID)

    # Held-out validation split only -- never the training images
    # (data/train_metadata.jsonl / data/train), otherwise this measures
    # memorization, not generalization.
    val_dataset = ChicFinderTripletDataset(
        processor, metadata_path="data/validation_metadata.jsonl", images_dir="data/validation"
    )
    val_loader = DataLoader(val_dataset, batch_size=10, shuffle=False)

    # 1. Eval Base Model (FashionCLIP, unfine-tuned -- the actual baseline
    # production would fall back to if this fine-tune underperforms it)
    base_t1, base_tk = evaluate_model(
        BASE_MODEL_ID,
        BASE_MODEL_ID,
        val_loader, device, name="Base FashionCLIP"
    )

    # 2. Eval Fine-Tuned Model
    ft_path = "models/fine_tuned_clip"
    try:
        ft_t1, ft_tk = evaluate_model(
            ft_path,
            BASE_MODEL_ID,
            val_loader, device, name="Fine-Tuned FashionCLIP"
        )
    except Exception as e:
        logger.error(f"Could not find fine-tuned weights: {e}")
        return

    print("\n" + "="*30)
    print("FINAL EVALUATION RESULTS")
    print("="*30)
    print(f"Base FashionCLIP     | Top-1: {base_t1:.2f}% | Top-5: {base_tk:.2f}%")
    print(f"Fine-Tuned           | Top-1: {ft_t1:.2f}% | Top-5: {ft_tk:.2f}%")
    print("="*30)

if __name__ == "__main__":
    main()