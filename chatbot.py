import os
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from src.config import CFG

# Load environment variables from .env file
load_dotenv(dotenv_path=CFG.env_variable_file)


def connect_to_qdrant(collection_name="confluence"):
    """Connect to existing Qdrant collection"""
    # Connect to Qdrant Cloud
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL"),
        api_key=os.environ.get("QDRANT_API_KEY")
    )
    return client, collection_name


def get_embedding(text, client):
    """Get embedding for a text using OpenAI API"""
    response = client.embeddings.create(
        model=CFG.embed_model,
        input=text
    )
    return response.data[0].embedding


def query_retrieval_system(qdrant_client, collection_name, query, openai_client, k=3):
    """Query the retrieval system and return relevant documents"""
    # Generate embedding for the query
    query_embedding = get_embedding(query, openai_client)

    # Perform similarity search in Qdrant
    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=("openai", query_embedding),  # Specify the vector name as "openai"
        limit=k
    )

    retrieved_documents = ""

    for result in search_results:
        text = result.payload.get("text", "No content found")
        attachments = result.payload.get("attachments", "No content found")

        final_text = add_attachment_description(text, attachments)
        retrieved_documents += final_text + "\n\n"

    return retrieved_documents


def add_attachment_description(text, attachments):
    """
    Adds the description of each attachment after the file name in the text.
    Args:
        text: The text
        attachments: A list of dictionaries where each dictionary has a filename as key and description as value
    Returns:
        The modified text with attachment descriptions
    """
    # For each attachment, find the filename in the text and add its description
    for attachment_dict in attachments:
        for filename, description in attachment_dict.items():
            # Look for the filename pattern in the text (with or without emoji)
            # Common patterns might be: ![🖼️ filename] or ![filename]
            file_patterns = [
                f"![🖼️ {filename}]",
                f"![{filename}]"
            ]
            # Replace each occurrence with the filename followed by its description
            for pattern in file_patterns:
                if pattern in text:
                    replacement = f"{pattern}\n\n**Image Description:** {description}"
                    text = text.replace(pattern, replacement)
    return text


def generate_answer(query, context_string, openai_client, model="gpt-4o"):
    """Generate an answer using OpenAI API with retrieved context as a string"""
    # Create prompt with context
    prompt = f"""Answer the following question based on the provided context information. 
If you don't know the answer or the context doesn't contain relevant information, say so.

Context:
{context_string}

Question: {query}

Answer:"""

    # Call OpenAI API
    response = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "You are a helpful assistant that answers questions based on the provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    answer = response.choices[0].message.content
    return answer


def generate_streaming_answer(query, context_string, openai_client, model="gpt-4o"):
    """Generate a streaming answer using OpenAI API with retrieved context as a string"""
    # Create prompt with context
    prompt = f"""Answer the following question based on the provided context information. 
If you don't know the answer or the context doesn't contain relevant information, say so.

Context:
{context_string}

Question: {query}

Answer:"""

    # Call OpenAI API with streaming enabled
    stream = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "You are a helpful assistant that answers questions based on the provided context."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        stream=True
    )

    return stream


if __name__ == "__main__":
    # Connect to Qdrant
    _qdrant_client, _collection_name = connect_to_qdrant("confluence")  # Replace with your collection name
    print(f"Successfully connected to Qdrant collection: {_collection_name}")

    # Initialize OpenAI client
    _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Test with a sample query
    _query = "tell me test framework weekly downloads for Playwright"
    # _query = "please tell me about Proxy issues (WF/JPMC) start time"

    retrieved_docs = query_retrieval_system(_qdrant_client, _collection_name, _query, _openai_client, k=3)

    # Generate answer
    query_result = generate_answer(_query, retrieved_docs, _openai_client)
