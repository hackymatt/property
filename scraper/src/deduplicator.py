"""Redis-backed job deduplicator using atomic SET NX.

Two separate namespaces prevent publish-time keys from blocking consume-time checks:
  dedup:q:<hash>  — set when a job is placed on the queue (prevents queue bloat)
  dedup:p:<hash>  — set when a job is actually processed (prevents double-processing)
"""

import hashlib

_TTL = {
    "list_pages": 3600,       # 1 h
    "list_items": 3600,       # 1 h
    "get_item":   86400 * 7,  # 7 d — don't re-scrape the same listing within a week
}
_DEFAULT_TTL = 3600


class JobDeduplicator:
    def __init__(self, redis_client):
        self._redis = redis_client

    def _key(self, prefix: str, source: str, stage: str, url: str) -> str:
        digest = hashlib.sha256(f"{source}:{stage}:{url}".encode()).hexdigest()
        return f"dedup:{prefix}:{digest}"

    async def mark_queued(self, source: str, stage: str, url: str) -> bool:
        """Call before publishing a follow-up job.
        Returns True if the job is new (and marks it queued); False if already queued.
        """
        key = self._key("q", source, stage, url)
        ttl = _TTL.get(stage, _DEFAULT_TTL)
        return await self._redis.set(key, 1, ex=ttl, nx=True) is not None

    async def mark_processed(self, source: str, stage: str, url: str) -> bool:
        """Call before processing a consumed job.
        Returns True if the job is new (and marks it processed); False if already processed.
        """
        key = self._key("p", source, stage, url)
        ttl = _TTL.get(stage, _DEFAULT_TTL)
        return await self._redis.set(key, 1, ex=ttl, nx=True) is not None

    async def clear(self, source: str, stage: str, url: str) -> None:
        """Remove both keys so a job can be requeued and reprocessed (e.g. after 429/403)."""
        await self._redis.delete(
            self._key("q", source, stage, url),
            self._key("p", source, stage, url),
        )
