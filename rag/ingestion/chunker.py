def chunk_code(snippet: str, max_lines=20):
    lines = snippet.split("\n")
    chunks = []

    for i in range(0, len(lines), max_lines):
        chunk = "\n".join(lines[i:i+max_lines])
        if chunk.strip():
            chunks.append(chunk)

    return chunks
