import os
import uuid
import json

from tqdm import tqdm
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client.models import PointStruct

from src.config import CFG
from src.vector_database.utils import get_embedding_for_text
from src.vector_database.database_connection import ensure_collection_exists, connect_to_qdrant
from src.agentic_chunker.chunker import chunk_page
from src.agentic_chunker.utils import download_local_llm


# Load and parse the tree file
with open(CFG.tree_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Download local LLM if needed
download_local_llm(CFG.local_llm_model)


def process_confluence_tree(tree, process_function, openai_client, parent_path=""):
    """
    Recursively traverse the Confluence page tree and apply a process function to each page.

    Args:
        tree: The Confluence page tree or a subtree
        process_function: A function that takes a page and its path as arguments
        openai_client: An OpenAI client
        parent_path: Path string to keep track of page hierarchy (for display purposes)
    """
    # If tree is a list (like at the root level), process each item
    if isinstance(tree, list):
        for item in tree:
            process_confluence_tree(item, process_function, openai_client=openai_client, parent_path=parent_path)
        return

    # Extract page information
    page_id = tree.get("id", "unknown")
    page_title = tree.get("title", "Untitled")

    # Build the current path
    current_path = f"{parent_path}/{page_title}" if parent_path else page_title

    # Process the current page
    process_function(tree, current_path, openai_client=openai_client)

    # Process content sections if they exist
    content_sections = tree.get("content", [])
    for section in content_sections:
        process_function(section, f"{current_path}/content", openai_client=openai_client)

    # Recursively process child pages
    child_pages = tree.get("child_pages", [])
    for child in child_pages:
        process_confluence_tree(child, process_function, openai_client=openai_client, parent_path=current_path)


def split_text(page, path, openai_client):
    """Processes a page: splits its content into chunks, embeds them, and uploads to Qdrant."""
    page_text = page.get("content", [])
    project_name = page.get("project_name", "unknown")

    for chunk in page_text:
        chunk_hierarchy = chunk.get("hierarchy", {})
        chunk_text = chunk.get("page_content", "")
        chunks_list = chunk_page(chunk_text, chunk_hierarchy, project_name)

        for chunk in chunks_list:
            embedding = get_embedding_for_text(openai_client, chunk.text, CFG.embed_model)

            metadata = {
                "text": chunk.text,
                "hierarchy": chunk.hierarchy,
                "keywords": chunk.keywords,
                "content_type": chunk.content_type,
                "summary": chunk.summary,
                "project_name": chunk.project_name,
                "source": path,
                "source_page_id": page.get("id", "unknown")
            }

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector={"openai": embedding[0]},
                payload=metadata
            )

            _qdrant_client.upsert(
                collection_name=_qdrant_collection_name,
                points=[point]
            )

    print(f"Page: {path} (ID: {page.get('id', 'unknown')})")


if __name__ == '__main__':
    print("Processing Confluence page tree...")
    load_dotenv(dotenv_path=CFG.env_variable_file)

    _qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "")
    _qdrant_client = connect_to_qdrant()
    _openai_client = OpenAI()

    ensure_collection_exists(_qdrant_client, _qdrant_collection_name, CFG.opeanai_embed_dim)

    process_confluence_tree(data, split_text, openai_client=_openai_client)
