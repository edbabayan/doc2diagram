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

    def _update_hierarchy(self, current_meta: Dict[str, str], label: str, header_text: str) -> Dict[str, str]:
        """
        Updates hierarchy for the current level, pruning deeper levels.
        """
        current_level = self.splitting_headers.index((self.label_to_tag[label], label))
        new_meta = {
            k: v for k, v in current_meta.items()
            if self.splitting_headers.index((self.label_to_tag[k], k)) < current_level
        }
        new_meta[label] = header_text
        return new_meta

    def _html_table_to_markdown(self, table: Tag) -> str:
        """
        Converts an HTML table to Markdown format.

        Args:
            table (Tag): BeautifulSoup Tag containing the table

        Returns:
            str: Markdown formatted table
        """
        if not table:
            return ""

        # Extract table headers
        headers = []
        header_row = table.find('tr')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

        # If no headers found, try to determine from first row
        if not headers and table.find('tr'):
            first_row = table.find_all('tr')[0]
            headers = [td.get_text(strip=True) for td in first_row.find_all('td')]

        # If still no headers, create generic ones
        if not headers:
            return ""

        # Start building markdown table
        markdown_table = []

        # Add header row
        markdown_table.append("| " + " | ".join(headers) + " |")

        # Add separator row
        markdown_table.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Add data rows (skip the header row if it exists)
        rows = table.find_all('tr')
        start_idx = 1 if headers and len(rows) > 0 else 0

        for row in rows[start_idx:]:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = [cell.get_text(strip=True) for cell in cells]
                # Make sure the row has the right number of cells
                while len(row_data) < len(headers):
                    row_data.append("")
                markdown_table.append("| " + " | ".join(row_data[:len(headers)]) + " |")

        # Extract any attachments within the table
        attachments = []
        for ac_image in table.find_all("ac:image"):
            attachment = ac_image.find("ri:attachment")
            if attachment and attachment.has_attr("ri:filename"):
                attachments.append(f"[Attachment] {attachment['ri:filename']}")

        # Also check for ac:link attachments within tables
        for ac_link in table.find_all("ac:link"):
            attachment = ac_link.find("ri:attachment")
            if attachment and attachment.has_attr("ri:filename"):
                attachments.append(f"[Attachment] {attachment['ri:filename']}")

        # Add attachments if found
        if attachments:
            markdown_table.append("")  # Add a blank line
            markdown_table.append("**Attachments:**")
            markdown_table.extend(attachments)

        return "\n".join(markdown_table)

    def _collect_chunk_content(self, start_header: Tag, current_level: int) -> str:
        """
        Collects all content below a header until a header of same or higher level is found.
        Converts HTML tables to markdown format and preserves attachments.
        """
        content_parts = []
        attachments = []

        for sibling in start_header.find_next_siblings():
            # If we hit a header of same or higher level, stop
            if isinstance(sibling, Tag) and sibling.name in self.header_tags:
                sibling_level = self.splitting_headers.index((sibling.name, self.header_tags[sibling.name]))
                if sibling_level <= current_level:
                    break

            # Handle tables - convert to markdown
            if isinstance(sibling, Tag) and sibling.name == 'table':
                markdown_table = self._html_table_to_markdown(sibling)
                if markdown_table:
                    content_parts.append(markdown_table)
            # Handle regular text content and collect attachments
            elif isinstance(sibling, Tag):
                text_part = sibling.get_text(strip=True)
                if text_part:
                    content_parts.append(text_part)

                # Check for ac:image attachments
                for ac_image in sibling.find_all("ac:image"):
                    attachment = ac_image.find("ri:attachment")
                    if attachment and attachment.has_attr("ri:filename"):
                        url = attachment['ri:filename']
                        # If the URL contains a download path, extract the full URL
                        if 'download/attachments' in url:
                            url = url
                        else:
                            url = f"ri:attachment:{url}"
                        attachments.append(f"[Attachment] {url}")

                # Check for ac:link attachments
                for ac_link in sibling.find_all("ac:link"):
                    attachment = ac_link.find("ri:attachment")
                    if attachment and attachment.has_attr("ri:filename"):
                        url = attachment['ri:filename']
                        # If the URL contains a download path, extract the full URL
                        if 'download/attachments' in url:
                            url = url
                        else:
                            url = f"ri:attachment:{url}"
                        attachments.append(f"[Attachment] {url}")

            # Also check for standalone attachments
            elif str(sibling).strip().startswith('[Attachment]'):
                attachments.append(str(sibling).strip())

        # Combine all content
        result = "\n\n".join(filter(None, content_parts))

        # Add attachments at the end if they weren't already included in the table
        if attachments and not any("[Attachment]" in part for part in content_parts):
            if result:
                result += "\n\n**Attachments:**\n"
            else:
                result = "**Attachments:**\n"
            result += "\n".join(attachments)

        return result.strip()

    def _extract_attachments_from_content(self, content: str) -> List[str]:
        """
        Extracts attachment URLs from content.

        Args:
            content (str): Content possibly containing attachment references

        Returns:
            List[str]: List of attachment references
        """
        import re
        attachment_pattern = r'\[Attachment\](.*?)(?=\[Attachment\]|$)'
        matches = re.findall(attachment_pattern, content, re.DOTALL)
        return [f"[Attachment]{match.strip()}" for match in matches if match.strip()]

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

            current_meta = self._update_hierarchy(current_meta, label, header_text)
            content = self._collect_chunk_content(header, current_level)
            if not content:
                content = header_text

            logger.info(f"Creating chunk: {header_text}")

            chunks.append({
                "hierarchy": current_meta.copy(),
                "page_content": content,
            })

        return chunks