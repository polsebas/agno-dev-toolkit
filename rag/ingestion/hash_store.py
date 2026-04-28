"""
SQLite-backed content-hash store for incremental RAG re-indexing.

Implements a simple Merkle-style check: store the SHA-256 of each
(file_path, symbol_name) chunk. On the next pipeline run, skip any
chunk whose hash hasn't changed.

Usage:
    from rag.ingestion.hash_store import HashStore
    store = HashStore()
    if not store.is_changed(file_path, symbol_name, content_hash):
        continue  # skip re-embedding
    # ... embed ...
    store.update(file_path, symbol_name, content_hash)
    store.commit()
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rag.ingestion.hash_store")

_DEFAULT_DB = "data/chunk_hashes.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chunk_hashes (
    file_path    TEXT NOT NULL,
    symbol_name  TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (file_path, symbol_name)
)
"""


class HashStore:
    """Persist chunk content hashes to avoid redundant re-embedding."""

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(db_path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        logger.debug("HashStore ready at %s", db_path)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def is_changed(self, file_path: str, symbol_name: str,
                   content_hash: str) -> bool:
        """Return True if this chunk is new or its content has changed."""
        stored = self._get_hash(file_path, symbol_name)
        return stored != content_hash

    def update(self, file_path: str, symbol_name: str,
               content_hash: str) -> None:
        """Upsert the hash for a chunk (call before commit())."""
        self._conn.execute(
            """
            INSERT INTO chunk_hashes (file_path, symbol_name, content_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(file_path, symbol_name)
            DO UPDATE SET content_hash = excluded.content_hash,
                          updated_at   = datetime('now')
            """,
            (file_path, symbol_name, content_hash),
        )

    def commit(self) -> None:
        """Flush pending writes to disk."""
        self._conn.commit()

    def purge_file(self, file_path: str) -> int:
        """Remove all hashes for a deleted/moved file. Returns row count."""
        cur = self._conn.execute(
            "DELETE FROM chunk_hashes WHERE file_path = ?", (file_path,)
        )
        self._conn.commit()
        return cur.rowcount

    def stats(self) -> dict:
        """Return summary stats for debugging."""
        cur = self._conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT file_path) FROM chunk_hashes"
        )
        total, files = cur.fetchone()
        return {"total_chunks_tracked": total, "files_tracked": files,
                "db_path": self._db_path}

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_hash(self, file_path: str, symbol_name: str) -> Optional[str]:
        cur = self._conn.execute(
            "SELECT content_hash FROM chunk_hashes WHERE file_path=? AND symbol_name=?",
            (file_path, symbol_name),
        )
        row = cur.fetchone()
        return row[0] if row else None
