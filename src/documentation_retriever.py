import os
import json

from loguru import logger
from dotenv import load_dotenv
from atlassian import Confluence

from src.html_parser import HTMLParser
from src.utils import extract_attached_filenames, extract_attachments_by_name, clean_header_tags


class ConfluencePageTreeBuilder:
    def __init__(self, confluence_client: Confluence, splitting_headers: list[tuple[str, str]], attachments_dir=None):
        self.confluence = confluence_client
        self.parser = HTMLParser(splitting_headers)
        self.attachments_dir = attachments_dir
        os.makedirs(attachments_dir, exist_ok=True)

    def search_pages(self, space=None, title=None, label=None, limit=None):
        query_parts = ['type = "page"']
        if title:
            query_parts.append(f'title ~ "{title}"')
        if space:
            query_parts.append(f'space = "{space}"')
        if label:
            query_parts.append(f'label = "{label}"')

        cql_query = " AND ".join(query_parts)
        logger.debug(f"Executing CQL search: {cql_query}")

        try:
            return self.confluence.cql(cql=cql_query, limit=limit)
        except Exception as query_error:
            logger.error(f"CQL search failed: {query_error}")
            raise

    def fetch_page_with_children(self, page_id, include_children=True, project_name=None):
        try:
            # Get the page content with its history
            page = self.confluence.get_page_by_id(page_id, expand="body.storage,history,history.lastUpdated")
        except Exception as fetch_error:
            logger.error(f"Error fetching page ID {page_id}: {fetch_error}")
            return {}

        title = page["title"]
        html = page["body"]["storage"]["value"]

        attachments = self.confluence.get_attachments_from_content(page_id)

        # Download each attachment
        for attachment in attachments.get("results", []):
            attachment_filename = attachment["title"]

            self.confluence.download_attachments_from_page(page_id,
                                                           filename=attachment_filename,
                                                           path=self.attachments_dir)

        # Extract the last modification date and author
        last_modified = None
        last_modified_by = None

        # First try to get the lastUpdated information directly
        if "history" in page and "lastUpdated" in page["history"]:
            history_data = page["history"]["lastUpdated"]
            if "when" in history_data:
                last_modified = history_data["when"]
            if "by" in history_data and "displayName" in history_data["by"]:
                last_modified_by = history_data["by"]["displayName"]

        # If not found, try to fetch history separately
        if not last_modified:
            try:
                history = self.confluence.get_page_by_id(page_id, expand="history.lastUpdated")
                if "history" in history and "lastUpdated" in history["history"]:
                    history_data = history["history"]["lastUpdated"]
                    if "when" in history_data:
                        last_modified = history_data["when"]
                    if "by" in history_data and "displayName" in history_data["by"]:
                        last_modified_by = history_data["by"]["displayName"]
            except Exception as history_error:
                logger.warning(f"Failed to fetch history for page {page_id}: {history_error}")

        filenames = extract_attached_filenames(html)
        attachments = extract_attachments_by_name(self.confluence, page_id, filenames)

        cleaned_html = clean_header_tags(html)
        chunks = self.parser.chunk(cleaned_html)


        logger.debug(f"Fetched page '{title}' (ID: {page_id}), children: {include_children}")

        result = {
            "id": page_id,
            "title": title,
            "content": chunks,
            "attachments": attachments,
            "last_modified": last_modified,
            "last_modified_by": last_modified_by,
            "child_pages": [],
        }

        # Add project_name to all pages if provided
        if project_name:
            result["project_name"] = project_name

        if include_children:
            try:
                children = self.confluence.get_child_pages(page_id)
                result["child_pages"] = [
                    self.fetch_page_with_children(child["id"], include_children, project_name)
                    for child in children
                ]
            except Exception as child_error:
                logger.warning(f"Failed to fetch children for page {page_id}: {child_error}")

        return result

    def get_page_tree(self, pages_response, include_children=True, project_name=None):
        logger.info("Building page tree from search results...")
        return [
            self.fetch_page_with_children(page["content"]["id"], include_children, project_name)
            for i, page in enumerate(pages_response.get("results", []))
        ]

    @staticmethod
    def save_tree_to_json(tree_data, output_file):
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(tree_data, f, ensure_ascii=False, indent=2)
            logger.success(f"Page tree saved to {output_file}")
        except Exception as json_error:
            logger.error(f"Failed to save JSON: {json_error}")


if __name__ == "__main__":
    from src.config import CFG

    # Load environment variables
    load_dotenv(dotenv_path=CFG.env_variable_file)
    logger.info(f"Loaded environment variables from {CFG.env_variable_file}")

    try:
        confluence = Confluence(
            url=os.environ["CONFLUENCE_URL"],
            username=os.environ["CONFLUENCE_USERNAME"],
            password=os.environ["CONFLUENCE_API_KEY"],
        )
        logger.success("Confluence client initialized successfully.")
    except Exception as init_error:
        logger.error(f"Failed to initialize Confluence client: {init_error}")
        raise

    builder = ConfluencePageTreeBuilder(confluence, CFG.HEADERS_TO_SPLIT_ON, CFG.attachments_dir)

    try:
        _project_name = "EPMRPP"

        results = builder.search_pages(space=_project_name, title="UX / UI")
        tree = builder.get_page_tree(results, project_name=_project_name)
        builder.save_tree_to_json(tree, CFG.tree_file_path)
    except Exception as run_error:
        logger.critical(f"Execution failed: {run_error}")