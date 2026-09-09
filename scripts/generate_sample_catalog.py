#!/usr/bin/env python3
"""
Generates a sample catalog for local development.

The real catalog lives in RDS and S3 (see commit bea05a5, which removed the
tracked products.json and stores.json). That is right for production but leaves
a laptop with nothing to render, so the Stores tab, store detail and the whole
saved-items flow look broken when they are only empty.

This writes throwaway sample data so those screens can be exercised offline:

  stores.json            5 stores, at the project root where api/main.py reads it
  products.json          ~45 products, likewise
  data/raw_images/*.png  a placeholder image per product, served by the /images mount

Run from the project root:

    python3 scripts/generate_sample_catalog.py

Nothing here is real merchandise. Brand names are placeholders standing in for
Egyptian retailers, prices are invented, and the images are flat colour tiles
with the product name on them. Do not ship this data or mistake it for the
catalog. It exists so the UI has something to draw.

Both output files are already in .gitignore, so this stays local.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "data" / "raw_images"

# Deterministic, so a rerun does not churn the files.
random.seed(1310)

STORES = [
    {
        "id": "tomato",
        "name": "Tomato",
        "description": "Everyday basics and smart casual pieces.",
        "website_url": "https://example.com/tomato",
        "location": "Cairo Festival City, Cairo",
        "categories": ["tops", "bottoms", "outerwear"],
    },
    {
        "id": "dice",
        "name": "Dice",
        "description": "Streetwear and denim for men and women.",
        "website_url": "https://example.com/dice",
        "location": "City Stars, Nasr City",
        "categories": ["tops", "bottoms", "shoes"],
    },
    {
        "id": "town-team",
        "name": "Town Team",
        "description": "Relaxed fits, heavy on knitwear.",
        "website_url": "https://example.com/town-team",
        "location": "San Stefano Mall, Alexandria",
        "categories": ["tops", "outerwear"],
    },
    {
        "id": "concrete",
        "name": "Concrete",
        "description": "Tailored menswear and workwear staples.",
        "website_url": "https://example.com/concrete",
        "location": "Mall of Arabia, 6th of October",
        "categories": ["tops", "bottoms", "outerwear", "shoes"],
    },
    {
        "id": "ravin",
        "name": "Ravin",
        "description": "Occasion wear and statement pieces.",
        "website_url": "https://example.com/ravin",
        "location": "Point 90 Mall, New Cairo",
        "categories": ["tops", "bottoms"],
    },
]

# category -> (product types, colour palette for the placeholder tile)
CATALOG = {
    "tops": (
        ["Oxford Shirt", "Cotton Tee", "Linen Shirt", "Polo", "Knit Sweater", "Hoodie"],
        [(58, 76, 110), (140, 90, 70), (72, 96, 78), (120, 60, 80), (90, 90, 100)],
    ),
    "bottoms": (
        ["Slim Jeans", "Chinos", "Cargo Pants", "Tailored Trousers", "Denim Shorts"],
        [(45, 55, 80), (110, 95, 70), (70, 75, 65), (50, 50, 55)],
    ),
    "outerwear": (
        ["Denim Jacket", "Bomber Jacket", "Overcoat", "Puffer", "Trench"],
        [(60, 65, 85), (85, 70, 60), (55, 60, 58), (100, 75, 85)],
    ),
    "shoes": (
        ["Leather Sneakers", "Chelsea Boots", "Runners", "Loafers"],
        [(70, 60, 55), (45, 45, 50), (95, 85, 75)],
    ),
}

COLOR_NAMES = ["Navy", "Rust", "Olive", "Charcoal", "Cream", "Burgundy", "Stone", "Black"]
SIZES = ["XS", "S", "M", "L", "XL"]


def _placeholder_image(path: Path, label: str, rgb: tuple[int, int, int]) -> None:
    """Writes a flat colour tile with the product name, at product-card ratio."""
    width, height = 600, 800
    img = Image.new("RGB", (width, height), rgb)
    draw = ImageDraw.Draw(img)

    # A lighter band behind the text so it stays readable on any tile colour.
    draw.rectangle([0, height - 150, width, height], fill=tuple(min(c + 30, 255) for c in rgb))

    words, lines, current = label.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > 18:
            lines.append(current)
            current = word
        else:
            current = candidate
    lines.append(current)

    y = height - 125
    for line in lines[:3]:
        draw.text((28, y), line, fill=(255, 255, 255))
        y += 22

    img.save(path, "PNG")


def main() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    products = []
    for store in STORES:
        for category in store["categories"]:
            types, palette = CATALOG[category]
            for product_type in random.sample(types, k=min(3, len(types))):
                color = random.choice(COLOR_NAMES)
                product_id = (
                    f"{store['id']}-{category}-{product_type.lower().replace(' ', '-')}"
                )
                filename = f"{product_id}.png"

                _placeholder_image(
                    IMAGES_DIR / filename,
                    f"{store['name']} {product_type}",
                    random.choice(palette),
                )

                products.append(
                    {
                        "id": product_id,
                        "name": f"{color} {product_type}",
                        "brand": store["name"],
                        "category": category,
                        "type": product_type.lower(),
                        "color": color.lower(),
                        "price_egp": random.choice([349, 449, 599, 749, 899, 1199, 1499]),
                        "sizes": random.sample(SIZES, k=random.randint(2, 5)),
                        "image_url": filename,
                        "product_url": f"{store['website_url']}/{product_id}",
                        "description": f"Sample {product_type.lower()} from {store['name']}.",
                        "store_id": store["id"],
                        "store_location": store["location"],
                    }
                )

    stores_out = [{**s, "logo_url": None} for s in STORES]

    (ROOT / "stores.json").write_text(json.dumps(stores_out, indent=2) + "\n")
    (ROOT / "products.json").write_text(json.dumps(products, indent=2) + "\n")

    print(f"stores.json         {len(stores_out)} stores")
    print(f"products.json       {len(products)} products")
    print(f"data/raw_images/    {len(products)} placeholder images")
    print("\nSample data only. Restart the API to load it.")


if __name__ == "__main__":
    main()
