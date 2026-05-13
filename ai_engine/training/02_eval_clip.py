import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from transformers import CLIPModel, CLIPProcessor
from dataset import MockTripletDataset, ChicFinderTripletDataset
import logging
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
        
        labels = sorted(list(set(true_labels + pred_labels)))
        cm = confusion_matrix(true_labels, pred_labels, labels=labels)
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(cm, annot=True, fmt='d', xticklabels=labels, yticklabels=labels, cmap='Blues')
        plt.xlabel('Predicted Category')
        plt.ylabel('True Category')
        plt.title(f'Confusion Matrix ({name})')
        plt.tight_layout()
        plt.savefig(f'confusion_matrix_{name.replace(" ", "_")}.png')
        plt.close()
            
    return (correct_top1 / num_queries) * 100, (correct_topk / num_queries) * 100

def evaluate_model(model_path, processor_id, dataloader, device, name="Model"):
    logger.info(f"Evaluating {name}...")
    model = CLIPModel.from_pretrained(model_path).to(device)
    anchors, positives, categories = get_embeddings(model, dataloader, device)
    top1, topk = calculate_accuracy(anchors, positives, categories, name=name)
    return top1, topk

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    # Load real validation dataset
    val_dataset = ChicFinderTripletDataset(processor)
    val_loader = DataLoader(val_dataset, batch_size=10, shuffle=False)

    # 1. Eval Base Model
    base_t1, base_tk = evaluate_model(
        "openai/clip-vit-base-patch32", 
        "openai/clip-vit-base-patch32", 
        val_loader, device, name="Base CLIP"
    )

    # 2. Eval Fine-Tuned Model
    ft_path = "models/fine_tuned_clip"
    try:
        ft_t1, ft_tk = evaluate_model(
            ft_path, 
            "openai/clip-vit-base-patch32", 
            val_loader, device, name="Fine-Tuned CLIP"
        )
    except Exception as e:
        logger.error(f"Could not find fine-tuned weights: {e}")
        return

    print("\n" + "="*30)
    print("FINAL EVALUATION RESULTS")
    print("="*30)
    print(f"Base CLIP      | Top-1: {base_t1:.2f}% | Top-5: {base_tk:.2f}%")
    print(f"Fine-Tuned     | Top-1: {ft_t1:.2f}% | Top-5: {ft_tk:.2f}%")
    print("="*30)

if __name__ == "__main__":
    main()