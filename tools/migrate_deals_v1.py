import json
import sys
from pathlib import Path

from lib_common import utc_now


DATA_FILE = Path("data/deals.json")

NEW_FIELDS = {
    "source": "admitad",
    "source_product_id": None,
    "description_en": None,
    "raw_category": None,
    "subcategory": None,
    "original_price": None,
    "created_at": None,
    "updated_at": None,
    "published_website": None,
    "published_telegram": None,
    "published_facebook": None,
}


def migrate_deal(deal, now):
    migrated = dict(deal)

    migrated.setdefault("source", "admitad")
    migrated.setdefault("source_product_id", str(deal["id"]))
    migrated.setdefault("description_en", None)
    migrated.setdefault("raw_category", deal.get("category"))
    migrated.setdefault("subcategory", None)
    migrated.setdefault("original_price", None)
    migrated.setdefault("created_at", now)
    migrated.setdefault("updated_at", now)
    migrated.setdefault("published_website", None)
    migrated.setdefault("published_telegram", None)
    migrated.setdefault("published_facebook", None)

    return migrated


def main():
    if not DATA_FILE.exists():
        print(f"ERROR: missing file: {DATA_FILE}")
        return 1

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            deals = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read {DATA_FILE}: {exc}")
        return 1

    if not isinstance(deals, list):
        print("ERROR: deals.json root must be a JSON array")
        return 1

    now = utc_now()
    migrated = [migrate_deal(deal, now) for deal in deals]

    print(f"INPUT_COUNT: {len(deals)}")
    print(f"OUTPUT_COUNT: {len(migrated)}")
    print(f"MIGRATION_TIME: {now}")

    if len(deals) != len(migrated):
        print("ERROR: migration changed record count")
        return 1

    print("MIGRATION_PLAN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
