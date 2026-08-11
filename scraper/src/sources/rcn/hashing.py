"""Per-record hashing, ported from data-hub's RCNRecordHasher — minus its
local "seen hashes from output file" dedup logic, which isn't needed here:
PropertyRaw's own unique constraint on (source_id, external_ref,
content_hash) + INSERT ... ON CONFLICT DO NOTHING (data-ingestion) is the
single, authoritative dedup point now."""

import json
from hashlib import sha256


def to_json_safe(value):
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "wkt"):
        return value.wkt

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            return str(value)

    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return str(value)

    return value


def hash_record(layer: str, record: dict) -> str:
    canonical = json.dumps({"layer": layer, "record": record}, sort_keys=True, default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()
