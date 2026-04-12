import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from transformers import CLIPModel, CLIPProcessor
import logging
from pathlib import Path

from dataset import MockTripletDataset
from loss import InfoNCELoss

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Firing up the kitchen on device: {device.upper()}")

    # 1. Load Base Model & Processor
    model_id = "openai/clip-vit-base-patch32"
    processor = CLIPProcessor.from_pretrained(model_id)
    model = CLIPModel.from_pretrained(model_id).to(device)

    # 2. Setup Mock DataLoader (We use batch_size=8 to be safe on VRAM initially)
    train_dataset = MockTripletDataset(processor, num_samples=160)
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)

    # 3. Setup Optimizer, Loss, and AMP Scaler
    criterion = InfoNCELoss(temperature=0.07)
    optimizer = optim.AdamW(model.vision_model.parameters(), lr=1e-5, weight_decay=0.01)
    scaler = torch.amp.GradScaler(device) # The magic speed boost!

    # 4. Training Loop (Just 2 epochs to test the pipeline)
    num_epochs = 2
    model.train()

    for epoch in range(num_epochs):
        total_loss = 0.0
        
        for batch_idx, batch in enumerate(train_loader):
            optimizer.zero_grad()
            
            # Move tensors to GPU
            anchor = batch["anchor"].to(device)
            positive = batch["positive"].to(device)
            negative = batch["negative"].to(device)

            # AMP Autocast context manager for speed
            with torch.amp.autocast(device_type=device):
                # Explicitly extract the tensor (.pooler_output) and project it
                anchor_out = model.vision_model(pixel_values=anchor)
                anchor_emb = model.visual_projection(anchor_out.pooler_output)
                
                pos_out = model.vision_model(pixel_values=positive)
                pos_emb = model.visual_projection(pos_out.pooler_output)
                
                neg_out = model.vision_model(pixel_values=negative)
                neg_emb = model.visual_projection(neg_out.pooler_output)

                # Now these are raw tensors, and the loss function will accept them!
                loss = criterion(anchor_emb, pos_emb, neg_emb)

            # Scale loss and backpropagate
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()

            if (batch_idx + 1) % 5 == 0:
                logger.info(f"Epoch {epoch+1}/{num_epochs} | Batch {batch_idx+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

        logger.info(f"--- Epoch {epoch+1} Complete | Avg Loss: {(total_loss / len(train_loader)):.4f} ---")

    # 5. Save the weights for Amr to use in FAISS!
    output_dir = "models/fine_tuned_clip"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    processor.save_pretrained(output_dir)
    logger.info(f"Success! Model weights saved to {output_dir}")

if __name__ == "__main__":
    main()