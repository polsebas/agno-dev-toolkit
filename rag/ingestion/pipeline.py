import os
from rag.ingestion.clone_repo import clone_repo
from rag.ingestion.extract_tests import get_test_files
from rag.ingestion.ast_extractor import extract_snippets
from rag.ingestion.distiller import distill
from rag.ingestion.chunker import chunk_code, chunk_docs
from rag.ingestion.embedder import embed
from rag.storage.factory import get_vector_store
from config.settings import settings
import subprocess


def run_pipeline():
    print("🚀 Running Agno Pipeline Orchestrator...")
    repo = clone_repo()
    print(f"📦 Repo cloned/located at {repo}")
    files = get_test_files(repo)
    print(f"📂 Found {len(files)} test files.")

    all_chunks = []
    all_metadata = []

    for file in files:
        with open(file, "r") as f:
            code = f.read()

        snippets = extract_snippets(code)

        for dict_snippet in snippets:
            try:
                # Discard raw source and extract distilled test code body
                distilled = distill(dict_snippet["code"])
                chunks = chunk_code(distilled, context=dict_snippet, max_lines=60)
                for chunk in chunks:
                    all_chunks.append(chunk)
                    # Relativize path for cleaner metadata
                    rel_path = os.path.relpath(file, start=repo)
                    all_metadata.append({
                        "source": rel_path,
                        "framework": "agno",
                        "type": "test_snippet",
                        "chunk_type": "full_function"
                    })
            except Exception:
                pass  # skip unparseable snippets

    if settings.ingest_docs:
        print("📚 Ingesting official docs...")
        docs_dir = "data/agno_docs"
        if not os.path.exists(docs_dir):
            print(" cloning https://github.com/agno-agi/docs to data/agno_docs")
            subprocess.run(["git", "clone", "https://github.com/agno-agi/docs", docs_dir])
        else:
            print(f"📦 Docs already cloned at {docs_dir}")
        
        doc_files = []
        for root, _, fnames in os.walk(docs_dir):
            for fname in fnames:
                if fname.endswith(".md") or fname.endswith(".mdx"):
                    doc_files.append(os.path.join(root, fname))
        
        print(f"📂 Found {len(doc_files)} doc files.")
        for d_file in doc_files:
            try:
                with open(d_file, "r", encoding="utf-8") as f:
                    content = f.read()
                d_chunks = chunk_docs(content)
                for chunk in d_chunks:
                    all_chunks.append(chunk)
                    rel_path = os.path.relpath(d_file, start=docs_dir)
                    all_metadata.append({
                        "source": rel_path,
                        "framework": "agno",
                        "type": "docs_section",
                        "chunk_type": "docs_section" # ensure metadata matches the requirement
                    })
            except Exception:
                pass

    if not all_chunks:
        print("No chunks to insert!")
        return

    print(f"🧩 Start embedding {len(all_chunks)} chunks...")
    embeddings = embed(all_chunks)
    print("✅ Embeddings extracted successfully.")

    # Use the factory to get the configured vector store
    store = get_vector_store()
    store.connect()
    store.create_collection()

    # Insert in batches to respect ChromaDB max batch size (5461)
    BATCH_SIZE = 5000
    total = len(all_chunks)
    for i in range(0, total, BATCH_SIZE):
        end = min(i + BATCH_SIZE, total)
        store.insert(
            texts=all_chunks[i:end],
            vectors=embeddings[i:end],
            metadata=all_metadata[i:end],
        )
        print(f"  📥 Inserted batch {i // BATCH_SIZE + 1} "
              f"({end}/{total} chunks)")

    print(f"🎉 Successfully ingested {total} chunks into "
          f"{store.__class__.__name__}.")


if __name__ == "__main__":
    run_pipeline()
