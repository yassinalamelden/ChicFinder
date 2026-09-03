import json
import re
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "https://psychonlinestore.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

# Only collections with a reliable, clean gender signal -- Vega/Denjoe-style
# genuinely-unisex collections are deliberately excluded (no reliable
# per-product gender to tag them with, same policy as the 324 ungendered
# OR records we dropped).
GENDERED_COLLECTIONS = {
    "parachute-pants": "Men",       # MEN BOTTOMS
    "men-denim-collection": "Men",
    "men-jackets-1": "Men",         # MEN JACKETS
    "men-knitwear": "Men",
    "men-summer-sets": "Men",
    "women-bottoms": "Women",
    "denim-collection": "Women",    # WOMEN DENIM COLLECTION
    "men-jackets": "Women",         # WOMEN JACKETS (site's own handle typo)
    "women-1": "Women",             # WOMEN KNITWEAR
    "summer-knitwear": "Women",     # WOMEN SUMMER SETS
    "cropped-tops": "Women",        # WOMEN TOPS
}


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
    output = "data/raw/psych.jsonl"
    session = requests.Session()
    session.headers.update(HEADERS)

    records = []
    seen = set()

    for handle, gender in GENDERED_COLLECTIONS.items():
        url = f"{BASE_URL}/collections/{handle}/products.json"
        print(f"Fetching collection '{handle}' ({gender})...")
        page = 1
        while True:
            r = session.get(url, params={"limit": 250, "page": page}, timeout=30)
            if not r.ok:
                print(f"  HTTP {r.status_code} - stopping")
                break
            batch = r.json().get("products", [])
            if not batch:
                break
            for p in batch:
                pid = str(p.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)

                title = strip(p.get("title"))
                if not title:
                    continue
                handle_p = p.get("handle", "")
                url_p = f"{BASE_URL}/products/{handle_p}" if handle_p else ""
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

                rec = {
                    "source": "psych",
                    "product_id": pid,
                    "title": title,
                    "brand": strip(p.get("vendor")) or "PSYCH",
                    "category": category,
                    "subcategory": tags[0] if tags else None,
                    "gender": gender,
                    "price": price,
                    "availability": availability,
                    "image_urls": images,
                    "product_url": url_p,
                    "description": strip(p.get("body_html")) or None,
                    "scraped_at": now(),
                }
                records.append(rec)
                print(f"  [{len(records)}] {title} ({gender})")
            if len(batch) < 250:
                break
            page += 1
            time.sleep(0.3)
        time.sleep(0.3)

    with open(output, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(records)} products -> {output}")


if __name__ == "__main__":
    main()
