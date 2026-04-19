def chunk_code(snippet: str, context: dict = None, max_lines=60):
    context = context or {}
    class_name = context.get("class_name")
    setup_code = context.get("setup_code")
    signature = context.get("signature", "")
    
    prefix_parts = []
    if class_name:
        prefix_parts.append(f"class {class_name}:")
    if setup_code:
        if class_name:
            indented_setup = "\n".join(f"    {line}" for line in setup_code.split("\n") if line)
            prefix_parts.append(indented_setup)
        else:
            prefix_parts.append(setup_code)
            
    # Always ensure two newlines after prefix if it exists to separate it clearly
    prefix_str = "\n".join(prefix_parts) + "\n\n" if prefix_parts else ""
    
    indent_prefix = "    " if class_name else ""
    
    lines = snippet.split("\n")
    
    if len(lines) <= max_lines:
        indented_snippet = "\n".join(f"{indent_prefix}{line}" if line else "" for line in lines)
        return [prefix_str + indented_snippet]
        
    chunks = []
    current_block = []
    
    for line in lines:
        current_block.append(line)
        if len(current_block) >= max_lines:
            split_idx = -1
            for i in range(len(current_block)-1, 0, -1):
                if current_block[i].strip() == "":
                    split_idx = i
                    break
            
            if split_idx != -1:
                chunk_lines = current_block[:split_idx]
                current_block = current_block[split_idx+1:]
            else:
                chunk_lines = current_block
                current_block = []
                
            chunks.append(chunk_lines)

    if current_block:
        chunks.append(current_block)
        
    final_chunks = []
    for i, c_lines in enumerate(chunks):
        indented_lines = "\n".join(f"{indent_prefix}{l}" if l else "" for l in c_lines)
        
        if i == 0:
            final_text = prefix_str + indented_lines
        else:
            indented_sig = "\n".join(f"{indent_prefix}{l}" if l else "" for l in signature.split("\n"))
            final_text = prefix_str + indented_sig + "\n" + indented_lines
            
        if final_text.strip():
            final_chunks.append(final_text)
            
    return final_chunks


def chunk_docs(content: str, max_lines=50):
    import re
    chunks = []
    # Split by ## headings
    # (?=^## ) with MULTILINE splits right before ##
    sections = re.split(r'(?m)^(?=## )', content)
    for section in sections:
        if not section.strip():
            continue
        lines = section.split('\n')
        if len(lines) <= max_lines:
            chunks.append(section.strip())
        else:
            # Further split by blank lines if it exceeds max_lines
            current_chunk = []
            current_length = 0
            # A blank line regex
            paragraphs = re.split(r'(?m)^\s*$', section)
            for p in paragraphs:
                p_lines = p.strip('\n').split('\n')
                if current_length + len(p_lines) > max_lines and current_chunk:
                    chunks.append('\n'.join(current_chunk).strip())
                    current_chunk = p_lines
                    current_length = len(p_lines)
                else:
                    if current_chunk:
                        current_chunk.append('') # keep blank line for separation
                    current_chunk.extend(p_lines)
                    current_length += len(p_lines) + (1 if current_length > 0 else 0)
            if current_chunk:
                chunks.append('\n'.join(current_chunk).strip())
    
    return [c for c in chunks if c.strip()]
