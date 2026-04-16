import os
from rag.ingestion.clone_repo import clone_repo
from rag.ingestion.extract_tests import get_test_files
from rag.ingestion.ast_extractor import extract_snippets
from rag.ingestion.distiller import distill
from rag.ingestion.chunker import chunk_code
from rag.ingestion.embedder import embed
from rag.storage.milvus_client import connect, create_collection, insert_batch

def run_pipeline():
    print("🚀 Running Agno Pipeline Orchestrator...")
    repo = clone_repo()
    print(f"📦 Repo cloned/located at {repo}")
    files = get_test_files(repo)
    print(f"📂 Found {len(files)} test files.")

    all_chunks = []
    all_sources = []
    all_frameworks = []
    all_types = []

    for file in files:
        with open(file, "r") as f:
            code = f.read()

        snippets = extract_snippets(code)

        for s in snippets:
            try:
                distilled = distill(s)
                chunks = chunk_code(distilled)
                for chunk in chunks:
                    all_chunks.append(chunk)
                    # Relativize path for cleaner metadata
                    rel_path = os.path.relpath(file, start=repo)
                    all_sources.append(rel_path)
                    all_frameworks.append("agno")
                    all_types.append("test_snippet")
            except Exception as e:
                pass # skip unparseable snippets

    if not all_chunks:
        print("No chunks to insert!")
        return

    print(f"🧩 Start embedding {len(all_chunks)} chunks...")
    embeddings = embed(all_chunks)
    print("✅ Embeddings extracted successfully.")

    connect()
    collection = create_collection()
    
    # Chunk ingestion in batches if too large, but Agno tests should be fine in one operation
    insert_batch(collection, embeddings, all_chunks, all_sources, all_frameworks, all_types)

    print(f"🎉 Successfully ingested {len(all_chunks)} chunks into Milvus.")

if __name__ == "__main__":
    run_pipeline()
