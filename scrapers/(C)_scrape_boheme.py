import json
import re
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://www.bohemeshop.net"
API = f"{BASE_URL}/products.json"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
GENDER_TAGS = {"men", "kids", "boys", "girls", "unisex", "women", "special sizes"}


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
    try:
        return float(str(raw).replace(",", ""))
    except:
        return None


def main():
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    output = "data/raw/boheme.jsonl"
    session = requests.Session()
    session.headers.update(HEADERS)

    print("Fetching BOHEME products...")
    all_products = []
    page = 1

    while True:
        r = session.get(API, params={"limit": 250, "page": page}, timeout=30)
        if not r.ok:
            print(f"  HTTP {r.status_code} - stopping")
            break
        batch = r.json().get("products", [])
        if not batch:
            break
        all_products.extend(batch)
        print(f"  Got {len(all_products)} products so far...")
        page += 1
        time.sleep(0.5)

    records = []
    seen = set()

    for p in all_products:
        pid = str(p.get("id", ""))
        if pid in seen:
            continue
        seen.add(pid)

        title = strip(p.get("title"))
        if not title:
            continue

        handle = p.get("handle", "")
        url_p = f"{BASE_URL}/products/{handle}" if handle else ""
        if not url_p:
            continue

        images = [strip(i.get("src")) for i in (p.get("images") or []) if i.get("src")]
        if not images:
            continue

        variants = p.get("variants") or []
        price = None
        availability = "OutOfStock"
        for v in variants:
            if price is None:
                price = get_price(v.get("price"))
            if v.get("available"):
                availability = "InStock"

        tags = [strip(t) for t in (p.get("tags") or []) if strip(t)]
        category = strip(p.get("product_type")) or (tags[0] if tags else None)
        sub_tags = [t for t in tags if t.lower() not in GENDER_TAGS]
        subcategory = sub_tags[0] if sub_tags else None

        rec = {
            "source": "boheme",
            "product_id": pid,
            "title": title,
            "brand": strip(p.get("vendor")) or "BOHEME",
            "category": category,
            "subcategory": subcategory,
            "price": price,
            "availability": availability,
            "image_urls": images,
            "product_url": url_p,
            "description": strip(p.get("body_html")) or None,
            "scraped_at": now(),
        }
        records.append(rec)
        print(f"  [{len(records)}] {title}")

    with open(output, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(records)} products -> {output}")


if __name__ == "__main__":
    main()
