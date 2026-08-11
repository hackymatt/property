"""Maps ScraperSourceStage.code_ref -> Stage class.

To add a source: write Stage subclasses under src/sources/<name>/stages.py,
register them here, deploy, then point ScraperSourceStage.code_ref rows at
the registered keys via Django admin. The database never holds executable
code — only these string references.
"""

from src.sources.otodom import stages as otodom_stages
from src.sources.rcn import stages as rcn_stages
from src.stages.base import Stage

STAGE_REGISTRY: dict[str, type[Stage]] = {
    "otodom.ListPagesStage": otodom_stages.ListPagesStage,
    "otodom.ListItemsStage": otodom_stages.ListItemsStage,
    "otodom.GetItemStage": otodom_stages.GetItemStage,
    "otodom.DownloadPhotosStage": otodom_stages.DownloadPhotosStage,
    "rcn.DiscoverStage": rcn_stages.DiscoverStage,
    "rcn.DownloadStage": rcn_stages.DownloadStage,
    "rcn.ExtractStage": rcn_stages.ExtractStage,
    "rcn.ReadRecordsStage": rcn_stages.ReadRecordsStage,
}


def resolve(code_ref: str) -> Stage:
    stage_cls = STAGE_REGISTRY.get(code_ref)
    if stage_cls is None:
        raise ValueError(f"Unknown code_ref '{code_ref}' — not found in STAGE_REGISTRY")
    return stage_cls()
