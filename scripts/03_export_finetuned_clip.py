"""
scripts/03_export_finetuned_clip.py

Merges the fine-tuned CLIPImageEncoder checkpoint back into the full CLIPModel
and saves it in HuggingFace format so encoder.py can load it from models/fine_tuned_clip/.

Usage:
    python scripts/03_export_finetuned_clip.py
    python scripts/03_export_finetuned_clip.py --checkpoint checkpoints/clip_balanced_epoch15.pt
"""

import argparse
import logging
from pathlib import Path

import torch
from transformers import CLIPModel, CLIPProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("export_finetuned_clip")

BASE_MODEL = "patrickjohncyh/fashion-clip"
DEFAULT_CHECKPOINT = "checkpoints/clip_balanced_final.pt"
OUTPUT_DIR = "models/fine_tuned_clip"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", default=OUTPUT_DIR)
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    logger.info("Loading base model: %s", BASE_MODEL)
    clip = CLIPModel.from_pretrained(BASE_MODEL)
    processor = CLIPProcessor.from_pretrained(BASE_MODEL)

    logger.info("Loading checkpoint: %s", ckpt_path)
    state_dict = torch.load(ckpt_path, map_location="cpu")

    # CLIPImageEncoder stores vision_model.* and visual_projection.*
    # These map directly onto CLIPModel's keys — strict=False skips text encoder keys
    missing, unexpected = clip.load_state_dict(state_dict, strict=False)
    logger.info("Keys loaded: %d | Missing (text encoder, expected): %d | Unexpected: %d",
                len(state_dict), len(missing), len(unexpected))
    if unexpected:
        logger.warning("Unexpected keys: %s", unexpected)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    clip.save_pretrained(out)
    processor.save_pretrained(out)
    logger.info("Saved fine-tuned model to: %s", out)


if __name__ == "__main__":
    main()
