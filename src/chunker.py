import re
from typing import List, Dict
from collections import defaultdict
from bs4 import BeautifulSoup, Tag
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


def header_chunker(html: str, HEADERS_TO_SPLIT_ON) -> list[dict]:
    soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")

    # Clean headers
    for tag_name, _ in HEADERS_TO_SPLIT_ON:
        for tag in soup.find_all(tag_name):
            for br in tag.find_all("br"):
                br.extract()
            tag.string = tag.get_text(strip=True)

    header_tags = {tag: label for tag, label in HEADERS_TO_SPLIT_ON}
    label_to_tag = {label: tag for tag, label in HEADERS_TO_SPLIT_ON}
    headers = soup.find_all(list(header_tags.keys()))

    chunks = []
    current_meta = {}

    for i, header in enumerate(headers):
        tag_name = header.name
        header_text = header.get_text(strip=True)
        label = header_tags[tag_name]
        current_level = HEADERS_TO_SPLIT_ON.index((tag_name, label))

        if not header_text:
            continue  # Skip empty headers

        # Clean metadata from deeper levels
        current_meta = {
            k: v for k, v in current_meta.items()
            if HEADERS_TO_SPLIT_ON.index((label_to_tag[k], k)) < current_level
        }
        current_meta[label] = header_text

        # Get all next siblings
        siblings = list(header.find_next_siblings())

        # Skip this chunk if the first sibling is a header
        if siblings and isinstance(siblings[0], Tag) and siblings[0].name in header_tags and siblings[0].name != header_text:
            continue

        # Collect content until next header of same or higher level
        content_parts = []
        for sibling in siblings:
            if isinstance(sibling, Tag) and sibling.name in header_tags:
                sibling_level = HEADERS_TO_SPLIT_ON.index((sibling.name, header_tags[sibling.name]))
                if sibling_level <= current_level:
                    break

            # Normal text
            text_part = sibling.get_text(strip=True)
            if text_part:
                content_parts.append(text_part)

            # Extract Confluence-style attachments
            for ac_image in sibling.find_all("ac:image"):
                attachment = ac_image.find("ri:attachment")
                if attachment and attachment.has_attr("ri:filename"):
                    filename = attachment["ri:filename"]
                    content_parts.append(f"[Attachment] {filename}")

        text = "\n".join(filter(None, content_parts)).strip()
        if not text:
            text = header_text

        chunks.append({
            "metadata": current_meta.copy(),
            "page_content": text
        })

    return chunks