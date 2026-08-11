"""Resolving which TERYT codes an RCN discovery run should check.

RCN publishes one file per powiat (county), named `{TERYT}_transakcje_ceny.gpkg.zip`,
where TERYT is a 4-digit code: 2 digits of województwo + 2 digits of powiat.

There is no index/listing endpoint — the only way to learn what exists is to
probe candidate codes. So "download everything" is expressed as the full
candidate space, and DiscoverStage's HEAD probe filters it down to the codes
that actually have a file (non-200 responses are skipped silently).

Scope comes from Job.params, so one Source can serve both:
    {"teryt_codes": ["1261"]}          -> just Kraków
    {"teryt_codes": ["1261", "1465"]}  -> Kraków + Warszawa
    {"teryt_codes": "all"}             -> every candidate code
"""

# Województwo codes are even, 02..32 (16 voivodeships).
VOIVODESHIP_CODES = [f"{n:02d}" for n in range(2, 33, 2)]

# Powiat numbers within a voivodeship: 01..39 are land counties, 61..79 are
# cities with county rights. Probing the gap costs nothing but HEAD requests,
# so the range is kept generous rather than precise.
MAX_POWIAT = 99

# Used when a Job supplies no params at all. Deliberately a single county
# rather than "all": an unconfigured job should not silently kick off
# ~1.5k probe requests against a public government service.
DEFAULT_TERYT_CODES = ["1261"]  # Kraków

ALL = "all"


def all_candidate_codes() -> list[str]:
    """Every syntactically valid powiat code. Most do not exist as files —
    DiscoverStage's HEAD probe filters them out."""
    return [
        f"{voivodeship}{powiat:02d}"
        for voivodeship in VOIVODESHIP_CODES
        for powiat in range(1, MAX_POWIAT + 1)
    ]


def resolve_teryt_codes(params: dict) -> list[str]:
    """Job.params -> concrete list of codes to probe."""
    requested = (params or {}).get("teryt_codes")

    if requested is None:
        return list(DEFAULT_TERYT_CODES)

    if isinstance(requested, str):
        if requested.strip().lower() == ALL:
            return all_candidate_codes()
        # Tolerate a single code given as a bare string, or "1261,1465".
        return [code.strip() for code in requested.split(",") if code.strip()]

    if isinstance(requested, (list, tuple)):
        return [str(code).strip() for code in requested if str(code).strip()]

    raise ValueError(
        f"Invalid teryt_codes in Job.params: {requested!r} — expected a list, "
        f'a comma-separated string, or "all"'
    )
