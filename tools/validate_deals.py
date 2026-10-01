import json
import sys
from pathlib import Path
from urllib.parse import urlparse


DATA_FILE = Path("data/deals.json")

REQUIRED_FIELDS = {
    "id",
    "source",
    "source_product_id",
    "title_en",
    "title_ar",
    "description_en",
    "description_ar",
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
    "created_at",
    "updated_at",
    "status",
    "published_website",
    "published_telegram",
    "published_facebook",
    "verified_at",
}

ALLOWED_STATUS = {"draft", "active", "expired"}


def valid_url(value):
    if not isinstance(value, str) or not value.strip():
        return False

    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_number(value, allow_none=True):
    if value is None and allow_none:
        return True

    return isinstance(value, (int, float)) and not isinstance(value, bool)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/deals.json")
    args = parser.parse_args()

    data_file = Path(args.input)

    errors = []
    warnings = []

    if not data_file.exists():
        print(f"ERROR: missing file: {data_file}")
        return 1

    try:
        with data_file.open("r", encoding="utf-8") as f:
            deals = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}")
        return 1
    except OSError as exc:
        print(f"ERROR: cannot read {data_file}: {exc}")
        return 1

    if not isinstance(deals, list):
        print("ERROR: deals.json root must be a JSON array")
        return 1

    seen_ids = set()

    for index, deal in enumerate(deals):
        prefix = f"deal[{index}]"

        if not isinstance(deal, dict):
            errors.append(f"{prefix}: expected object")
            continue

        missing = sorted(REQUIRED_FIELDS - set(deal))
        if missing:
            errors.append(f"{prefix}: missing fields: {', '.join(missing)}")

        product_id = deal.get("id")
        if product_id is None or str(product_id).strip() == "":
            errors.append(f"{prefix}: missing id")
        else:
            normalized_id = str(product_id)
            if normalized_id in seen_ids:
                errors.append(f"{prefix}: duplicate id: {normalized_id}")
            seen_ids.add(normalized_id)

        affiliate_url = deal.get("affiliate_url")
        if not valid_url(affiliate_url):
            errors.append(f"{prefix}: invalid affiliate_url")

        price = deal.get("price")
        if not valid_number(price, allow_none=False) or price <= 0:
            errors.append(f"{prefix}: invalid price")

        original_price = deal.get("original_price")
        if not valid_number(original_price):
            errors.append(f"{prefix}: invalid original_price")
        elif original_price is not None and original_price <= 0:
            errors.append(f"{prefix}: original_price must be greater than zero")

        discount = deal.get("discount")
        if not valid_number(discount):
            errors.append(f"{prefix}: invalid discount")
        elif discount is not None and (discount < 0 or discount > 100):
            errors.append(f"{prefix}: discount must be between 0 and 100")

        status = deal.get("status")
        if status not in ALLOWED_STATUS:
            errors.append(f"{prefix}: invalid status: {status!r}")

        for field in ("title_en", "category", "store", "country", "currency"):
            value = deal.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: empty required value: {field}")

        for field in ("published_website", "published_telegram", "published_facebook"):
            value = deal.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(f"{prefix}: invalid {field}")

        if original_price is not None and price > original_price:
            warnings.append(
                f"{prefix}: price ({price}) is greater than original_price ({original_price})"
            )

    print(f"FILE: {data_file}")
    print(f"COUNT: {len(deals)}")
    print(f"UNIQUE_IDS: {len(seen_ids)}")
    print(f"ERRORS: {len(errors)}")
    print(f"WARNINGS: {len(warnings)}")

    if errors:
        print("\nVALIDATION ERRORS:")
        for error in errors:
            print(f"- {error}")

    if warnings:
        print("\nVALIDATION WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        return 1

    print("\nVALIDATION_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
