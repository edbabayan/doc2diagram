from bs4 import BeautifulSoup, Tag


def header_chunker(html: str, splitting_headers) -> list[dict]:
    soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")

    # Clean headers
    for tag_name, _ in splitting_headers:
        for tag in soup.find_all(tag_name):
            for br in tag.find_all("br"):
                br.extract()
            tag.string = tag.get_text(strip=True)

    header_tags = {tag: label for tag, label in splitting_headers}
    label_to_tag = {label: tag for tag, label in splitting_headers}
    headers = soup.find_all(list(header_tags.keys()))

    chunks = []
    current_meta = {}

    for i, header in enumerate(headers):
        tag_name = header.name
        header_text = header.get_text(strip=True)
        label = header_tags[tag_name]
        current_level = splitting_headers.index((tag_name, label))

        if not header_text:
            continue  # Skip empty headers

        # Clean metadata from deeper levels
        current_meta = {
            k: v for k, v in current_meta.items()
            if splitting_headers.index((label_to_tag[k], k)) < current_level
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
                sibling_level = splitting_headers.index((sibling.name, header_tags[sibling.name]))
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