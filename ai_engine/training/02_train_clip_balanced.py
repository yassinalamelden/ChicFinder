"""
CLIP + Balanced Training Pipeline
====================================
Combines the CLIP vision encoder with the balanced training strategy:
  - Category-balanced batch sampling (4 per category x 7 categories = 28)
  - Subcategory-aware hard negative mining
  - Composite loss weighting (category x gender x subcategory)
  - Selective augmentation for rare categories

Run from the project root:
    python ai_engine/training/02_train_clip_balanced.py
"""

import os
import sys
import logging
import torch
import torch.optim as optim
from transformers import CLIPModel, CLIPProcessor

sys.path.insert(0, os.path.dirname(__file__))

from balanced_training_pipeline import (
    TrainingConfig,
    DatasetBuilder,
    CompositeWeightCalculator,
    WeightedBatchSampler,
    PositivePairGenerator,
    SubcategoryHardNegativeSampler,
    RareCategoryAugmentation,
    FashionNTXentLoss,
    train_epoch,
    set_seed,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CLIPImageEncoder(torch.nn.Module):
    """Thin wrapper around CLIP's vision encoder that returns L2-normalized embeddings."""

    def __init__(self, clip_model: CLIPModel):
        super().__init__()
        self.vision_model = clip_model.vision_model
        self.visual_projection = clip_model.visual_projection

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        outputs = self.vision_model(pixel_values=pixel_values)
        pooled = outputs.pooler_output
        return self.visual_projection(pooled)


def main():
    config = TrainingConfig(
        jsonl_path='data/metadata.jsonl',
        image_base_path='data/raw_images',
        batch_size=14,
        num_epochs=20,
        learning_rate=1e-5,
        num_hard_negatives=3,
        temperature=0.1,
    )
    set_seed(config.seed)

    logger.info("=" * 70)
    logger.info("CLIP + BALANCED FASHION RETRIEVAL TRAINING")
    logger.info("=" * 70)

    # ── Data ──────────────────────────────────────────────────────────────
    builder = DatasetBuilder(config.jsonl_path, config.image_base_path)
    category_products, product_metadata, category_counts = builder.load()
    builder.print_statistics()

    config.steps_per_epoch = max(1, len(product_metadata) // config.batch_size)
    logger.info(f"Steps per epoch: {config.steps_per_epoch} ({len(product_metadata)} products / batch {config.batch_size})")

    weight_calc = CompositeWeightCalculator(
        builder.category_weights,
        builder.gender_weights,
        builder.subcategory_weights,
        cap=config.composite_cap,
    )

    batch_sampler = WeightedBatchSampler(
        category_products,
        product_metadata,
        config.categories_per_batch,
        builder.source_weights,
        config.batch_size,
    )

    pair_gen = PositivePairGenerator(use_multi_view=True, augmentation_prob=config.augmentation_prob)

    hard_neg_sampler = SubcategoryHardNegativeSampler(
        category_products,
        product_metadata,
        builder.subcategory_products,
        builder.source_weights,
        num_hard_negatives=config.num_hard_negatives,
    )

    augmentation = RareCategoryAugmentation(config.rare_categories, config.augmentation_prob)

    # ── Model ─────────────────────────────────────────────────────────────
    device = config.device
    logger.info(f"Loading CLIP on {device.upper()}...")

    clip = CLIPModel.from_pretrained("patrickjohncyh/fashion-clip")
    model = CLIPImageEncoder(clip).to(device)

    # Freeze first 9 of 12 transformer blocks — only fine-tune the last 3 + projection.
    # Cuts trainable params from ~150M to ~30M, fitting comfortably in 6GB VRAM.
    for param in model.parameters():
        param.requires_grad = False
    for i in range(9, 12):
        for param in model.vision_model.encoder.layers[i].parameters():
            param.requires_grad = True
    for param in model.visual_projection.parameters():
        param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.1f}%)")

    criterion = FashionNTXentLoss(weight_calc, temperature=config.temperature)
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # ── Training loop ──────────────────────────────────────────────────────
    os.makedirs("checkpoints", exist_ok=True)

    for epoch in range(1, config.num_epochs + 1):
        logger.info(f"\nEpoch {epoch}/{config.num_epochs}")

        avg_loss, weight_stats = train_epoch(
            model=model,
            batch_sampler=batch_sampler,
            pair_gen=pair_gen,
            hard_neg_sampler=hard_neg_sampler,
            augmentation=augmentation,
            criterion=criterion,
            optimizer=optimizer,
            device=device,
            epoch=epoch,
            config=config,
            weight_calc=weight_calc,
        )

        logger.info(f"Epoch {epoch} complete — loss: {avg_loss:.4f} | "
                    f"weights: min={weight_stats.get('min', 0):.2f} "
                    f"max={weight_stats.get('max', 0):.2f} "
                    f"mean={weight_stats.get('mean', 0):.2f}")

        if epoch % config.save_interval == 0:
            ckpt_path = f"checkpoints/clip_balanced_epoch{epoch}.pt"
            torch.save(model.state_dict(), ckpt_path)
            logger.info(f"Saved checkpoint: {ckpt_path}")

    torch.save(model.state_dict(), "checkpoints/clip_balanced_final.pt")
    logger.info("Training complete. Final model saved to checkpoints/clip_balanced_final.pt")


if __name__ == '__main__':
    main()
