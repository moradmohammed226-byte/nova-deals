import argparse
import json
import sys
from collections import Counter
from pathlib import Path

CATEGORY_MAP = {
    "Sports Shoes,Clothing&Accessories": "fashion",
    "Apparel Accessories": "fashion",
    "Women's Clothing": "fashion",
    "Men's Clothing": "fashion",
    "Novelty & Special Use": "fashion",
    "Luggage & Bags": "fashion",
    "Hair Extensions & Wigs": "fashion",
    "Computer & Office": "electronics",
    "Consumer Electronics": "electronics",
    "Electronic Components & Supplies": "electronics",
    "Home & Garden": "home",
    "Home Appliances": "home",
    "Home Improvement": "home",
    "Mother & Kids": "other",
    "Toys & Hobbies": "other",
    "Office & School Supplies": "other",
    "Automobiles, Parts & Accessories": "other",
    "Motorcycle Equipments & Parts": "other",
    "Tools": "other",
    "Sports & Entertainment": "other",
    "Beauty & Health": "other",
}

VALID_CATEGORIES = {"fashion", "electronics", "home", "other"}


def root_category(category):
    text = str(category or "").strip()
    if " > " in text:
        return text.split(" > ", 1)[0].strip()
    return text


def normalize_deals(deals):
    unknown = Counter()
    normalized = Counter()

    for deal in deals:
        raw = deal.get("raw_category") or deal.get("category")
        root = root_category(raw)
        target = CATEGORY_MAP.get(root)

        if target is None:
            unknown[root] += 1
            continue

        deal["raw_category"] = raw
        deal["category"] = target
        normalized[target] += 1

    return unknown, normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/deals.json")
    parser.add_argument("--output", default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        print(f"ERROR: missing file: {input_path}")
        return 1

    try:
        with input_path.open("r", encoding="utf-8") as f:
            deals = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read {input_path}: {exc}")
        return 1

    if not isinstance(deals, list):
        print("ERROR: input root must be a JSON array")
        return 1

    unknown, normalized = normalize_deals(deals)

    print(f"INPUT: {input_path}")
    print(f"COUNT: {len(deals)}")

    print("\n=== NORMALIZED DISTRIBUTION ===")
    for category, count in normalized.most_common():
        print(f"{count:>3} | {category}")

    print("\n=== UNKNOWN ROOT CATEGORIES ===")
    if unknown:
        for category, count in unknown.most_common():
            print(f"{count:>3} | {category}")
        print("\nNORMALIZATION_REVIEW_REQUIRED")
        return 1
    else:
        print("NONE")

    if not args.apply:
        print("\nNORMALIZATION_PLAN_OK")
        return 0

    if output_path.parent:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)
        f.write("\n")

    invalid = [
        deal.get("category")
        for deal in deals
        if deal.get("category") not in VALID_CATEGORIES
    ]

    if invalid:
        print("ERROR: invalid normalized category detected")
        return 1

    print(f"\nOUTPUT: {output_path}")
    print("NORMALIZATION_APPLIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
