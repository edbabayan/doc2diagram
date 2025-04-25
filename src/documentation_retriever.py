import os
import json
from dotenv import load_dotenv
from loguru import logger
from atlassian import Confluence

from src.config import CFG
from src.chunker import header_chunker
from src.utils import (
    extract_attached_filenames,
    extract_attachments_by_name,
    clean_header_tags,
)


# Load environment variables
dotenv_path = CFG.root / ".env"
load_dotenv(dotenv_path=dotenv_path)
logger.info(f"Loaded environment variables from {dotenv_path}")

# Initialize Confluence client
try:
    confluence = Confluence(
        url=os.environ["CONFLUENCE_URL"],
        username=os.environ["CONFLUENCE_USERNAME"],
        password=os.environ["CONFLUENCE_API_KEY"],
    )
    logger.success("Confluence client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Confluence client: {e}")
    raise


def search_pages(space=None, title=None, label=None, limit=None):
    """Search for Confluence pages using CQL query parameters."""
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
        return confluence.cql(cql=cql_query, limit=limit)
    except Exception as e:
        logger.error(f"CQL search failed: {e}")
        raise


def fetch_page_with_children(page_id, include_children=True):
    """Fetch page content and recursively fetch children if required."""
    try:
        page = confluence.get_page_by_id(page_id, expand="body.storage")
    except Exception as e:
        logger.error(f"Error fetching page ID {page_id}: {e}")
        return {}

    title = page["title"]
    html = page["body"]["storage"]["value"]

    filenames = extract_attached_filenames(html)
    attachments = extract_attachments_by_name(confluence, page_id, filenames)

    for name, url in zip(filenames, attachments):
        html = html.replace(name, url)

    cleaned_html = clean_header_tags(html)
    chunks = header_chunker(cleaned_html, CFG.HEADERS_TO_SPLIT_ON)

    logger.debug(f"Fetched page '{title}' (ID: {page_id}), children: {include_children}")

    result = {
        "id": page_id,
        "title": title,
        "content": chunks,
        "child_pages": [],
    }

    if include_children:
        try:
            children = confluence.get_child_pages(page_id)
            result["child_pages"] = [
                fetch_page_with_children(child["id"], include_children)
                for child in children
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch children for page {page_id}: {e}")

    return result


def get_page_tree(pages_response, include_children=True):
    """Process a list of page search results into full tree structure."""
    logger.info("Building page tree from search results...")
    return [
        fetch_page_with_children(page["content"]["id"], include_children)
        for page in pages_response.get("results", [])
    ]


def print_page_tree(pages, indent=0):
    """Print page titles as a tree structure."""
    for page in pages:
        logger.info("    " * indent + f"- {page['title']} (ID: {page['id']})")
        if page["child_pages"]:
            print_page_tree(page["child_pages"], indent + 1)


def save_tree_to_json(tree_data, output_file):
    """Save the tree structure to a JSON file."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tree_data, f, ensure_ascii=False, indent=2)
        logger.success(f"Page tree saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")


if __name__ == "__main__":
    logger.info("Starting Confluence page extraction...")

    try:
        results = search_pages(space="EPMRPP", title="UX / UI")
        tree = get_page_tree(results)
        print_page_tree(tree)
        save_tree_to_json(tree, CFG.root / "confluence_page_tree.json")
    except Exception as e:
        logger.critical(f"Execution failed: {e}")
