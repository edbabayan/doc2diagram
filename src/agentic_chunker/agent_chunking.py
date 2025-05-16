import os
import uuid
import json

from tqdm import tqdm
from loguru import logger
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client.models import PointStruct

from src.config import CFG
from src.vector_database.utils import get_embedding_for_text
from src.vector_database.database_connection import ensure_collection_exists, connect_to_qdrant
from src.agentic_chunker.chunker import chunk_page
from src.agentic_chunker.utils import download_local_llm


# Load and parse the tree file
logger.info(f"Loading tree file from {CFG.tree_file_path}")
with open(CFG.tree_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Download local LLM if needed
logger.info(f"Checking if local LLM {CFG.local_llm_model} needs to be downloaded")
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
        logger.info(f"Processing a list of {len(tree)} pages")
        for item in tqdm(tree, desc="Processing top-level pages"):
            process_confluence_tree(item, process_function, openai_client=openai_client, parent_path=parent_path)
        return

    # Extract page information
    page_id = tree.get("id", "unknown")
    page_title = tree.get("title", "Untitled")

    # Build the current path
    current_path = f"{parent_path}/{page_title}" if parent_path else page_title

    # Process the current page
    logger.info(f"Processing page: {current_path} (ID: {page_id})")
    process_function(tree, current_path, openai_client=openai_client)

    # Process content sections if they exist
    content_sections = tree.get("content", [])
    if content_sections:
        logger.debug(f"Processing {len(content_sections)} content sections for page {page_title}")
        for section in tqdm(content_sections, desc=f"Processing sections of {page_title}", leave=False):
            process_function(section, f"{current_path}/content", openai_client=openai_client)

    # Recursively process child pages
    child_pages = tree.get("child_pages", [])
    if child_pages:
        logger.info(f"Processing {len(child_pages)} child pages for {page_title}")
        for child in tqdm(child_pages, desc=f"Processing child pages of {page_title}", leave=False):
            process_confluence_tree(child, process_function, openai_client=openai_client, parent_path=current_path)


def split_text(page, path, openai_client):
    """Processes a page: splits its content into chunks, embeds them, and uploads to Qdrant."""
    page_text = page.get("content", [])
    project_name = page.get("project_name", "unknown")
    page_id = page.get("id", "unknown")

    chunks_count = 0
    logger.debug(f"Splitting text for page: {path} (ID: {page_id})")

    for chunk in page_text:
        chunk_hierarchy = chunk.get("hierarchy", {})
        chunk_text = chunk.get("page_content", "")
        chunk_attachments = chunk.get("attachments", [])

        if chunk_hierarchy != {"Subsection": "Logo"}:
            continue

        logger.debug(f"Chunking text of length {len(chunk_text)} with hierarchy {chunk_hierarchy}")
        chunks_list = chunk_page(chunk_text, chunk_hierarchy, chunk_attachments, project_name)

        for idx, chunk in enumerate(tqdm(chunks_list, desc="Exporting chunks", leave=True)):
            try:
                embedding = get_embedding_for_text(openai_client, chunk.text, CFG.embed_model)

                metadata = {
                    "text": chunk.text,
                    "hierarchy": chunk.hierarchy,
                    "keywords": chunk.keywords,
                    "content_type": chunk.content_type,
                    "summary": chunk.summary,
                    "project_name": chunk.project_name,
                    "source": path,
                    "source_page_id": page_id,
                    "attachments": chunk.attachments,
                    "last_modified": page['last_modified'],
                    "last_modified_by": page['last_modified_by'],
                }

                point_id = str(uuid.uuid4())
                point = PointStruct(
                    id=point_id,
                    vector={"openai": embedding[0]},
                    payload=metadata
                )

                _qdrant_client.upsert(
                    collection_name=_qdrant_collection_name,
                    points=[point]
                )

                chunks_count += 1

            except Exception as e:
                logger.error(f"Error processing chunk {idx + 1}: {str(e)}")

    logger.info(f"Completed processing page: {path} (ID: {page_id}) - {chunks_count} chunks processed")


if __name__ == '__main__':
    logger.info("Starting Confluence page tree processing")
    load_dotenv(dotenv_path=CFG.env_variable_file)
    logger.info("Environment variables loaded")

    _qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "")
    if not _qdrant_collection_name:
        logger.warning("QDRANT_COLLECTION_NAME not set, using default empty string")

    logger.info("Connecting to Qdrant")
    _qdrant_client = connect_to_qdrant()

    logger.info("Initializing OpenAI client")
    _openai_client = OpenAI()

    logger.info(f"Ensuring collection '{_qdrant_collection_name}' exists")
    ensure_collection_exists(_qdrant_client, _qdrant_collection_name, CFG.opeanai_embed_dim)

    try:
        process_confluence_tree(data, split_text, openai_client=_openai_client)
        logger.success("Successfully completed processing Confluence page tree")
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        logger.exception("Detailed exception information:")
        raise
