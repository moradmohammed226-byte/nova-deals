import json
import sys
from collections import Counter
from pathlib import Path


DATA_FILE = Path("data/deals.json")


def count_ready(deals, field):
    return sum(bool(str(deal.get(field) or "").strip()) for deal in deals)


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

    statuses = Counter(deal.get("status") for deal in deals)
    categories = Counter(deal.get("category") for deal in deals)
    sources = Counter(deal.get("source") for deal in deals)

    print("=== SUDX MARKET DEALS REPORT ===")
    print(f"FILE: {DATA_FILE}")
    print(f"COUNT: {len(deals)}")

    print("\n=== STATUS ===")
    for value, count in statuses.most_common():
        print(f"{count} | {value}")

    print("\n=== CATEGORIES ===")
    for value, count in categories.most_common():
        print(f"{count} | {value}")

    print("\n=== SOURCES ===")
    for value, count in sources.most_common():
        print(f"{count} | {value}")

    print("\n=== CONTENT READINESS ===")
    print(f"AFFILIATE_READY: {count_ready(deals, 'affiliate_url')}")
    print(f"AR_TITLE_READY: {count_ready(deals, 'title_ar')}")
    print(f"AR_DESCRIPTION_READY: {count_ready(deals, 'description_ar')}")

    print("\n=== PUBLISHING ===")
    print(f"WEBSITE_PUBLISHED: {count_ready(deals, 'published_website')}")
    print(f"TELEGRAM_PUBLISHED: {count_ready(deals, 'published_telegram')}")
    print(f"FACEBOOK_PUBLISHED: {count_ready(deals, 'published_facebook')}")

    publish_ready = sum(
        deal.get("status") == "active"
        and bool(str(deal.get("affiliate_url") or "").strip())
        for deal in deals
    )
    print(f"PUBLISH_READY_ACTIVE: {publish_ready}")

    print("\nREPORT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
