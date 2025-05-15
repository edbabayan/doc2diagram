from loguru import logger
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Tuple, Any


class HTMLParser:
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

    def _process_cell_content(self, cell: Tag) -> Tuple[str, List[Dict[str, str]]]:
        """
        Processes a table cell's content, extracting rich elements like links and attachments.

        Args:
            cell (Tag): BeautifulSoup Tag containing a table cell

        Returns:
            Tuple[str, List[Dict[str, str]]]: Processed cell content and list of found attachments
        """
        cell_content = ""
        attachments = []

        # Process hyperlinks (a tags)
        links = cell.find_all('a')
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True) or href
            cell_content += f"[{text}]({href})"

        # Process attachments in ac:link tags
        ac_links = cell.find_all("ac:link")
        for ac_link in ac_links:
            attachment = ac_link.find("ri:attachment")
            if attachment and attachment.has_attr("ri:filename"):
                filename = attachment['ri:filename']
                short_name = filename.split('/')[-1].split('?')[0]

                # Add to attachments list as a dict
                attachments.append({
                    "file_name": short_name,
                })

                # Get the plain text body if available
                plain_text_body = ac_link.find("ac:plain-text-link-body")
                if plain_text_body and plain_text_body.get_text(strip=True):
                    cell_content += f"[{plain_text_body.get_text(strip=True)}]({filename})"
                else:
                    # Use short filename for display
                    cell_content += f"[📎 {short_name}]"

        # Process images in ac:image tags
        ac_images = cell.find_all("ac:image")
        for ac_image in ac_images:
            attachment = ac_image.find("ri:attachment")
            if attachment and attachment.has_attr("ri:filename"):
                filename = attachment['ri:filename']
                short_name = filename.split('/')[-1].split('?')[0]

                # Add to attachments list as a dict
                attachments.append({
                    "file_name": short_name,
                })

                cell_content += f"![🖼️ {short_name}]"

        # Process page links
        ri_pages = cell.find_all("ri:page")
        for page in ri_pages:
            if page.has_attr("ri:content-title"):
                title = page["ri:content-title"]
                cell_content += f"[📄 {title}]"

        # Process lists within cells
        lists = cell.find_all(['ul', 'ol'])
        for list_elem in lists:
            list_items = list_elem.find_all('li')
            for item in list_items:
                # Check for attachments in list items
                item_attachments = item.find_all("ri:attachment")
                if item_attachments:
                    for attachment in item_attachments:
                        if attachment.has_attr("ri:filename"):
                            filename = attachment['ri:filename']
                            short_name = filename.split('/')[-1].split('?')[0]

                            # Add to attachments list as a dict
                            attachments.append({
                                "file_name": short_name,
                            })

                            cell_content += f"- [📎 {short_name}]\n"

                # Check for links in list items
                item_links = item.find_all('a')
                if item_links:
                    for link in item_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True) or href
                        cell_content += f"- [{text}]({href})\n"

                # If no special content, just get the text
                if not item_attachments and not item_links:
                    item_text = item.get_text(strip=True)
                    if item_text:
                        cell_content += f"- {item_text}\n"

        # If no special content was found, use the text content
        if not cell_content:
            cell_content = cell.get_text(strip=True)

        return cell_content, attachments

    def _html_table_to_markdown(self, table: Tag) -> Tuple[str, List[Dict[str, str]]]:
        """
        Converts an HTML table to Markdown format, preserving links and attachments.

        Args:
            table (Tag): BeautifulSoup Tag containing the table

        Returns:
            Tuple[str, List[Dict[str, str]]]: Markdown formatted table and list of found attachments
        """
        if not table:
            return "", []

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
            return "", []

        # Start building markdown table
        markdown_table = []

        # Add header row
        markdown_table.append("| " + " | ".join(headers) + " |")

        # Add separator row
        markdown_table.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Add data rows (skip the header row if it exists)
        rows = table.find_all('tr')
        start_idx = 1 if headers and len(rows) > 0 else 0

        # Collect all attachments found in the table
        all_attachments = []

        for row in rows[start_idx:]:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = []

                for cell in cells:
                    # Use the helper method to process this cell
                    cell_content, cell_attachments = self._process_cell_content(cell)
                    row_data.append(cell_content)
                    all_attachments.extend(cell_attachments)

                # Make sure the row has the right number of cells
                while len(row_data) < len(headers):
                    row_data.append("")

                markdown_table.append("| " + " | ".join(row_data[:len(headers)]) + " |")

        # Add attachments section note in the markdown table if found
        if all_attachments:
            markdown_table.append("")  # Add a blank line
            markdown_table.append("**Attachments available**")

        return "\n".join(markdown_table), all_attachments

    def _collect_chunk_content(self, start_header: Tag, current_level: int) -> Tuple[str, List[Dict[str, str]]]:
        """
        Collects all content below a header until a header of same or higher level is found.
        Converts HTML tables to markdown format and preserves attachments.

        Returns:
            Tuple[str, List[Dict[str, str]]]: Content and list of attachments as dictionaries
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
                markdown_table, table_attachments = self._html_table_to_markdown(sibling)
                if markdown_table:
                    content_parts.append(markdown_table)
                    attachments.extend(table_attachments)
            # Handle regular text content and collect attachments
            elif isinstance(sibling, Tag):
                text_part = sibling.get_text(strip=True)
                if text_part:
                    content_parts.append(text_part)

                # Check for ac:image attachments
                for ac_image in sibling.find_all("ac:image"):
                    attachment = ac_image.find("ri:attachment")
                    if attachment and attachment.has_attr("ri:filename"):
                        filename = attachment['ri:filename']
                        short_name = filename.split('/')[-1].split('?')[0]

                        # Add to attachments list as a dict
                        attachments.append({
                            "file_name": short_name,
                        })

                        content_parts.append(f"![🖼️ {short_name}]")

                # Check for ac:link attachments
                for ac_link in sibling.find_all("ac:link"):
                    attachment = ac_link.find("ri:attachment")
                    if attachment and attachment.has_attr("ri:filename"):
                        filename = attachment['ri:filename']
                        short_name = filename.split('/')[-1].split('?')[0]

                        # Add to attachments list as a dict
                        attachments.append({
                            "file_name": short_name,
                        })

                        # Get the plain text body if available
                        plain_text_body = ac_link.find("ac:plain-text-link-body")
                        if plain_text_body and plain_text_body.get_text(strip=True):
                            content_parts.append(f"[{plain_text_body.get_text(strip=True)}]")
                        else:
                            content_parts.append(f"[📎 {short_name}]")

        # Combine all content
        result = "\n\n".join(filter(None, content_parts))

        return result.strip(), attachments

    def chunk(self, html: str) -> List[Dict[str, Any]]:
        """
        Chunks the HTML document into structured sections based on headers.

        Args:
            html (str): Raw HTML content to be chunked.

        Returns:
            List[Dict[str, Any]]: Chunks with 'hierarchy', 'page_content', and 'attachments'.
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
            content, attachments = self._collect_chunk_content(header, current_level)
            if not content:
                content = header_text

            logger.info(f"Creating chunk: {header_text}")

            chunks.append({
                "hierarchy": current_meta.copy(),
                "page_content": content,
                "attachments": attachments
            })

        return chunks