from loguru import logger
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Tuple, Any
import json
import urllib.parse


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

    @staticmethod
    def _extract_roadmap_data(soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], BeautifulSoup]:
        """
        Extracts Confluence roadmap macros data from the HTML and removes them from the soup.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the HTML

        Returns:
            Tuple[List[Dict[str, Any]], BeautifulSoup]: Tuple containing list of extracted roadmap data objects
            and the modified soup with roadmap macros removed
        """
        roadmaps = []
        roadmap_macros = soup.find_all('ac:structured-macro', {'ac:name': 'roadmap'})

        if not roadmap_macros:
            return roadmaps, soup

        logger.info(f"Found {len(roadmap_macros)} roadmap macro(s) in the HTML")

        for i, macro in enumerate(roadmap_macros):
            logger.info(f"Processing roadmap #{i + 1}")

            # Find the source parameter which contains the encoded JSON data
            source_param = macro.find('ac:parameter', {'ac:name': 'source'})

            if not source_param:
                logger.warning(f"Roadmap #{i + 1} has no source parameter")
                continue

            try:
                # URL decode the content
                encoded_json = source_param.text
                decoded_json = urllib.parse.unquote(encoded_json)

                # Parse the JSON data
                roadmap_data = json.loads(decoded_json)

                # Process the roadmap data
                processed_data = {
                    "type": "roadmap",
                    "title": roadmap_data.get('title', 'Unnamed Roadmap'),
                    "timeline": roadmap_data.get('timeline', {}),
                    "items": []
                }

                # Process lanes and bars (tasks)
                for lane in roadmap_data.get('lanes', []):
                    lane_title = lane.get('title', 'Unnamed Lane')

                    for bar in lane.get('bars', []):
                        processed_data["items"].append({
                            "lane": lane_title,
                            "title": bar.get('title', 'Unnamed Task'),
                            "description": bar.get('description', ''),
                            "start_date": bar.get('startDate', 'N/A'),
                            "duration": bar.get('duration', 0),
                            "row_index": bar.get('rowIndex', 0),
                            "id": bar.get('id', '')
                        })

                roadmaps.append(processed_data)
                logger.info(f"Successfully processed roadmap: {processed_data['title']}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data from roadmap #{i + 1}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing roadmap #{i + 1}: {str(e)}")

        # Remove all roadmap macros from the soup
        for macro in roadmap_macros:
            macro.decompose()

        logger.info(f"Removed {len(roadmap_macros)} roadmap macro(s) from the soup")

        return roadmaps, soup

    @staticmethod
    def _process_cell_content(cell: Tag) -> Tuple[str, List[Dict[str, str]]]:
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

    def _process_entire_body(self, soup: BeautifulSoup) -> Tuple[str, List[Dict[str, str]]]:
        """
        Process the entire body of HTML when no headers are present.
        Extracts content and attachments from the whole document.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the HTML

        Returns:
            Tuple[str, List[Dict[str, str]]]: Page content and list of attachments
        """
        content_parts = []
        attachments = []
        body = soup.body if soup.body else soup

        # Process all elements in the body
        for element in body.find_all(True):  # True selects all elements
            # Skip header tags that we're configured to use for chunking
            if element.name in self.header_tags:
                continue

            # Handle tables
            if element.name == 'table':
                markdown_table, table_attachments = self._html_table_to_markdown(element)
                if markdown_table:
                    content_parts.append(markdown_table)
                    attachments.extend(table_attachments)
                continue

            # Extract text content
            text = element.get_text(strip=True)
            if text and element.parent.name != 'table':  # Avoid duplicating table content
                content_parts.append(text)

            # Process attachments and links
            # Images
            for img in element.find_all("img"):
                src = img.get("src", "")
                alt = img.get("alt", "Image")
                if src:
                    content_parts.append(f"![{alt}]({src})")

            # Links
            for link in element.find_all("a"):
                href = link.get("href", "")
                text = link.get_text(strip=True) or href
                if href:
                    content_parts.append(f"[{text}]({href})")

            # Confluence-specific attachments (ac:image)
            for ac_image in element.find_all("ac:image"):
                attachment = ac_image.find("ri:attachment")
                if attachment and attachment.has_attr("ri:filename"):
                    filename = attachment['ri:filename']
                    short_name = filename.split('/')[-1].split('?')[0]
                    attachments.append({
                        "file_name": short_name,
                    })
                    content_parts.append(f"![🖼️ {short_name}]")

            # Confluence-specific links (ac:link)
            for ac_link in element.find_all("ac:link"):
                attachment = ac_link.find("ri:attachment")
                if attachment and attachment.has_attr("ri:filename"):
                    filename = attachment['ri:filename']
                    short_name = filename.split('/')[-1].split('?')[0]
                    attachments.append({
                        "file_name": short_name,
                    })
                    plain_text_body = ac_link.find("ac:plain-text-link-body")
                    if plain_text_body and plain_text_body.get_text(strip=True):
                        content_parts.append(f"[{plain_text_body.get_text(strip=True)}]({filename})")
                    else:
                        content_parts.append(f"[📎 {short_name}]")

        # Filter out empty strings and join
        filtered_content = list(filter(None, content_parts))
        result = "\n\n".join(filtered_content)

        return result.strip(), attachments

    @staticmethod
    def _roadmap_to_markdown(roadmap_data: Dict[str, Any]) -> str:
        """
        Converts roadmap data to a markdown representation.

        Args:
            roadmap_data (Dict[str, Any]): Processed roadmap data

        Returns:
            str: Markdown representation of the roadmap
        """
        markdown_parts = []

        # Add title and timeline info
        markdown_parts.append(f"# {roadmap_data['title']}")

        timeline = roadmap_data.get('timeline', {})
        if timeline:
            start_date = timeline.get('startDate', 'N/A')
            end_date = timeline.get('endDate', 'N/A')
            markdown_parts.append(f"**Timeline:** {start_date} to {end_date}")

        # Add items table
        items = roadmap_data.get('items', [])
        if items:
            markdown_parts.append("\n## Roadmap Items")

            # Get all unique keys from all items to use as column headers
            all_keys = set()
            for item in items:
                all_keys.update(item.keys())

            # Create the header row
            header_row = "| " + " | ".join(all_keys) + " |"
            markdown_parts.append(header_row)

            # Create the separator row
            separator_row = "| " + " | ".join(["------" for _ in all_keys]) + " |"
            markdown_parts.append(separator_row)

            # Add each item as a row
            for item in items:
                row_values = []
                for key in all_keys:
                    # Get value, replace newlines, and use 'N/A' if missing
                    value = item.get(key, 'N/A')
                    if isinstance(value, str):
                        value = value.replace('\n', ' ')
                    row_values.append(str(value))

                row = "| " + " | ".join(row_values) + " |"
                markdown_parts.append(row)

        return "\n".join(markdown_parts)

    def _extract_table_data(self, soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], BeautifulSoup]:
        """
        Extracts Confluence table macros data from the HTML and removes them from the soup.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the HTML

        Returns:
            Tuple[List[Dict[str, Any]], BeautifulSoup]: Tuple containing list of extracted table data objects
            and the modified soup with tables removed
        """
        tables_data = []

        # Look for both standard tables and table-chart macros
        standard_tables = soup.find_all('table')
        table_chart_macros = soup.find_all('ac:structured-macro', {'ac:name': 'table-chart'})
        table_filter_macros = soup.find_all('ac:structured-macro', {'ac:name': 'table-filter'})

        logger.info(f"Found {len(standard_tables)} standard tables in the HTML")
        logger.info(f"Found {len(table_chart_macros)} table-chart macros in the HTML")
        logger.info(f"Found {len(table_filter_macros)} table-filter macros in the HTML")

        # Process standard HTML tables
        for i, table in enumerate(standard_tables):
            logger.info(f"Processing standard table #{i + 1}")

            try:
                # Extract table headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

                # Extract table rows
                rows = []
                data_rows = table.find_all('tr')[1:] if headers else table.find_all('tr')

                for row in data_rows:
                    cells = row.find_all(['td', 'th'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    rows.append(row_data)

                table_data = {
                    "type": "standard_table",
                    "headers": headers,
                    "rows": rows,
                    "markdown": self._html_table_to_markdown(table)[0]  # Use existing method
                }

                tables_data.append(table_data)
                logger.info(f"Successfully processed standard table #{i + 1}")

            except Exception as e:
                logger.error(f"Error processing standard table #{i + 1}: {str(e)}")

        # Process table-chart macros
        for i, macro in enumerate(table_chart_macros):
            logger.info(f"Processing table-chart macro #{i + 1}")

            try:
                # Extract parameters from the macro
                parameters = {}
                for param in macro.find_all('ac:parameter'):
                    name = param.get('ac:name')
                    value = param.text
                    parameters[name] = value

                # Find the nested table within the rich-text-body
                rich_text_body = macro.find('ac:rich-text-body')
                nested_tables = []

                if rich_text_body:
                    # Try to find table-filter macro first
                    filter_macro = rich_text_body.find('ac:structured-macro', {'ac:name': 'table-filter'})

                    if filter_macro:
                        filter_rich_text = filter_macro.find('ac:rich-text-body')
                        if filter_rich_text:
                            nested_tables = filter_rich_text.find_all('table')
                    else:
                        # Look for direct tables
                        nested_tables = rich_text_body.find_all('table')

                for j, nested_table in enumerate(nested_tables):
                    # Process each nested table
                    table_markdown, _ = self._html_table_to_markdown(nested_table)

                    # Extract headers and rows
                    headers = []
                    rows = []

                    header_row = nested_table.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

                    data_rows = nested_table.find_all('tr')[1:] if headers else nested_table.find_all('tr')
                    for row in data_rows:
                        cells = row.find_all(['td', 'th'])
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        rows.append(row_data)

                    chart_data = {
                        "type": "table_chart",
                        "parameters": parameters,
                        "headers": headers,
                        "rows": rows,
                        "markdown": table_markdown
                    }

                    tables_data.append(chart_data)
                    logger.info(f"Successfully processed table-chart #{i + 1}, nested table #{j + 1}")

            except Exception as e:
                logger.error(f"Error processing table-chart macro #{i + 1}: {str(e)}")

        # Process standalone table-filter macros (if not already processed as part of table-chart)
        for i, macro in enumerate(table_filter_macros):
            # Skip if this macro is within a table-chart (already processed)
            if macro.parent and macro.parent.parent and macro.parent.parent.name == 'ac:structured-macro' and macro.parent.parent.get(
                    'ac:name') == 'table-chart':
                continue

            logger.info(f"Processing standalone table-filter macro #{i + 1}")

            try:
                # Extract parameters from the macro
                parameters = {}
                for param in macro.find_all('ac:parameter'):
                    name = param.get('ac:name')
                    value = param.text
                    parameters[name] = value

                # Find the nested table
                rich_text_body = macro.find('ac:rich-text-body')
                if rich_text_body:
                    nested_tables = rich_text_body.find_all('table')

                    for j, nested_table in enumerate(nested_tables):
                        # Process each nested table
                        table_markdown, _ = self._html_table_to_markdown(nested_table)

                        # Extract headers and rows
                        headers = []
                        rows = []

                        header_row = nested_table.find('tr')
                        if header_row:
                            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]

                        data_rows = nested_table.find_all('tr')[1:] if headers else nested_table.find_all('tr')
                        for row in data_rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            rows.append(row_data)

                        filter_data = {
                            "type": "table_filter",
                            "parameters": parameters,
                            "headers": headers,
                            "rows": rows,
                            "markdown": table_markdown
                        }

                        tables_data.append(filter_data)
                        logger.info(f"Successfully processed table-filter #{i + 1}, nested table #{j + 1}")

            except Exception as e:
                logger.error(f"Error processing table-filter macro #{i + 1}: {str(e)}")

        # Now remove all the tables from the soup
        # 1. Remove standard tables
        for table in standard_tables:
            table.decompose()
        logger.info(f"Removed {len(standard_tables)} standard tables from the soup")

        # 2. Remove table-chart macros
        for macro in table_chart_macros:
            macro.decompose()
        logger.info(f"Removed {len(table_chart_macros)} table-chart macros from the soup")

        # 3. Remove standalone table-filter macros
        standalone_filter_macros = []
        for macro in table_filter_macros:
            # Check if this is a standalone macro (not inside a table-chart)
            if not (macro.parent and macro.parent.parent and
                    macro.parent.parent.name == 'ac:structured-macro' and
                    macro.parent.parent.get('ac:name') == 'table-chart'):
                standalone_filter_macros.append(macro)
                macro.decompose()

        logger.info(f"Removed {len(standalone_filter_macros)} standalone table-filter macros from the soup")

        return tables_data, soup


    def chunk(self, html: str) -> List[Dict[str, Any]]:
        """
        Chunks the HTML document into structured sections based on headers.
        If no headers are found, the entire document is treated as a single chunk.
        Also extracts roadmap data from structured macros.

        Args:
            html (str): Raw HTML content to be chunked.

        Returns:
            List[Dict[str, Any]]: Chunks with 'hierarchy', 'page_content', and 'attachments'.
                                 Roadmap data is included as special chunks with 'type': 'roadmap'.
        """
        soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
        self._clean_headers(soup)

        chunks = []

        # First, extract any roadmaps from the document
        roadmaps, soup = self._extract_roadmap_data(soup)

        # Add roadmaps as special chunks
        for roadmap in roadmaps:
            # Convert the roadmap data to markdown for better readability
            roadmap_markdown = self._roadmap_to_markdown(roadmap)

            chunks.append({
                "hierarchy": {"roadmap": roadmap["title"]},
                "page_content": roadmap_markdown,
            })

            logger.info(f"Added roadmap chunk: {roadmap['title']}")

        # Next, extract table data
        tables, soup = self._extract_table_data(soup)

        # Add table data as special chunks
        for i, table in enumerate(tables):
            table_type = table.get("type", "unknown_table")
            table_title = f"Table {i + 1}"

            # Try to get a meaningful title from the parameters or context
            if table_type == "table_chart" and "column" in table.get("parameters", {}):
                table_title = f"Chart: {table['parameters']['column']}"
            elif table_type == "table_filter" and "sort" in table.get("parameters", {}):
                table_title = f"Filtered Table: {table['parameters']['sort']}"
            elif table.get("headers") and len(table.get("headers", [])) > 0:
                table_title = f"Table: {table['headers'][0]} and {len(table['headers']) - 1} other columns"

            chunks.append({
                "hierarchy": {"table": table_title},
                "page_content": table.get("markdown", ""),
                "data": {
                    "headers": table.get("headers", []),
                    "rows": table.get("rows", []),
                    "parameters": table.get("parameters", {})
                },
                "type": table_type
            })

            logger.info(f"Added table chunk: {table_title}")

        # Now process the regular content as before
        headers = soup.find_all(list(self.header_tags.keys()))

        # If no headers found, process the entire document as one chunk
        if not headers:
            logger.info("No headers found. Processing entire document as one chunk.")
            content, attachments = self._process_entire_body(soup)
            if content:
                chunks.append({
                    "hierarchy": {},  # Empty hierarchy since no headers
                    "page_content": content,
                    "attachments": attachments
                })
            return chunks

        # If headers are found, process as before
        current_meta = {}
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