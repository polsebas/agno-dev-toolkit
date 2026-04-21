import ast
from rag.ingestion.ast_extractor import extract_snippets
from rag.ingestion.distiller import distill
from rag.ingestion.chunker import chunk_code

code = """
class TestFoo:
    def setUp(self):
        self.val = 1
        
    def fixture_db(self):
        return {}

    def test_something(self):
        assert self.val == 1
        a = 1
        b = 2

    async def test_async_something(self):
        pass
"""

snippets = extract_snippets(code)
for s in snippets:
    print(f"--- SNIPPET ({s['signature']}) ---")
    d = distill(s["code"])
    chunks = chunk_code(d, context=s)
    for i, c in enumerate(chunks):
        print(f"Chunk {i}:")
        print(c)
        print("~")
