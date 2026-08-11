"""RCN-specific bits of the Geoportal endpoint.

The throttled binary HTTP helpers live in src/sdk/binary.py and are shared
with other sources (listing photos use the same ones) — only the URL layout
and the probe size are RCN's own.

Note on the probe: Geoportal answers `Accept-Ranges: None` and returns 200
for a ranged request, i.e. it ignores `Range` and starts streaming the whole
(hundreds of MB) file. That is why the probe must cap how much it reads.
"""

from src.sdk.binary import throttled_download_to_file, throttled_get_bytes, throttled_head  # noqa: F401

BASE_URL = "https://opendata.geoportal.gov.pl/InneDane/latest_exports/rcn_transakcje_ceny/GPKG"
PROBE_BYTES = 65536


def file_url(file_id: str) -> str:
    return f"{BASE_URL}/{file_id}_transakcje_ceny.gpkg.zip"
