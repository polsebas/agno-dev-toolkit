"""
Agno RAG Ingestion Pipeline — Semantic Chunking Edition.

Changes vs. previous version:
- Uses SemanticChunker (tree-sitter) instead of line-based chunk_code().
- Incremental re-indexing via HashStore: only chunks whose SHA-256 changed
  are re-embedded and re-inserted (Merkle-style, à la Cursor).
- Richer ChromaDB/Milvus metadata per chunk:
    symbol_name, chunk_type, line_start, line_end, content_hash, file_path.
- Markdown docs ingestion kept as-is via chunk_docs().
"""

import os
import subprocess
import logging

from rag.ingestion.clone_repo import clone_repo
from rag.ingestion.extract_tests import get_test_files
from rag.ingestion.chunker import chunk_docs          # docs still use markdown chunker
from rag.ingestion.embedder import embed
from rag.ingestion.hash_store import HashStore
from rag.storage.factory import get_vector_store
from analysis.ast.semantic_chunker import SemanticChunker
from config.settings import settings

logger = logging.getLogger("rag.ingestion.pipeline")


def run_pipeline() -> None:
    """
    Main ingestion entry point.

    1. Clone / locate Agno framework source.
    2. Walk all .py files, extract SemanticChunks.
    3. Skip chunks whose content_hash hasn't changed (incremental).
    4. Embed only changed/new chunks.
    5. Insert into vector store with rich metadata.
    6. Optionally ingest official docs (.md / .mdx).
    """
    print("🚀 Running Agno Semantic Pipeline...")

    repo = clone_repo()
    print(f"📦 Repo located at {repo}")

    chunker = SemanticChunker()
    hash_store = HashStore()
    store = get_vector_store()
    store.connect()
    store.create_collection()

    # ------------------------------------------------------------------
    # Phase 1: Python source — semantic chunks from ALL .py files
    # ------------------------------------------------------------------
    py_files = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs
                   if d not in {"venv", ".venv", ".git", "__pycache__", "node_modules"}]
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    print(f"📂 Found {len(py_files)} Python source files.")

    new_chunks, new_texts, new_meta = [], [], []
    skipped = 0

    for fpath in py_files:
        rel_path = os.path.relpath(fpath, start=repo)
        try:
            chunks = chunker.chunk_file(fpath)
        except Exception as e:
            logger.debug("Skipping %s: %s", fpath, e)
            continue

        for chunk in chunks:
            if chunk.symbol_name == "module_docstring" and not chunk.text.strip():
                continue

            if not hash_store.is_changed(rel_path, chunk.symbol_name, chunk.content_hash):
                skipped += 1
                continue

            new_chunks.append(chunk)
            new_texts.append(chunk.text)
            new_meta.append({
                "source": rel_path,
                "framework": "agno",
                "type": "source_chunk",
                "chunk_type": chunk.chunk_type,
                "symbol_name": chunk.symbol_name,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "content_hash": chunk.content_hash,
            })
            hash_store.update(rel_path, chunk.symbol_name, chunk.content_hash)

    print(f"⚡ {skipped} chunks unchanged (skipped re-embedding).")
    print(f"🆕 {len(new_chunks)} chunks to embed.")

    # ------------------------------------------------------------------
    # Phase 2: Official docs — markdown section chunking
    # ------------------------------------------------------------------
    if settings.ingest_docs:
        print("📚 Ingesting official docs...")
        docs_dir = "data/agno_docs"
        if not os.path.exists(docs_dir):
            print("   cloning https://github.com/agno-agi/docs …")
            subprocess.run(["git", "clone", "https://github.com/agno-agi/docs", docs_dir],
                           check=False)
        else:
            print(f"📦 Docs already at {docs_dir}")

        doc_files = []
        for root, _, fnames in os.walk(docs_dir):
            for fname in fnames:
                if fname.endswith((".md", ".mdx")):
                    doc_files.append(os.path.join(root, fname))

        print(f"📂 Found {len(doc_files)} doc files.")
        for d_file in doc_files:
            rel_path = os.path.relpath(d_file, start=docs_dir)
            try:
                with open(d_file, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            for i, chunk_text in enumerate(chunk_docs(content)):
                symbol_key = f"doc::{rel_path}::{i}"
                import hashlib
                h = hashlib.sha256(chunk_text.encode()).hexdigest()
                if not hash_store.is_changed(rel_path, symbol_key, h):
                    skipped += 1
                    continue
                new_texts.append(chunk_text)
                new_meta.append({
                    "source": rel_path,
                    "framework": "agno",
                    "type": "docs_section",
                    "chunk_type": "docs_section",
                    "symbol_name": symbol_key,
                    "line_start": 0,
                    "line_end": 0,
                    "content_hash": h,
                })
                hash_store.update(rel_path, symbol_key, h)

    # ------------------------------------------------------------------
    # Phase 3: Embed + insert only changed chunks
    # ------------------------------------------------------------------
    if not new_texts:
        print("✅ Nothing new to embed — index is up to date.")
        hash_store.commit()
        hs = hash_store.stats()
        hash_store.close()
        print(f"📊 Hash store: {hs['total_chunks_tracked']} chunks tracked "
              f"across {hs['files_tracked']} files.")
        return

    print(f"🧩 Embedding {len(new_texts)} chunks...")
    embeddings = embed(new_texts)
    print("✅ Embeddings done.")

    BATCH_SIZE = 5000
    total = len(new_texts)
    for i in range(0, total, BATCH_SIZE):
        end = min(i + BATCH_SIZE, total)
        store.insert(
            texts=new_texts[i:end],
            vectors=embeddings[i:end],
            metadata=new_meta[i:end],
        )
        print(f"  📥 Inserted batch {i // BATCH_SIZE + 1} ({end}/{total} chunks)")

    hash_store.commit()
    hs = hash_store.stats()
    hash_store.close()

    print(f"🎉 Ingested {total} new/changed chunks into {store.__class__.__name__}.")
    print(f"📊 Hash store: {hs['total_chunks_tracked']} chunks tracked "
          f"across {hs['files_tracked']} files.")


if __name__ == "__main__":
    run_pipeline()
