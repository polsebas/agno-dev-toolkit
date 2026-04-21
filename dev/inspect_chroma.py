import chromadb
from config.settings import settings

client = chromadb.PersistentClient(path=settings.chroma_persist_path)
collection = client.get_collection(settings.collection_name)

print(f"Collection count: {collection.count()}")

# Peek at 5 items
results = collection.peek(limit=5)
for i in range(len(results['ids'])):
    print("-" * 40)
    print(f"ID: {results['ids'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    print(f"Content: {results['documents'][i][:200]}...")
