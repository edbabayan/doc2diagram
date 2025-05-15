from typing import List
from loguru import logger
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain_openai.chat_models import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import CFG
from src.agentic_chunker.utils import encode_image
from src.agentic_chunker.prompts import AgentPrompts

# Load environment variables
load_dotenv(dotenv_path=CFG.env_variable_file)

openai = ChatOpenAI(model="gpt-4o", temperature=0)

# Define the Chunk model
class Chunk(BaseModel):
    text: str = Field(
        description="The text content of the chunk."
    )
    hierarchy: dict = Field(
        description="The hierarchical structure of the chunk, including sections and subsections."
    )
    keywords: list = Field(
        description="A list of keywords associated with the chunk, providing context and metadata."
    )
    content_type: str = Field(
        description="The type of content being processed, such as 'promotional', 'technical', etc."
    )
    summary: str = Field(
        description="A summary of the chunk, highlighting its main points and themes."
    )
    project_name: str = Field(
        description="The name of the project."
    )
    attachments: list = Field(
        description="A list of attachments associated with the chunk, such as images or documents."
    )


# Define a new model for multiple chunks
class ChunkList(BaseModel):
    chunks: List[Chunk] = Field(
        description="A list of text chunks with their associated metadata."
    )


# Initialize the language model with streaming enabled
logger.info(f"Initializing language model: {CFG.local_llm_model}")
try:
    qwen3 = ChatOllama(
        model=CFG.local_llm_model,
        temperature=0.0,
    )
    logger.success(f"Successfully initialized {CFG.local_llm_model}")
except Exception as e:
    logger.error(f"Failed to initialize language model: {str(e)}")
    logger.exception("Detailed exception information:")
    raise


def chunk_page(text, hierarchy, project_name):
    """
    Splits the text into chunks of a specified size.

    Args:
        text (str): The text to be split.
        hierarchy (dict): The hierarchy of the chunks.
        project_name (str): The name of the project.
    Returns:
        list: A list of Chunk objects.
    """
    logger.info(f"Chunking page with hierarchy: {hierarchy}")
    logger.debug(f"Text length: {len(text)} characters, Project: {project_name}")

    system_message = SystemMessage(content=AgentPrompts.chunker_prompt)

    # Format the user message more clearly, separating the text and instructions
    user_message = HumanMessage(
        content=f"""
            Please split the following text into appropriate chunks:
            
            TEXT TO CHUNK:
            {text}
            
            ADDITIONAL CONTEXT:
            - Hierarchy: {hierarchy}
            - Project Name: {project_name}
            
            Return multiple chunks, with each chunk representing a logical section of the text.
            """
    )

    # Bind the ChunkList tool instead of the single Chunk
    logger.debug("Binding ChunkList tool to language model")
    structured_qwen3 = qwen3.bind_tools([ChunkList])

    structured_openai = openai.bind_tools([ChunkList])

    try:
        logger.info("Invoking language model to chunk text")
        response = structured_openai.invoke([system_message, user_message])

        # Get the raw chunks from the response
        raw_chunks = response.tool_calls[0]["args"].get("chunks", [])

        # Create properly formatted chunks with the manual hierarchy and project_name
        formatted_chunks = []
        for raw_chunk in raw_chunks:
            # Extract images from attachments
            attached_images = [attachment for attachment in raw_chunk.get("attachments", []) if attachment.endswith(('.png', '.jpg', '.jpeg'))]

            # Generate image descriptions using the language model
            # image_description = describe_image(openai, raw_chunk.get("text", ""), attached_images)

            # Create a complete chunk with manually provided hierarchy and project_name
            chunk = Chunk(
                text=raw_chunk.get("text", ""),
                hierarchy=hierarchy,  # Manually set hierarchy
                keywords=raw_chunk.get("keywords", []),
                content_type=raw_chunk.get("content_type", "unknown"),
                summary=raw_chunk.get("summary", ""),
                project_name=project_name,  # Manually set project_name
                attachments=raw_chunk.get("attachments", [])
            )
            formatted_chunks.append(chunk)

        # Return just the list of chunks
        return formatted_chunks

    except Exception as e:
        logger.error(f"Error during chunking: {str(e)}")
        logger.exception("Detailed exception information:")
        # Return an empty list if chunking fails
        return []


def describe_image(llm, associated_text, attached_images):
    """
    Generates a description for an image using the language model.

    Args:
        llm: The language model to use for generating the description.
        associated_text (str): The text associated with the image.
        image_name (str): The name of the image file.

    Returns:
        str: A description of the image.
    """
    images_description = {}
    for image_name in attached_images:
        # Check if the image file exists
        if not (CFG.attachments_dir / image_name).exists():
            logger.warning(f"Image file {image_name} does not exist.")
            continue
        else:
            image_path = CFG.attachments_dir / image_name
            logger.info(f"Image file {image_name} exists at {image_path}")
            # If the image file exists, generate a description
            description = generate_image_description(llm, image_path, associated_text)
            images_description[image_name] = description

    return images_description


def generate_image_description(llm, image_path, associated_text):
    """
    Generates a description for an image using the language model.

    Args:
        llm: The language model to use for generating the description.
        image_path (str): The path of the image file.
        associated_text (str): The text associated with the image.

    Returns:
        str: A description of the image.
    """
    base64_image = encode_image(image_path)
    system_message = SystemMessage(
        content="You are an expert image analyzer. You should describe the image, for example if the image contains text"
                "return the text of the image or if the image contains a chart, return the data of the chart or if the "
                "image contains a logo, return the name of the logo and say that it is a logo."
    )

    user_message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": f"Describe this image. Consider its relation to this associated text: '{associated_text}'."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            }
        ]
    )

    # Invoke the language model
    logger.debug("Invoking language model for image description")
    response = llm.invoke([system_message, user_message])

    return response.content


if __name__ == '__main__':
    logger.info("Running chunker test")

    test_chunk = {
            "hierarchy": {
              "Subsection": "Logo"
            },
            "page_content": "![🖼️ image-2023-10-17_10-27-2.png](image-2023-10-17_10-27-2.png)\n\n[📎 RP_Logo_Pack.zip](RP_Logo_Pack.zip)\n\nThe logo helps to reflect one of the key ideas  of the product - focusing on detecting bugs in software. The focus - the main symbol of the product - helps emphasise this task and adds significance. The color scheme of the logo consists of topaz and black, giving it a stylish and professional appearance.\n\n![🖼️ image-2023-10-6_17-2-57.png](image-2023-10-6_17-2-57.png)\n\n![🖼️ image-2023-10-6_17-7-30.png](image-2023-10-6_17-7-30.png)\n\nClear space\n\nWhen using the logo, it is important to adhere to standard clear space and safe zone guidelines to ensure proper emphasis and differentiation from other branding elements. This also ensures consistency in logo usage and effective perception across different contexts.\n\n![🖼️ image-2023-10-6_17-10-29.png](image-2023-10-6_17-10-29.png)\n\nTo prevent distortion of the logo and ensure its clear understanding, there are recommended minimum sizes for the logo. Depending on the application method and material, the minimum size of the logo may vary. However, the main factor remains the clear readability of the logo.\n\n![🖼️ image-2023-10-6_17-12-19.png](image-2023-10-6_17-12-19.png)\n\nIncorrect usage\n\nOur logo is an important component of brand recognition, so it is important to follow the rules below in order not to violate the integrity and recognition of the ReportPortal logo.\n\n![🖼️ image-2023-10-6_17-14-52.png](image-2023-10-6_17-14-52.png)\n\nSymbol\n\nTo maintain clarity and readability of the symbol, it is important to adhere to a clear space around it. The minimum clear space should be equal to half of the size of the symbol.\n\n![🖼️ image-2023-10-6_17-31-35.png](image-2023-10-6_17-31-35.png)\n\nIt is also recommended to use the symbol only with the branded colors, as shown in the example below.\n\n![🖼️ image-2023-10-6_17-32-42.png](image-2023-10-6_17-32-42.png)",
            "attachments": [
              {
                "file_name": "image-2023-10-17_10-27-2.png",
                "url": "image-2023-10-17_10-27-2.png"
              },
              {
                "file_name": "RP_Logo_Pack.zip",
                "url": "RP_Logo_Pack.zip"
              },
              {
                "file_name": "image-2023-10-6_17-2-57.png",
                "url": "image-2023-10-6_17-2-57.png"
              },
              {
                "file_name": "image-2023-10-6_17-7-30.png",
                "url": "image-2023-10-6_17-7-30.png"
              },
              {
                "file_name": "image-2023-10-6_17-10-29.png",
                "url": "image-2023-10-6_17-10-29.png"
              },
              {
                "file_name": "image-2023-10-6_17-12-19.png",
                "url": "image-2023-10-6_17-12-19.png"
              },
              {
                "file_name": "image-2023-10-6_17-14-52.png",
                "url": "image-2023-10-6_17-14-52.png"
              },
              {
                "file_name": "image-2023-10-6_17-31-35.png",
                "url": "image-2023-10-6_17-31-35.png"
              },
              {
                "file_name": "image-2023-10-6_17-32-42.png",
                "url": "image-2023-10-6_17-32-42.png"
              }
            ]
          }

    # Example usage
    hierarchy_test = test_chunk['hierarchy']
    text_test = test_chunk['page_content']
    project_name_test = "ReportPortal"

    logger.info("Starting test chunking")

    # This will now return a list of Chunk objects
    chunked_text = chunk_page(text_test, hierarchy_test, project_name_test)
