import json
import re
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://mobaco.com"
API = f"{BASE_URL}/wp-json/wc/store/v1"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
CATEGORIES = ["men", "women", "junior-boys", "junior-girls"]




def now():
    return datetime.now(timezone.utc).isoformat()


def strip(value):
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", text).strip()


def get_price(raw):
    if raw is None:
        return None
    text = re.sub(r"[^\d.]", "", str(raw))
    try:
        p = float(text)
        return p / 100 if p > 500000 else p
    except:
        return None


def get_categories():
    cats = {}
    r = requests.get(f"{API}/products/categories", params={"per_page": 100}, headers=HEADERS, timeout=20)
    if r.ok:
        for c in r.json():
            print(c["slug"]) 
            cats[c["slug"]] = c["id"]
    return cats


def main():
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    output = "data/raw/mobaco.jsonl"
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Getting categories...")
    cats = get_categories()
    records = []
    seen = set()

    for slug in CATEGORIES:
        cat_id = cats.get(slug)
        if not cat_id:
            print(f"  Skipping '{slug}' - not found")
            continue
        print(f"\nScraping: {slug}")
        page = 1
        while True:
            r = session.get(f"{API}/products", params={"category": cat_id, "per_page": 100, "page": page}, timeout=30)
            if not r.ok:
                break
            products = r.json()
            if not products:
                break
            for p in products:
                pid = str(p.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                title = strip(p.get("name"))
                if not title:
                    continue
                url = p.get("permalink", "")
                images = [i["src"] for i in (p.get("images") or []) if i.get("src")]
                if not images:
                    continue
                prices = p.get("prices", {})
                price = get_price(prices.get("price") or prices.get("regular_price"))
                stock = p.get("is_in_stock")
                availability = "InStock" if stock else "OutOfStock"
                pcats = p.get("categories") or []
                category = pcats[0]["name"] if pcats else slug
                subcategory = pcats[-1]["name"] if len(pcats) > 1 else None
                rec = {
                    "source": "mobaco",
                    "product_id": pid,
                    "title": title,
                    "brand": "Mobaco",
                    "category": category,
                    "subcategory": subcategory,
                    "price": price,
                    "availability": availability,
                    "image_urls": images,
                    "product_url": url,
                    "description": strip(p.get("short_description")) or None,
                    "scraped_at": now(),
                }
                records.append(rec)
                print(f"  [{len(records)}] {title}")
            if len(products) < 100:
                break
            page += 1
            time.sleep(0.3)

    with open(output, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(records)} products -> {output}")



if __name__ == "__main__":
    main()
