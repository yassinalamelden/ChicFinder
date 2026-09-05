import json
import logging
import sys
import time
from pathlib import Path

import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from transformers import CLIPModel, CLIPProcessor

from dataset import ChicFinderTripletDataset
from loss import InfoNCELoss

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Same base model as production (ai_engine/embeddings/encoder.py) -- fine-tune
# FashionCLIP itself (already pre-trained on ~700k fashion images), not
# generic CLIP. Fine-tuning generic CLIP would throw that head start away
# and hand encoder.py a model in a different feature space than it expects.
MODEL_ID = "patrickjohncyh/fashion-clip"
OUTPUT_DIR = "models/fine_tuned_clip"
NUM_EPOCHS = 15
BATCH_SIZE = 8
LOG_PATH = "models/training_log.json"


def build_loaders(processor, batch_size):
    train_dataset = ChicFinderTripletDataset(
        processor, metadata_path="data/train_metadata.jsonl", images_dir="data/train"
    )
    val_dataset = ChicFinderTripletDataset(
        processor, metadata_path="data/validation_metadata.jsonl", images_dir="data/validation"
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    logger.info(f"Train products (with >=2 images): {len(train_dataset)} | "
                f"Validation products: {len(val_dataset)}")
    return train_loader, val_loader


def embed(model, batch, device):
    anchor = batch["anchor"].to(device)
    positive = batch["positive"].to(device)
    negative = batch["negative"].to(device)

    anchor_emb = model.visual_projection(model.vision_model(pixel_values=anchor).pooler_output)
    pos_emb = model.visual_projection(model.vision_model(pixel_values=positive).pooler_output)
    neg_emb = model.visual_projection(model.vision_model(pixel_values=negative).pooler_output)
    return anchor_emb, pos_emb, neg_emb


def run_validation(model, val_loader, criterion, device):
    model.eval()
    total_loss = 0.0
    n_batches = 0
    with torch.no_grad():
        for batch in val_loader:
            anchor_emb, pos_emb, neg_emb = embed(model, batch, device)
            loss = criterion(anchor_emb, pos_emb, neg_emb)
            total_loss += loss.item()
            n_batches += 1
    model.train()
    return total_loss / max(n_batches, 1)


def train_one_run(device, num_epochs, batch_size):
    """Runs the full training loop on `device`. Raises on CUDA OOM so the
    caller can fall back to CPU with a fresh model/optimizer (a model that
    OOM'd mid-backward can have corrupted grad state -- safer to restart
    clean than try to resume the same run on a different device)."""
    logger.info(f"Loading {MODEL_ID} on {device.upper()}...")
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID).to(device)

    train_loader, val_loader = build_loaders(processor, batch_size)

    criterion = InfoNCELoss(temperature=0.07)
    optimizer = optim.AdamW(model.vision_model.parameters(), lr=1e-5, weight_decay=0.01)

    use_amp = device == "cuda"
    scaler = torch.amp.GradScaler(device, enabled=use_amp)

    history = []
    best_val_loss = float("inf")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    model.train()

    for epoch in range(num_epochs):
        epoch_start = time.time()
        total_loss = 0.0

        for batch_idx, batch in enumerate(train_loader):
            optimizer.zero_grad()

            with torch.amp.autocast(device_type=device, enabled=use_amp):
                anchor_emb, pos_emb, neg_emb = embed(model, batch, device)
                loss = criterion(anchor_emb, pos_emb, neg_emb)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()

            if (batch_idx + 1) % 20 == 0:
                logger.info(f"Epoch {epoch+1}/{num_epochs} | Batch {batch_idx+1}/{len(train_loader)} "
                            f"| Loss: {loss.item():.4f}")

        train_loss = total_loss / max(len(train_loader), 1)
        val_loss = run_validation(model, val_loader, criterion, device)
        elapsed = time.time() - epoch_start

        logger.info(f"--- Epoch {epoch+1}/{num_epochs} | Train loss: {train_loss:.4f} | "
                    f"Val loss: {val_loss:.4f} | {elapsed/60:.1f} min ---")
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss,
                         "minutes": round(elapsed / 60, 2), "device": device})

        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_pretrained(OUTPUT_DIR)
            processor.save_pretrained(OUTPUT_DIR)
            logger.info(f"New best val loss ({val_loss:.4f}) -- saved checkpoint to {OUTPUT_DIR}")

    return best_val_loss


def main():
    num_epochs = NUM_EPOCHS
    batch_size = BATCH_SIZE

    if torch.cuda.is_available():
        try:
            logger.info("Attempting GPU training...")
            best = train_one_run("cuda", num_epochs, batch_size)
            logger.info(f"Done on GPU. Best val loss: {best:.4f}")
            return
        except torch.cuda.OutOfMemoryError as e:
            logger.warning(f"CUDA OOM ({e}) -- falling back to CPU with a fresh model/optimizer.")
            torch.cuda.empty_cache()
        except RuntimeError as e:
            if "out of memory" not in str(e).lower():
                raise
            logger.warning(f"CUDA OOM ({e}) -- falling back to CPU with a fresh model/optimizer.")
            torch.cuda.empty_cache()
    else:
        logger.info("No CUDA device available -- training on CPU.")

    best = train_one_run("cpu", num_epochs, batch_size)
    logger.info(f"Done on CPU. Best val loss: {best:.4f}")


if __name__ == "__main__":
    main()
