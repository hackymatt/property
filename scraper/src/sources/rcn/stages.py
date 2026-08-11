"""RCN (FILE_REGISTRY) stage classes: DISCOVER -> DOWNLOAD -> EXTRACT -> READ.

Shaped to mirror the portal pipeline: every stage returns a small list of
refs and only the FINAL stage returns records, one message per batch. The
scraper never writes to the database — reading records is where its job
ends, and data-ingestion is what lands them in PropertyRaw (same as
Otodom's get_item). That is why there is no "load" stage here.

Nothing is normalized on the way in. Column names, values and the original
CRS are preserved verbatim so PropertyRaw stays reprocessable; mapping,
reprojection and validation belong to the later normalization phase that
reads PropertyRaw.

Change-detection ("did this file actually change") lives in bench against
JobRunLog, and per-record dedup in PropertyRaw's unique constraint — no
local registry files, unlike the original data-hub pipeline.
"""

import asyncio
import hashlib
import shutil
import time
import zipfile
from pathlib import Path

from config import RCN_SCRATCH_DIR
from src.logger import logger
from src.sources.rcn import geoportal
from src.sources.rcn.hashing import hash_record, to_json_safe
from src.sources.rcn.teryt_codes import resolve_teryt_codes
from src.stages.base import NextStageRef, RawItem, Stage, StageContext

DEFAULT_BATCH_SIZE = 2000

# The scratch volume is ephemeral by design, but a job that dies between
# EXTRACT and READ leaves its .gpkg behind. Sweep anything older than this
# on the next download rather than tracking ownership.
SCRATCH_MAX_AGE_SECONDS = 24 * 3600


def _scratch_root() -> Path:
    return Path(RCN_SCRATCH_DIR) / "rcn"


class DiscoverStage(Stage):
    """Probes the TERYT codes this job asks for (Job.params -> ctx.params;
    see teryt_codes.resolve_teryt_codes) and returns a ref + cheap
    fingerprint for every code that actually has a file. Codes with no file
    are skipped silently — that's how "all" narrows down to reality, since
    RCN exposes no index to list what exists.

    Returns refs for every file FOUND, changed or not: the hash-gate
    (comparing against the last successful terminal run) happens in bench,
    which has DB access; scraper deliberately has none."""

    async def run(self, ctx: StageContext) -> list[NextStageRef]:
        codes = resolve_teryt_codes(ctx.params)
        logger.info("[rcn.DiscoverStage] probing %d TERYT code(s)", len(codes))

        refs = []
        for code in codes:
            url = geoportal.file_url(code)
            fingerprint = await self._probe(ctx, url)
            if fingerprint is None:
                continue
            refs.append(NextStageRef(url=url, metadata={"file_id": code, "fingerprint": fingerprint}))

        logger.info("[rcn.DiscoverStage] %d/%d code(s) have a file", len(refs), len(codes))
        return refs

    @staticmethod
    async def _probe(ctx: StageContext, url: str) -> dict | None:
        head = await geoportal.throttled_head(ctx.throttle_helper, ctx.domain_name, url)
        if head is None:
            return None
        size = head["headers"].get("Content-Length")
        probe_bytes = await geoportal.throttled_get_bytes(
            ctx.throttle_helper,
            ctx.domain_name,
            url,
            headers={"Range": f"bytes=0-{geoportal.PROBE_BYTES - 1}"},
            max_bytes=geoportal.PROBE_BYTES,
        )
        probe_hash = None
        if probe_bytes:
            probe_hash = hashlib.sha256(probe_bytes).hexdigest()
        return {"size": size, "probe_hash": probe_hash}


class DownloadStage(Stage):
    """ctx.url = file URL, ctx.metadata carries file_id/fingerprint from
    DISCOVER. Downloads to the shared scratch volume; single ref for EXTRACT."""

    async def run(self, ctx: StageContext) -> list[NextStageRef]:
        await asyncio.to_thread(_purge_stale_scratch)

        file_id = ctx.metadata.get("file_id")
        dest = _scratch_root() / str(file_id) / "archive.zip"

        ok = await geoportal.throttled_download_to_file(ctx.throttle_helper, ctx.domain_name, ctx.url, dest)
        if not ok or not await asyncio.to_thread(_valid_zip, dest):
            if dest.exists():
                dest.unlink(missing_ok=True)
            logger.warning("[rcn.DownloadStage] failed/invalid download for file_id=%s", file_id)
            return []

        return [NextStageRef(url=str(dest), metadata=ctx.metadata)]


class ExtractStage(Stage):
    """ctx.url = local zip path. Unzips, finds the .gpkg, deletes the zip,
    then plans the read: one ref per chunk of rows.

    The layer comes from ScraperSource.config["layer"] — one source per
    layer (rcn/lokale, rcn/budynki, ...), because layers have different
    columns and map to different property types, exactly like Otodom has a
    separate source per sell/apartment. Chunk size: Job.params["batch_size"].
    """

    async def run(self, ctx: StageContext) -> list[NextStageRef]:
        zip_path = Path(ctx.url)
        gpkg_path = await asyncio.to_thread(_extract_zip, zip_path)
        if gpkg_path is None:
            logger.warning("[rcn.ExtractStage] no .gpkg found in %s", zip_path)
            return []

        zip_path.unlink(missing_ok=True)
        layer = ctx.source_config.get("layer")
        if not layer:
            raise ValueError(
                "ScraperSource.config must set 'layer' for an RCN source, "
                'e.g. {"layer": "transakcje_lokale"}'
            )

        batch_size = int(ctx.params.get("batch_size") or DEFAULT_BATCH_SIZE)
        return await asyncio.to_thread(self._plan_chunks, gpkg_path, ctx.metadata, layer, batch_size)

    @staticmethod
    def _plan_chunks(gpkg_path: Path, base_metadata: dict, layer: str, batch_size: int) -> list[NextStageRef]:
        import pyogrio

        file_id = base_metadata.get("file_id")
        available = [info[0] for info in pyogrio.list_layers(gpkg_path)]

        if layer not in available:
            logger.error(
                "[rcn.ExtractStage] layer '%s' not in file (available: %s) — "
                "fix ScraperSource.config for this source",
                layer, available,
            )
            return []

        total = int(pyogrio.read_info(gpkg_path, layer=layer).get("features", 0))
        refs = [
            # url must be unique per (file, layer, chunk) — it feeds the
            # scraper's (source, stage, url) dedup key.
            NextStageRef(
                url=f"{file_id}:{layer}:{offset}",
                metadata={
                    **base_metadata,
                    "gpkg_path": str(gpkg_path),
                    "layer": layer,
                    "offset": offset,
                    "limit": batch_size,
                },
            )
            for offset in range(0, total, batch_size)
        ]
        logger.info(
            "[rcn.ExtractStage] layer=%s (file has %s) -> %d record(s) in %d chunk(s)",
            layer, available, total, len(refs),
        )
        return refs


class ReadRecordsStage(Stage):
    """Final stage — reads one chunk of the layer and EMITS each row as its
    own record, verbatim. One record per message all the way to
    data-ingestion, which is what writes them to PropertyRaw; the scraper
    never touches the database.

    property_type comes from ScraperSource.property_type (applied in
    scrape.py::emit), since a source is one layer and therefore one kind of
    property."""

    async def run(self, ctx: StageContext) -> list[str]:
        metadata = ctx.metadata
        gpkg_path = Path(metadata.get("gpkg_path") or "")
        layer = metadata.get("layer")
        offset = int(metadata.get("offset") or 0)
        limit = int(metadata.get("limit") or DEFAULT_BATCH_SIZE)

        if not layer or not gpkg_path.exists():
            logger.warning(
                "[rcn.ReadRecordsStage] missing gpkg/layer (path=%s layer=%s) — "
                "scratch file was probably swept; the next DISCOVER will redo the file",
                gpkg_path, layer,
            )
            return []

        records = await asyncio.to_thread(self._read_chunk, gpkg_path, layer, offset, limit)
        for record in records:
            await ctx.emit(RawItem(external_ref=record["_hash"], data=record))

        logger.info("[rcn.ReadRecordsStage] layer=%s offset=%d -> %d record(s)", layer, offset, len(records))
        return []

    @staticmethod
    def _read_chunk(gpkg_path: Path, layer: str, offset: int, limit: int) -> list[dict]:
        import pyogrio

        df = pyogrio.read_dataframe(gpkg_path, layer=layer, skip_features=offset, max_features=limit)
        if df.empty:
            return []

        records = []
        for raw in df.to_dict(orient="records"):
            record = {key: to_json_safe(value) for key, value in raw.items()}
            record["_layer"] = layer
            record["_hash"] = hash_record(layer, record)
            records.append(record)
        return records


def _valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except zipfile.BadZipFile:
        return False


def _extract_zip(zip_path: Path) -> Path | None:
    extract_dir = zip_path.parent / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)
    except zipfile.BadZipFile:
        return None
    gpkg_files = list(extract_dir.glob("*.gpkg"))
    return gpkg_files[0] if gpkg_files else None


def _purge_stale_scratch() -> None:
    root = _scratch_root()
    if not root.exists():
        return
    cutoff = time.time() - SCRATCH_MAX_AGE_SECONDS
    for entry in root.iterdir():
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                logger.info("[rcn] Purged stale scratch dir %s", entry)
        except OSError:
            continue
