from pydantic import BaseModel, Field
from typing import List
from loguru import logger

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from src.config import CFG
from src.agentic_chunker.prompts import AgentPrompts


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
    user_message = HumanMessage(
        content=f"Split the following text into appropriate chunks: {text} with hierarchy: {hierarchy} and {project_name}"
                f"name of the project. "
                f"Return multiple chunks, with each chunk representing a logical section of the text."
    )

    # Bind the ChunkList tool instead of the single Chunk
    logger.debug("Binding ChunkList tool to language model")
    structured_qwen3 = qwen3.bind_tools([ChunkList])

    try:
        logger.info("Invoking language model to chunk text")
        response = structured_qwen3.invoke([system_message, user_message])

        # Get the raw chunks from the response
        raw_chunks = response.tool_calls[0]["args"].get("chunks", [])

        # Create properly formatted chunks with the manual hierarchy and project_name
        formatted_chunks = []
        for raw_chunk in raw_chunks:
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


if __name__ == '__main__':
    logger.info("Running chunker test")

    test_chunk = {'hierarchy': {'Subsection': 'About ReportPortal', 'Topic': 'Our brand story'},
                  'page_content': "At ReportPortal, we are committed to delivering cutting-edge solutions that empower teams and organizations to achieve excellence in test automation and reporting. Our platform stands at the intersection of innovation and efficiency, providingreal-time analytics and insights into automated test results.\nOur mission\nОur mission is clear and resolute: to empower quality assurance excellence in the ever-evolving landscape of software development. We are dedicated to equipping QA professionals, testers, and development teams with the tools, knowledge,and resources they need to deliver exceptional software products.\nOur core values\n• Innovation:We're dedicated to pioneering new approaches and technologies that enhance testing efficiencyand effectiveness.\n• Collaboration:We foster a spirit of collaboration, recognizing that achieving QA excellence requires collective effort.\n• Empowerment:We empower testers and QA professionals by offering intuitive, user-friendly tools and resources.\n• Transparency:We provide clear documentation, guidelines, and support to ensure that you have a full understandingof how to maximize the potential of our platform.\n• Community:Our mission extends beyond our platform, as we actively engage with this community to share knowledgeand best practices.",
                  'metadata': ['test automation',
                               'reporting',
                               'real-time analytics',
                               'quality assurance',
                               'community engagement'],
                  'content_type': 'promotional'}

    # Example usage
    hierarchy_test = test_chunk['hierarchy']
    text_test = test_chunk['page_content']
    project_name_test = "ReportPortal"

    logger.info("Starting test chunking")

    # This will now return a list of Chunk objects
    chunked_text = chunk_page(text_test, hierarchy_test, project_name_test)
