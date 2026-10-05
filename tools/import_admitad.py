import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from lib_common import load_deals, utc_now
from collections import Counter, defaultdict

G = "http://base.google.com/ns/1.0"
TOP_PER_CATEGORY = 50
TARGET = 100


def clean_xml_bytes(data):
    # XML 1.0 allows only TAB, LF and CR among control characters.
    return re.sub(rb"[\x00-\x08\x0B\x0C\x0E-\x1F]", b"", data)


def value(item, tag):
    node = item.find(f"{{{G}}}{tag}")
    if node is None or node.text is None:
        return ""
    return html.unescape(node.text.strip())


def money(value_text):
    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s+([A-Z]{3})\s*$", value_text)
    if not match:
        return None, ""
    return float(match.group(1)), match.group(2)


def sunsky_text(element, tag):
    node = element.find(tag)
    if node is None or node.text is None:
        return ""
    return html.unescape(node.text.strip())


def sunsky_category_name(category_map, category_id):
    return category_map.get(str(category_id).strip(), "")


def sunsky_root_category(category_map, category_id):
    current = str(category_id or "").strip()
    if not current:
        return ""

    seen = set()

    while current and current not in seen:
        seen.add(current)
        name, parent = category_map.get(current, ("", ""))
        if not name:
            return ""

        if not parent:
            return name.strip()

        current = str(parent).strip()

    return ""


def sunsky_product_category(category_map, category_id):
    from normalize_categories import CATEGORY_MAP

    current = str(category_id or "").strip()
    if not current:
        return None, None

    seen = set()

    while current and current not in seen:
        seen.add(current)

        name, parent = category_map.get(current, ("", ""))
        name = str(name or "").strip()

        if name and name in CATEGORY_MAP:
            return CATEGORY_MAP[name], name

        if not parent:
            break

        current = str(parent).strip()

    root = sunsky_root_category(category_map, category_id)
    if root in CATEGORY_MAP:
        return CATEGORY_MAP[root], root

    return None, root or None


def parse_google_item(item):
    offer_id = value(item, "id")
    title = value(item, "title")
    category = value(item, "product_type")
    image = value(item, "image_link")

    from normalize_categories import CATEGORY_MAP

    root_category = str(category or "").split(" > ", 1)[0].strip()
    if root_category not in CATEGORY_MAP:
        return None

    affiliate_url = value(item, "link")
    availability = value(item, "availability").lower()

    regular_price, currency = money(value(item, "price"))
    sale_price, sale_currency = money(value(item, "sale_price"))

    if not all([offer_id, title, category, image, affiliate_url]):
        return None

    if availability != "in stock":
        return None

    if regular_price is None or sale_price is None:
        return None

    if not (regular_price > sale_price > 0):
        return None

    if not currency:
        currency = sale_currency

    discount = (regular_price - sale_price) / regular_price * 100
    price_score = max(0.0, min(1.0, (50.0 - sale_price) / 25.0))
    discount_score = min(1.0, discount / 50.0)
    score = 0.65 * discount_score + 0.35 * price_score

    return {
        "id": offer_id,
        "source": "admitad",
        "source_product_id": offer_id,
        "title_en": title,
        "title_ar": "",
        "description_en": value(item, "description") or None,
        "description_ar": "",
        "category": category,
        "raw_category": category,
        "subcategory": None,
        "store": "SUNSKY",
        "country": "GLOBAL",
        "currency": currency or sale_currency,
        "price": round(sale_price, 2),
        "original_price": round(regular_price, 2),
        "discount": round(discount, 2),
        "image": image,
        "product_url": None,
        "affiliate_url": affiliate_url,
        "created_at": None,
        "updated_at": None,
        "status": "draft",
        "published_website": None,
        "published_telegram": None,
        "published_facebook": None,
        "_score": score,
    }


def parse_sunsky_offer(offer, category_map):
    offer_id = str(offer.get("id") or "").strip()
    available = str(offer.get("available") or "").strip().lower()

    title = sunsky_text(offer, "name")
    image = sunsky_text(offer, "picture")
    affiliate_url = sunsky_text(offer, "url")
    description = sunsky_text(offer, "description")

    category_id = sunsky_text(offer, "categoryId")
    category, raw_category = sunsky_product_category(category_map, category_id)

    price_text = sunsky_text(offer, "price")
    try:
        price = float(price_text)
    except (TypeError, ValueError):
        return None

    currency = sunsky_text(offer, "currencyId") or "USD"

    if not all([offer_id, title, image, affiliate_url, category, raw_category]):
        return None

    if available not in {"true", "1", "yes"}:
        return None

    if price <= 0:
        return None

    # SUNSKY feed provides one current price only. Do not invent a discount.
    price_score = max(0.0, min(1.0, (50.0 - price) / 25.0))
    score = 0.35 * price_score

    return {
        "id": offer_id,
        "source": "admitad",
        "source_product_id": offer_id,
        "title_en": title,
        "title_ar": "",
        "description_en": description or None,
        "description_ar": "",
        "category": category,
        "raw_category": raw_category,
        "subcategory": None,
        "store": "SUNSKY",
        "country": "GLOBAL",
        "currency": currency,
        "price": round(price, 2),
        "original_price": None,
        "discount": 0,
        "image": image,
        "product_url": None,
        "affiliate_url": affiliate_url,
        "created_at": None,
        "updated_at": None,
        "status": "draft",
        "published_website": None,
        "published_telegram": None,
        "published_facebook": None,
        "_score": score,
    }


def iter_products(stream):
    parser = ET.XMLPullParser(events=("start", "end"))
    source_type = None
    category_map = {}
    inside_categories = False

    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break

        parser.feed(clean_xml_bytes(chunk))

        for event, element in parser.read_events():
            tag = element.tag

            if event == "start":
                if tag == "yml_catalog":
                    source_type = "sunsky"
                elif tag == "categories":
                    inside_categories = True
                continue

            if source_type == "sunsky":
                if tag == "category" and inside_categories:
                    category_id = str(element.get("id") or "").strip()
                    parent_id = str(element.get("parentId") or "").strip()
                    name = (element.text or "").strip()
                    if category_id and name:
                        category_map[category_id] = (name, parent_id)
                    element.clear()

                elif tag == "categories":
                    inside_categories = False
                    element.clear()

                elif tag == "offer":
                    product = parse_sunsky_offer(element, category_map)
                    element.clear()
                    if product is not None:
                        yield product

            elif tag == "item":
                product = parse_google_item(element)
                element.clear()
                if product is not None:
                    yield product

    # Do not close the parser: the feed may be streamed/truncated after complete items.

def select_products(groups):
    TARGET = 100
    MAX_PER_CATEGORY = 25

    selected = []
    positions = {category: 0 for category in groups}

    while len(selected) < TARGET:
        best = None

        for category, candidates in groups.items():
            index = positions[category]

            if index >= MAX_PER_CATEGORY or index >= len(candidates):
                continue

            candidate = candidates[index]

            # Mild diversity penalty: additional products from the same
            # category must be progressively stronger to be selected.
            diversity_factor = 1.0 / (1.0 + 0.20 * index)
            adjusted_score = candidate["_score"] * diversity_factor

            key = (
                adjusted_score,
                candidate["_score"],
                candidate["discount"],
                -candidate["price"],
            )

            if best is None or key > best[0]:
                best = (key, category, candidate)

        if best is None:
            break

        _, category, candidate = best
        selected.append(candidate)
        positions[category] += 1

    return selected


def merge_deals(selected):
    path = Path("data/deals.json")
    existing = load_deals(path)
    now = utc_now()

    feed_fields = {
        "source",
        "source_product_id",
        "title_en",
        "description_en",
        "category",
        "raw_category",
        "subcategory",
        "store",
        "country",
        "currency",
        "price",
        "original_price",
        "discount",
        "image",
        "product_url",
        "affiliate_url",
    }

    preserved_fields = {
        "title_ar",
        "description_ar",
        "status",
        "published_website",
        "published_telegram",
        "published_facebook",
        "verified_at",
    }

    existing_by_id = {str(old.get("id")): old for old in existing}
    merged = []

    for product in selected:
        product_id = str(product["id"])
        old = existing_by_id.get(product_id)

        if old is not None:
            deal = dict(old)
            for field in feed_fields:
                deal[field] = product.get(field)

            if not deal.get("created_at"):
                deal["created_at"] = now
            deal["updated_at"] = now

            for field in preserved_fields:
                if field not in deal:
                    deal[field] = None if field.startswith("published_") else ""

            merged.append(deal)
        else:
            deal = dict(product)
            deal["created_at"] = now
            deal["updated_at"] = now

            for field in preserved_fields:
                if field not in deal:
                    deal[field] = None if field.startswith("published_") else ""

            merged.append(deal)

    return merged

def main():
    groups = defaultdict(list)
    parsed = 0
    accepted = 0

    for product in iter_products(sys.stdin.buffer):
        parsed += 1
        groups[product["category"]].append(product)
        accepted += 1

    selected = select_products(groups)
    merged = merge_deals(selected)

    print(json.dumps(merged, ensure_ascii=False, indent=2))

    print(
        f"\n# IMPORT STATS: parsed={parsed} "
        f"accepted={accepted} categories={len(groups)} selected={len(selected)} "
        f"merged={len(merged)}",
        file=sys.stderr,
    )

    print("# CATEGORY DISTRIBUTION:", file=sys.stderr)
    for category, count in Counter(
        product["category"] for product in merged
    ).most_common():
        print(f"# {count:2d} | {category}", file=sys.stderr)


if __name__ == "__main__":
    main()
