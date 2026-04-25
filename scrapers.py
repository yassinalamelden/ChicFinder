import json
import re
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand configs
# ---------------------------------------------------------------------------
BRANDS = [
    {
        "name": "asili",
        "type": "shopify",
        "base_url": "https://asilieg.com",
        "api": "https://asilieg.com/products.json",
    },
    {
        "name": "in_your_shoe",
        "type": "shopify",
        "base_url": "https://inyourshoe.com",
        "api": "https://inyourshoe.com/products.json",
    },
    {
        "name": "y_studios",
        "type": "shopify",
        "base_url": "https://ystudios.net",
        "api": "https://ystudios.net/products.json",
    },
    {
        "name": "ravin",
        "type": "shopify",
        "base_url": "https://shop.iravin.com",
        "api": "https://shop.iravin.com/products.json",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
GENDER_TAGS = {"men", "kids", "boys", "girls", "unisex", "women", "special sizes"}
JSONL_PATH = "data/barawy_raw.jsonl"
IMAGES_DIR = "data/raw_images"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    except Exception:
        return None

def next_url(link_header):
    for part in link_header.split(","):
        if 'rel="next"' in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def append_jsonl(record: dict):
    Path(JSONL_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()

# ---------------------------------------------------------------------------
# Image downloader
# ---------------------------------------------------------------------------

def download_images(product_id: str, image_urls: list[str]):
    out_dir = Path(IMAGES_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, url in enumerate(image_urls):
        dest = out_dir / f"{product_id}_{idx}.jpg"
        if dest.exists():
            continue

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                dest.write_bytes(r.content)
                break
            except Exception as e:
                log.warning(f"  Image download failed (attempt {attempt}/{MAX_RETRIES}): {url} — {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

# ---------------------------------------------------------------------------
# Shopify scraper
# ---------------------------------------------------------------------------

def scrape_shopify(brand_config: dict):
    brand = brand_config["name"]
    base_url = brand_config["base_url"]
    api = brand_config["api"]

    session = requests.Session()
    session.headers.update(HEADERS)

    log.info(f"[{brand}] Starting Shopify scrape...")

    url = f"{api}?limit=250"
    seen = set()
    count = 0

    while url:
        try:
            r = session.get(url, timeout=30)
            if not r.ok:
                log.error(f"[{brand}] HTTP {r.status_code} — stopping pagination")
                break
            batch = r.json().get("products", [])
        except Exception as e:
            log.error(f"[{brand}] Request/parse error: {e}")
            break

        for p in batch:
            try:
                pid = str(p.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)

                title = strip(p.get("title"))
                if not title:
                    continue

                handle = p.get("handle", "")
                product_url = f"{base_url}/products/{handle}" if handle else ""
                if not product_url:
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

                record = {
                    "id": f"{brand}_{pid}",
                    "brand": brand,
                    "name": title,
                    "price": price,
                    "category": category,
                    "subcategory": subcategory,
                    "availability": availability,
                    "image_urls": images,
                    "product_url": product_url,
                    "description": strip(p.get("body_html")) or None,
                    "scraped_at": now(),
                }

                append_jsonl(record)
                download_images(record["id"], images)
                count += 1
                log.info(f"  [{brand}] [{count}] {title}")

            except Exception as e:
                log.error(f"  [{brand}] Error processing product {p.get('id')}: {e}")
                continue

        if len(batch) < 250:
            break

        link = r.headers.get("Link", "")
        url = next_url(link) if link else None
        time.sleep(0.5)

    log.info(f"[{brand}] Done — {count} products saved.")

# ---------------------------------------------------------------------------
# Playwright scraper
# ---------------------------------------------------------------------------

def scrape_playwright(brand_config: dict):
    brand = brand_config["name"]
    start_url = brand_config["url"]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error(f"[{brand}] Playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    log.info(f"[{brand}] Starting Playwright scrape...")
    count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(start_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            for _ in range(5):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(0.8)

            links = page.eval_on_selector_all(
                "a[href*='/product']",
                "els => els.map(e => e.href)"
            )
            links = list(dict.fromkeys(links))
            log.info(f"[{brand}] Found {len(links)} product links")

            for product_url in links:
                try:
                    page.goto(product_url, timeout=20000)
                    page.wait_for_load_state("domcontentloaded", timeout=10000)

                    title = strip(page.title())
                    pid = re.sub(r"[^a-z0-9]+", "_", product_url.lower())[-40:]

                    price_el = page.query_selector("[class*='price']")
                    price = get_price(strip(price_el.inner_text()) if price_el else None)

                    img_els = page.query_selector_all("img[src*='cdn'], img[src*='product']")
                    images = list({strip(el.get_attribute("src")) for el in img_els if el.get_attribute("src")})

                    sold_out = page.query_selector("[class*='sold-out'], [class*='unavailable']")
                    availability = "OutOfStock" if sold_out else "InStock"

                    record = {
                        "id": f"{brand}_{pid}",
                        "brand": brand,
                        "name": title,
                        "price": price,
                        "category": None,
                        "subcategory": None,
                        "availability": availability,
                        "image_urls": images,
                        "product_url": product_url,
                        "description": None,
                        "scraped_at": now(),
                    }

                    append_jsonl(record)
                    download_images(record["id"], images)
                    count += 1
                    log.info(f"  [{brand}] [{count}] {title}")

                except Exception as e:
                    log.error(f"  [{brand}] Error on {product_url}: {e}")
                    continue

                time.sleep(0.5)

        except Exception as e:
            log.error(f"[{brand}] Fatal Playwright error: {e}")
        finally:
            browser.close()

    log.info(f"[{brand}] Done — {count} products saved.")

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    Path("data").mkdir(exist_ok=True)

    for brand in BRANDS:
        brand_type = brand.get("type")
        if brand_type == "shopify":
            scrape_shopify(brand)
        elif brand_type == "playwright":
            scrape_playwright(brand)
        else:
            log.warning(f"Unknown type '{brand_type}' for brand '{brand.get('name')}' — skipping")

if __name__ == "__main__":
    main()