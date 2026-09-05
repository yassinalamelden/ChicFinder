import os
import json
import random
import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np

def _load_metadata(metadata_path):
    """
    Loads either shape used in this repo:
      - metadata.json: dict keyed by filename stem -> record
      - *_metadata.jsonl (e.g. data/train_metadata.jsonl,
        data/validation_metadata.jsonl -- the product-level, brand x
        gender stratified split): one JSON record per line, each with
        a "filename" field.
    Returns the dict-keyed-by-filename-stem shape either way, since
    that's what the rest of this class expects.
    """
    if str(metadata_path).endswith(".jsonl"):
        metadata = {}
        with open(metadata_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                filename = rec.get("filename")
                if filename:
                    metadata[os.path.splitext(filename)[0]] = rec
        return metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


class ChicFinderTripletDataset(Dataset):
    """
    A real triplet dataset using scraped data. Groups images by
    product_id to form (anchor, positive, negative) triplets.

    metadata_path can be data/metadata.json (dict, whole dataset) or
    one of the train/validation split manifests (data/train_metadata.jsonl,
    data/validation_metadata.jsonl) -- pass the matching images_dir
    (data/train or data/validation) so training and validation never
    draw from overlapping images.
    """
    def __init__(self, processor, metadata_path="data/train_metadata.jsonl", images_dir="data/train"):
        self.processor = processor
        self.images_dir = images_dir

        self.metadata = _load_metadata(metadata_path)

        # Group images by product_id
        self.product_to_images = {}
        self.filename_to_category = {}
        for image_id, info in self.metadata.items():
            pid = info.get("product_id")
            if pid is None:
                continue
            if pid not in self.product_to_images:
                self.product_to_images[pid] = []
            self.product_to_images[pid].append(info["filename"])
            
            # Normalize category casing/whitespace -- the raw per-brand
            # taxonomy has the same real category spelled differently
            # ("Set"/"sets"/"Sets", "Shirts"/"shirts") purely from string
            # formatting, not a real distinction. This doesn't unify
            # genuinely different labels ("Tops" vs "T-Shirts") -- that's
            # the separate, bigger taxonomy-unification task -- it just
            # stops casing/whitespace from fragmenting one category into
            # several confusion-matrix rows.
            cat = info.get("category")
            cat = cat.strip().title() if cat and cat.strip() else "Unknown"
            self.filename_to_category[info["filename"]] = cat

        # Filter products with at least 2 images for Anchor/Positive pairs
        self.valid_products = [pid for pid, imgs in self.product_to_images.items() if len(imgs) >= 2]

    def __len__(self):
        return len(self.valid_products)

    def _load_image(self, filename):
        path = os.path.join(self.images_dir, filename)
        return Image.open(path).convert("RGB")

    def __getitem__(self, idx):
        try:
            anchor_pid = self.valid_products[idx]

            # Sample Anchor and Positive from the same product
            anchor_fn, positive_fn = random.sample(self.product_to_images[anchor_pid], 2)

            # Sample Negative from a different product
            negative_pid = random.choice(self.valid_products)
            while negative_pid == anchor_pid:
                negative_pid = random.choice(self.valid_products)

            negative_fn = random.choice(self.product_to_images[negative_pid])

            anchor_img = self._load_image(anchor_fn)
            pos_img = self._load_image(positive_fn)
            neg_img = self._load_image(negative_fn)

            anchor_pt = self.processor(images=anchor_img, return_tensors="pt")["pixel_values"].squeeze(0)
            pos_pt = self.processor(images=pos_img, return_tensors="pt")["pixel_values"].squeeze(0)
            neg_pt = self.processor(images=neg_img, return_tensors="pt")["pixel_values"].squeeze(0)

            return {
                "anchor": anchor_pt,
                "positive": pos_pt,
                "negative": neg_pt,
                "anchor_category": self.filename_to_category.get(anchor_fn, "unknown")
            }
        except Exception:
            return self.__getitem__((idx + 1) % len(self))

class MockTripletDataset(Dataset):
    """
    A dummy dataset that generates random images so Yassin can test 
    the training pipeline before Barawy finishes scraping the real data.
    """
    def __init__(self, processor, num_samples=100):
        self.processor = processor
        self.num_samples = num_samples

    def __len__(self):
        return self.num_samples

    def _generate_random_image(self):
        # Generates a random 224x224 RGB image
        random_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        return Image.fromarray(random_array)

    def __getitem__(self, idx):
        # Generate 3 random images to act as Anchor, Positive, and Negative
        anchor_img = self._generate_random_image()
        pos_img = self._generate_random_image()
        neg_img = self._generate_random_image()

        # Process them using Hugging Face's CLIP processor
        anchor_pt = self.processor(images=anchor_img, return_tensors="pt")["pixel_values"].squeeze(0)
        pos_pt = self.processor(images=pos_img, return_tensors="pt")["pixel_values"].squeeze(0)
        neg_pt = self.processor(images=neg_img, return_tensors="pt")["pixel_values"].squeeze(0)

        return {
            "anchor": anchor_pt,
            "positive": pos_pt,
            "negative": neg_pt
        }