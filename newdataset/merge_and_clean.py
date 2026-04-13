import csv
import json
import re
from pathlib import Path

INPUT_FILES = [
    "data/raw/mobaco.jsonl",
    "data/raw/townteam.jsonl",
    "data/raw/tomato.jsonl",
]

CSV_OUTPUT  = "data/clean/all_products.csv"
JSONL_OUTPUT = "data/clean/all_products.jsonl"

FIELDS = [
    "source", "product_id", "title", "brand",
    "category", "subcategory", "price", "availability",
    "image_urls", "product_url", "description", "scraped_at",
]


def strip(value):
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", text).strip()


def is_english(text):
    text = strip(text)
    if not text:
        return False
    if any("\u0600" <= ch <= "\u06ff" for ch in text):
        return False
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    return sum(ord(ch) < 128 for ch in letters) / len(letters) >= 0.7


def main():
    Path("data/clean").mkdir(parents=True, exist_ok=True)

    all_records = []
    for path_str in INPUT_FILES:
        path = Path(path_str)
        if not path.exists():
            print(f"WARNING: {path} not found - did you run that scraper?")
            continue
        count = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_records.append(json.loads(line))
                    count += 1
        print(f"Loaded {count} records from {path}")

    # Clean & filter
    cleaned = []
    seen_urls = set()
    for r in all_records:
        title = strip(r.get("title"))
        url   = strip(r.get("product_url"))
        pid   = strip(r.get("product_id"))

        if not title or not url or not pid:
            continue
        if not is_english(title):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Fix images to a plain string list
        imgs = r.get("image_urls") or []
        if isinstance(imgs, str):
            try:
                imgs = json.loads(imgs)
            except:
                imgs = [imgs]
        imgs = [strip(i) for i in imgs if strip(i)]
        if not imgs:
            continue

        desc  = strip(r.get("description"))
        brand = strip(r.get("brand"))
        if desc  and not is_english(desc):  desc  = ""
        if brand and not is_english(brand): brand = ""

        cleaned.append({
            "source":      strip(r.get("source")),
            "product_id":  pid,
            "title":       title,
            "brand":       brand or "",
            "category":    strip(r.get("category")),
            "subcategory": strip(r.get("subcategory")),
            "price":       r.get("price"),
            "availability":strip(r.get("availability")),
            "image_urls":  imgs,
            "product_url": url,
            "description": desc,
            "scraped_at":  strip(r.get("scraped_at")),
        })

    print(f"\nTotal after cleaning: {len(cleaned)} products")

    # Write CSV
    with open(CSV_OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in cleaned:
            row = dict(r)
            row["image_urls"] = json.dumps(r["image_urls"], ensure_ascii=False)
            writer.writerow(row)

    # Write JSONL
    with open(JSONL_OUTPUT, "w", encoding="utf-8") as f:
        for r in cleaned:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"CSV  saved → {CSV_OUTPUT}")
    print(f"JSONL saved → {JSONL_OUTPUT}")

    from collections import Counter
    counts = Counter(r["source"] for r in cleaned)
    print("\nProducts per source:")
    for src, n in sorted(counts.items()):
        print(f"  {src:12s}  {n}")


if __name__ == "__main__":
    main()
