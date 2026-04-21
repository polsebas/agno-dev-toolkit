from rag.storage.factory import get_vector_store
store = get_vector_store()

# Simulate a real developer query
from rag.ingestion.embedder import embed
q = embed(['how to create an agent with tools and memory'])[0]
results = store.search(q, top_k=5, min_score=0.0)
for r in results:
    print('---')
    print('score:', r['score'])
    print('type:', r.get('chunk_type'))
    print('source:', r['source'])
    print('text:', r['text'][:150])
