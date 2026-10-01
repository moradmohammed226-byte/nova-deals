from datetime import datetime, timezone
import json
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_deals(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return data


def save_deals(path, deals):
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)
        f.write("\n")
