import os
import json
import random
import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np

class ChicFinderTripletDataset(Dataset):
    """
    A real triplet dataset using scraped data from data/raw_images.
    Groups images by product_id to form (anchor, positive, negative) triplets.
    """
    def __init__(self, processor, metadata_path="data/metadata.json", images_dir="data/raw_images"):
        self.processor = processor
        self.images_dir = images_dir

        with open(metadata_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

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
            
            # Ensure category is a string and not None
            cat = info.get("category")
            if cat is None:
                cat = "unknown"
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