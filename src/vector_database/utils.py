from typing import List

from openai import OpenAI


def get_embedding_for_text(
        openai_client: OpenAI,
        text: str,
        embedding_model: str,
        chunk_size: int = 5000
) -> List[List[float]]:
    """
    Get embeddings for a text, chunking if necessary.
    """
    embeddings = []

    if len(text) > chunk_size:
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        for chunk in chunks:
            response = openai_client.embeddings.create(
                input=chunk,
                model=embedding_model
            )
            print(f"Processing chunk of length: {len(chunk)}")
            embeddings.append(response.data[0].embedding)
    else:
        response = openai_client.embeddings.create(
            input=text,
            model=embedding_model
        )
        embeddings.append(response.data[0].embedding)

    return embeddings