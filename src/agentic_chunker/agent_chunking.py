import json

from src.config import CFG
from src.agentic_chunker.chunker import chunk_page
from src.agentic_chunker.utils import download_local_llm

with open(CFG.tree_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)


download_local_llm(CFG.local_llm_model)


def process_confluence_tree(tree, process_function, parent_path=""):
    """
    Recursively traverse the Confluence page tree and apply a process function to each page.

    Args:
        tree: The Confluence page tree or a subtree
        process_function: A function that takes a page and its path as arguments
        parent_path: Path string to keep track of page hierarchy (for display purposes)
    """
    # If tree is a list (like at the root level), process each item
    if isinstance(tree, list):
        for item in tree:
            process_confluence_tree(item, process_function, parent_path)
        return

    # Extract page information
    page_id = tree.get("id", "unknown")
    page_title = tree.get("title", "Untitled")

    # Build the current path
    current_path = f"{parent_path}/{page_title}" if parent_path else page_title

    # Process the current page
    process_function(tree, current_path)

    # Process content sections if they exist
    content_sections = tree.get("content", [])
    for section in content_sections:
        # You could also process individual content sections if needed
        process_function(section, f"{current_path}/content")
        pass

    # Recursively process child pages
    child_pages = tree.get("child_pages", [])
    for child in child_pages:
        process_confluence_tree(child, process_function, current_path)


# Example usage: Print all page titles with their paths
def print_page_info(page, path):
    """Example process function that prints page ID and title"""
    split_text = page.get("content", [])
    project_name = page.get("project_name", "unknown")
    for chunk in split_text:
        chunk_hierarchy = chunk.get("hierarchy", {})
        chunk_text = chunk.get("page_content", "")
        chunks_list = chunk_page(chunk_text, chunk_hierarchy, project_name)

    print(f"Page: {path} (ID: {page.get('id', 'unknown')})")


# Process the tree
print("Processing Confluence page tree...")
process_confluence_tree(data, print_page_info)