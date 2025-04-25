from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Tuple


def _clean_headers(soup: BeautifulSoup, splitting_headers: List[Tuple[str, str]]) -> None:
    """
    Cleans <br> tags and whitespace from specified header tags in the soup.
    """
    for tag_name, _ in splitting_headers:
        for tag in soup.find_all(tag_name):
            for br in tag.find_all("br"):
                br.extract()
            tag.string = tag.get_text(strip=True)


def _update_metadata(current_meta: dict, label: str, header_text: str,
                     splitting_headers: List[Tuple[str, str]], label_to_tag: dict) -> dict:
    """
    Updates metadata for the current header level, pruning deeper levels.
    """
    current_level = splitting_headers.index((label_to_tag[label], label))
    # Remove metadata from deeper levels
    new_meta = {
        k: v for k, v in current_meta.items()
        if splitting_headers.index((label_to_tag[k], k)) < current_level
    }
    new_meta[label] = header_text
    return new_meta


def _collect_chunk_content(start_header: Tag, header_tags: dict, current_level: int,
                           splitting_headers: List[Tuple[str, str]]) -> str:
    """
    Collects all sibling content until the next same or higher-level header.
    Also extracts filenames from Confluence-style attachments.
    """
    content_parts = []

    for sibling in start_header.find_next_siblings():
        if isinstance(sibling, Tag) and sibling.name in header_tags:
            sibling_level = splitting_headers.index((sibling.name, header_tags[sibling.name]))
            if sibling_level <= current_level:
                break

        # Collect visible text
        text_part = sibling.get_text(strip=True)
        if text_part:
            content_parts.append(text_part)

        # Check for Confluence attachments
        for ac_image in sibling.find_all("ac:image"):
            attachment = ac_image.find("ri:attachment")
            if attachment and attachment.has_attr("ri:filename"):
                content_parts.append(f"[Attachment] {attachment['ri:filename']}")

    return "\n".join(filter(None, content_parts)).strip()


def header_chunker(html: str, splitting_headers: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    """
    Splits HTML content into chunks based on header tags and levels.

    Args:
        html (str): The full HTML document.
        splitting_headers (list): List of tuples with (header_tag, metadata_label).

    Returns:
        list: List of dicts containing 'metadata' and 'page_content'.
    """
    soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
    _clean_headers(soup, splitting_headers)

    header_tags = {tag: label for tag, label in splitting_headers}
    label_to_tag = {label: tag for tag, label in splitting_headers}
    headers = soup.find_all(list(header_tags.keys()))

    chunks = []
    current_meta = {}

    for header in headers:
        tag_name = header.name
        header_text = header.get_text(strip=True)
        label = header_tags[tag_name]
        current_level = splitting_headers.index((tag_name, label))

        if not header_text:
            continue

        # Update metadata for this level
        current_meta = _update_metadata(current_meta, label, header_text, splitting_headers, label_to_tag)

        # Collect associated content
        page_content = _collect_chunk_content(header, header_tags, current_level, splitting_headers)

        # Fallback: Use header as content if section is empty
        if not page_content:
            page_content = header_text

        chunks.append({
            "metadata": current_meta.copy(),
            "page_content": page_content
        })

    return chunks
