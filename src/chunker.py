import re
from typing import List, Dict
from collections import defaultdict

from langchain.text_splitter import HTMLHeaderTextSplitter


def hierarchical_title_chunking(text: str) -> List[Dict]:
    lines = text.splitlines()
    chunks = []
    stack = []

    for line in lines:
        header_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()

            # Pop deeper or equal level headings
            while stack and stack[-1]['level'] >= level:
                stack.pop()

            new_chunk = {
                "title": title,
                "level": level,
                "chunk_text": "",
                "child_chunks": []
            }

            if stack:
                stack[-1]['child_chunks'].append(new_chunk)
            else:
                chunks.append(new_chunk)

            stack.append(new_chunk)
        else:
            if stack:
                stack[-1]['chunk_text'] += line + '\n'

    return chunks


def html_chunking(html: str, splitting_headers: list[tuple[str, str]]) -> List[str]:
    header_splitter = HTMLHeaderTextSplitter(headers_to_split_on=splitting_headers)
    chunks = header_splitter.split_text(html)

    merged = defaultdict(list)
    for chunk in chunks:
        key = tuple(sorted(chunk.metadata.items()))  # Use metadata as grouping key
        merged[key].append(chunk.page_content.strip())

    # Combine the chunks per header
    final_chunks = []
    for metadata_tuple, content_list in merged.items():
        metadata_dict = dict(metadata_tuple)
        combined_content = "\n".join(content_list)
        final_chunks.append({"metadata": metadata_dict, "page_content": combined_content})

    return final_chunks