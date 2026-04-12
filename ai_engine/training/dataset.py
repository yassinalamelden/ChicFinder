import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np

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