import json
import sys
from collections import defaultdict
from pathlib import Path
import re


DATA_FILE = Path("data/deals.json")


def normalize_title(title):
    text = str(title or "").lower()
    text = re.sub(r"[^a-z0-9\u0600-\u06ff]+", " ", text)
    return " ".join(text.split())


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/deals.json")
    args = parser.parse_args()

    data_file = Path(args.input)

    if not data_file.exists():
        print(f"ERROR: missing file: {data_file}")
        return 1

    try:
        with data_file.open("r", encoding="utf-8") as f:
            deals = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read {data_file}: {exc}")
        return 1

    if not isinstance(deals, list):
        print("ERROR: deals.json root must be a JSON array")
        return 1

    source_groups = defaultdict(list)
    title_groups = defaultdict(list)

    for deal in deals:
        source_key = (
            str(deal.get("source") or ""),
            str(deal.get("source_product_id") or deal.get("id") or ""),
        )
        source_groups[source_key].append(deal.get("id"))

        title_key = normalize_title(deal.get("title_en"))
        if title_key:
            title_groups[title_key].append(deal.get("id"))

    exact_duplicates = {
        key: ids for key, ids in source_groups.items() if len(ids) > 1
    }

    title_warnings = {
        key: ids for key, ids in title_groups.items() if len(ids) > 1
    }

    print(f"FILE: {data_file}")
    print(f"COUNT: {len(deals)}")
    print(f"UNIQUE_SOURCE_KEYS: {len(source_groups)}")
    print(f"EXACT_SOURCE_DUPLICATE_GROUPS: {len(exact_duplicates)}")
    print(
        "EXACT_SOURCE_DUPLICATE_RECORDS:",
        sum(len(ids) - 1 for ids in exact_duplicates.values()),
    )
    print(f"TITLE_SIMILARITY_WARNING_GROUPS: {len(title_warnings)}")
    print(
        "TITLE_SIMILARITY_WARNING_RECORDS:",
        sum(len(ids) - 1 for ids in title_warnings.values()),
    )

    if exact_duplicates:
        print("\nEXACT SOURCE DUPLICATES:")
        for key, ids in exact_duplicates.items():
            print(f"- {key}: {ids}")

    if title_warnings:
        print("\nTITLE SIMILARITY WARNINGS:")
        for title, ids in list(title_warnings.items())[:20]:
            print(f"- {title}")
            print(f"  IDS: {ids}")

    if exact_duplicates:
        print("\nDEDUPE_REQUIRED")
        return 1

    print("\nDEDUPE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
