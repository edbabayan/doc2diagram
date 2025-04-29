import os
import json

from loguru import logger
from dotenv import load_dotenv
from atlassian import Confluence

from src.chunker import HTMLChunker
from src.meta_miner.metadata_parser import MetadataExtractor
from src.utils import extract_attached_filenames, extract_attachments_by_name, clean_header_tags


class ConfluencePageTreeBuilder:
    def __init__(self, confluence_client: Confluence, splitting_headers: list[tuple[str, str]]):
        self.confluence = confluence_client
        self.extractor = MetadataExtractor()
        self.chunker = HTMLChunker(splitting_headers)

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

    def fetch_page_with_children(self, page_id, include_children=True):
        try:
            page = self.confluence.get_page_by_id(page_id, expand="body.storage")
        except Exception as fetch_error:
            logger.error(f"Error fetching page ID {page_id}: {fetch_error}")
            return {}

        title = page["title"]
        html = page["body"]["storage"]["value"]

        filenames = extract_attached_filenames(html)
        attachments = extract_attachments_by_name(self.confluence, page_id, filenames)

        for name, url in zip(filenames, attachments):
            html = html.replace(name, url)

        cleaned_html = clean_header_tags(html)
        chunks = self.chunker.chunk(cleaned_html)

        logger.debug(f"Fetched page '{title}' (ID: {page_id}), children: {include_children}")

        meta_result = self.extractor.extract({'id': page_id,
                                         "title": title,
                                         "content": chunks})

        result = {
            "id": page_id,
            "title": title,
            "content": meta_result["content"],
            "child_pages": [],
        }

        if include_children:
            try:
                children = self.confluence.get_child_pages(page_id)
                result["child_pages"] = [
                    self.fetch_page_with_children(child["id"], include_children)
                    for child in children
                ]
            except Exception as child_error:
                logger.warning(f"Failed to fetch children for page {page_id}: {child_error}")

        return result

    def get_page_tree(self, pages_response, include_children=True):
        logger.info("Building page tree from search results...")
        return [
            self.fetch_page_with_children(page["content"]["id"], include_children)
            for page in pages_response.get("results", [])
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

    builder = ConfluencePageTreeBuilder(confluence, CFG.HEADERS_TO_SPLIT_ON)

    try:
        results = builder.search_pages(space="EPMRPP", title="UX / UI")
        tree = builder.get_page_tree(results)
        builder.save_tree_to_json(tree, CFG.root / "confluence_page_tree.json")
    except Exception as run_error:
        logger.critical(f"Execution failed: {run_error}")
