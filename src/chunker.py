from loguru import logger
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Tuple


class HTMLChunker:
    def __init__(self, splitting_headers: List[Tuple[str, str]]):
        """
        Initializes the chunker with header configuration only.

        Args:
            splitting_headers (List[Tuple[str, str]]):
                List of tuples like [("h1", "section"), ("h2", "subsection")].
        """
        self.splitting_headers = splitting_headers
        self.header_tags = {tag: label for tag, label in splitting_headers}
        self.label_to_tag = {label: tag for tag, label in splitting_headers}

    def _clean_headers(self, soup: BeautifulSoup):
        """
        Cleans <br> tags and whitespace in header tags.
        """
        for tag_name, _ in self.splitting_headers:
            for tag in soup.find_all(tag_name):
                for br in tag.find_all("br"):
                    br.extract()
                tag.string = tag.get_text(strip=True)

    def _update_metadata(self, current_meta: Dict[str, str], label: str, header_text: str) -> Dict[str, str]:
        """
        Updates metadata for the current level, pruning deeper levels.
        """
        current_level = self.splitting_headers.index((self.label_to_tag[label], label))
        new_meta = {
            k: v for k, v in current_meta.items()
            if self.splitting_headers.index((self.label_to_tag[k], k)) < current_level
        }
        new_meta[label] = header_text
        return new_meta

    def _collect_chunk_content(self, start_header: Tag, current_level: int) -> str:
        """
        Collects all content below a header until a header of same or higher level is found.
        """
        content_parts = []

        for sibling in start_header.find_next_siblings():
            if isinstance(sibling, Tag) and sibling.name in self.header_tags:
                sibling_level = self.splitting_headers.index((sibling.name, self.header_tags[sibling.name]))
                if sibling_level <= current_level:
                    break

            text_part = sibling.get_text(strip=True)
            if text_part:
                content_parts.append(text_part)

            for ac_image in sibling.find_all("ac:image"):
                attachment = ac_image.find("ri:attachment")
                if attachment and attachment.has_attr("ri:filename"):
                    content_parts.append(f"[Attachment] {attachment['ri:filename']}")

        return "\n".join(filter(None, content_parts)).strip()

    def chunk(self, html: str) -> List[Dict[str, str]]:
        """
        Chunks the HTML document into structured sections based on headers.

        Args:
            html (str): Raw HTML content to be chunked.

        Returns:
            List[Dict[str, str]]: Chunks with 'hierarchy' and 'page_content'.
        """
        soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
        self._clean_headers(soup)

        chunks = []
        current_meta = {}
        headers = soup.find_all(list(self.header_tags.keys()))

        for header in headers:
            tag_name = header.name
            header_text = header.get_text(strip=True)
            label = self.header_tags[tag_name]
            current_level = self.splitting_headers.index((tag_name, label))

            if not header_text:
                continue

            current_meta = self._update_metadata(current_meta, label, header_text)
            content = self._collect_chunk_content(header, current_level)
            if not content:
                content = header_text

            logger.info(f"Creating chunk: {header_text}")

            chunks.append({
                "hierarchy": current_meta.copy(),
                "page_content": content
            })

        return chunks
