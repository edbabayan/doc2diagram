import os

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import VectorParams, Distance


def connect_to_qdrant():
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_key = os.getenv("QDRANT_API_KEY", "")

    return QdrantClient(url=qdrant_url, api_key=qdrant_key)

def connect_to_collection(client, collection_name):
    collection_info = client.collec(collection_name)
    if not collection_info:
        raise ValueError(f"Collection '{collection_name}' does not exist.")
    return client, collection_info

def ensure_collection_exists(
    qdrant_client: QdrantClient, qdrant_collection_name: str, embed_dim: int
) -> None:
    """Check if collection exists, if not, create it.

    Args:
        qdrant_client (QdrantClient): The Qdrant client.
        qdrant_collection_name (str): The Qdrant collection name.
        embed_dim (int): The OpenAI embedding dimension.
    """
    try:
        qdrant_client.get_collection(qdrant_collection_name)
        logger.info(f"Collection '{qdrant_collection_name}' already exists.")
    except UnexpectedResponse as error:
        if "Not found" in str(error):
            logger.info(
                f"Collection '{qdrant_collection_name}' not found. Creating it now."
            )
            create_collection(
                qdrant_client, qdrant_collection_name, embed_dim
            )
        else:
            raise


def create_collection(
    qdrant_client: QdrantClient, qdrant_collection_pdf_name: str, embed_dim: int
) -> None:
    """Create a new collection in Qdrant if it doesn't exist.

    Args:
        qdrant_client (QdrantClient): The Qdrant client.
        qdrant_collection_pdf_name (str): The Qdrant collection name.
        embed_dim (int): The OpenAI embedding dimension.
    """
    try:
        qdrant_client.create_collection(
            collection_name=qdrant_collection_pdf_name,
            vectors_config={
                "openai": VectorParams(
                    size=embed_dim,  # openai vector size
                    distance=Distance.COSINE,
                ),
            },
        )
        logger.info(f"Collection '{qdrant_collection_pdf_name}' created successfully.")
    except UnexpectedResponse as err:
        if "already exists" not in str(err):
            raise
        logger.info(f"Collection '{qdrant_collection_pdf_name}' already exists.")


if __name__ == '__main__':
    from dotenv import load_dotenv
    from src.config import CFG

    # Load environment variables from .env file
    load_dotenv(dotenv_path=CFG.env_variable_file)
    _qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "")

    _qdrant_client = connect_to_qdrant()
    ensure_collection_exists(_qdrant_client, _qdrant_collection_name, CFG.opeanai_embed_dim)
    print('')