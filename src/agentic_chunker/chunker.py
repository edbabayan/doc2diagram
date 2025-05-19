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


class Chunk(BaseModel):
    text: str = Field(
        description="The text content of the chunk. This MUST include all original content with ALL references to attachments preserved exactly as they appear in the original text."
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
    attachments: List[dict] = Field(
        description="A list of ALL attachment dictionaries with format {filename: information} that appear in the chunk text. For images, information contains the description, for other files, it's an empty string. Every attachment referenced in the text MUST appear here."
    )


# Define a new model for multiple chunks
class ChunkList(BaseModel):
    chunks: List[Chunk] = Field(
        description="A list of text chunks with their associated metadata. Each chunk MUST preserve ALL attachment references from the original text."
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


def chunk_page(text, hierarchy, attached_files, project_name):
    """
    Splits the text into chunks of a specified size.

    Args:
        text (str): The text to be split.
        hierarchy (dict): The hierarchy of the chunks.
        attached_files (list): A list of attached files.
        project_name (str): The name of the project.
    Returns:
        list: A list of Chunk objects.
    """
    logger.info(f"Chunking page with hierarchy: {hierarchy}")
    logger.debug(f"Text length: {len(text)} characters, Project: {project_name}")

    # Convert attached_files to a consistent format the LLM can work with
    file_names = [attachment.get("file_name", "") for attachment in attached_files if "file_name" in attachment]

    system_message = SystemMessage(content=AgentPrompts.chunker_prompt)

    # Format the user message more clearly, emphasizing the importance of attachments
    user_message = HumanMessage(
        content=f"""
            Please split the following text into appropriate chunks:

            TEXT TO CHUNK:
            {text}

            ADDITIONAL CONTEXT:
            - Hierarchy: {hierarchy}
            - Project Name: {project_name}
            - Attached Files: {file_names}

            Return multiple chunks, with each chunk representing a logical section of the text.
            IMPORTANT: Each chunk MUST include ALL attachments referenced in that section of text.
            Every attachment file name in the list should be included in the appropriate chunk's attachments.
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
            # Extract the raw attachments from the chunk
            # First try to get them from the attachments field
            raw_attachments = raw_chunk.get("attachments", [])

            # If raw_attachments is empty or None, try to parse them from the text
            if not raw_attachments:
                # Find all image references in the format ![🖼️ filename.png]
                import re
                image_pattern = r"!\[🖼️\s+(.*?)\]"
                found_images = re.findall(image_pattern, raw_chunk.get("text", ""))

                # Find all file references in the format [📎 filename.ext]
                file_pattern = r"\[📎\s+(.*?)\]"
                found_files = re.findall(file_pattern, raw_chunk.get("text", ""))

                # Combine all found attachments
                raw_attachments = found_images + found_files

            # Process attachments into the new format
            processed_attachments = []

            # Filter images vs other files if raw_attachments is a list of strings
            if raw_attachments and all(isinstance(item, str) for item in raw_attachments):
                image_files = [attachment for attachment in raw_attachments if
                               attachment.endswith(('.png', '.jpg', '.jpeg'))]
                other_files = [attachment for attachment in raw_attachments if
                               not attachment.endswith(('.png', '.jpg', '.jpeg'))]

                # Generate descriptions for images
                image_descriptions = describe_image(openai, raw_chunk.get("text", ""), image_files)

                # Add image attachments with descriptions
                for image_file in image_files:
                    description = image_descriptions.get(image_file, "")
                    processed_attachments.append({image_file: description})

                # Add other file attachments with empty descriptions
                for other_file in other_files:
                    processed_attachments.append({other_file: ""})
            # Handle if raw_attachments is already a list of dictionaries
            elif raw_attachments:
                # Handle different possible formats of attachments
                for attachment in raw_attachments:
                    if isinstance(attachment, dict):
                        # If it's a dict with file_name key
                        if "file_name" in attachment:
                            file_name = attachment["file_name"]
                            if file_name.endswith(('.png', '.jpg', '.jpeg')):
                                description = describe_image(openai, raw_chunk.get("text", ""), [file_name]).get(
                                    file_name, "")
                            else:
                                description = ""
                            processed_attachments.append({file_name: description})
                        # If it's already in the format {file_name: description}
                        else:
                            processed_attachments.append(attachment)
                    elif isinstance(attachment, str):
                        # If it's just a string filename
                        if attachment.endswith(('.png', '.jpg', '.jpeg')):
                            description = describe_image(openai, raw_chunk.get("text", ""), [attachment]).get(
                                attachment, "")
                        else:
                            description = ""
                        processed_attachments.append({attachment: description})

            # Extract the hierarchy values and convert to a list
            hierarchy_values = list(hierarchy.values())

            # Create a string from the hierarchy values, each on a new line
            hierarchy_prefix = '\n'.join(hierarchy_values) + '\n\n'

            # Add the hierarchy values to the beginning of the text
            modified_text = hierarchy_prefix + raw_chunk['text']


            # Create a complete chunk with manually provided hierarchy and project_name
            chunk = Chunk(
                text=modified_text,
                hierarchy=hierarchy,  # Manually set hierarchy
                keywords=raw_chunk.get("keywords", []),
                content_type=raw_chunk.get("content_type", "unknown"),
                summary=raw_chunk.get("summary", ""),
                project_name=project_name,  # Manually set project_name
                attachments=processed_attachments
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
    Generates descriptions for images using the language model.

    Args:
        llm: The language model to use for generating the description.
        associated_text (str): The text associated with the image.
        attached_images (list): List of image file names.

    Returns:
        dict: A dictionary mapping image names to their descriptions.
    """
    images_description = {}
    for image_name in attached_images:
        # Check if the image file exists
        if not (CFG.attachments_dir / image_name).exists():
            logger.warning(f"Image file {image_name} does not exist.")
            images_description[image_name] = ""  # Empty description for non-existent images
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
        "id": "1049861440",
        "title": "JS agents & client release pipeline",
        "content": [
          {
            "type": "content",
            "hierarchy": {},
            "page_content": "trueJs-agents release pipelinefalseautotoptrue9416\n\ntrueJs-agents release pipelinefalseautotoptrue9416\n\ntrue\n\nJs-agents release pipeline\n\nfalse\n\nauto\n\ntop\n\ntrue\n\n941\n\n6\n\nRelease steps:\n\nCreate a Pull Request from develop to master branch, name it as \"Release {Release version}\"Run the agent examples fromexamples repowith release candidate, ensure that everything is fine and attach the launch link in ReportPortal to the Pull Request description.Also provide some notes or screenshots if necessary.Fill in or update theCHANGELOG.md.Guide for changelog entries -https://keepachangelog.com/en/1.1.0/.Do not forget to mention contributors here in case the Pull Request contains changes from them.UpdateREADME.mdif applicable.Updateversion_fragmentfile with necessary version fragment to bump next release version correctly (the default fragment ispatch).Note: do not change version inVERSIONfile orpackage.jsonmanually.Receive at least 1 approve from team members (preferably from Team Lead).Merge Pull Request to master viamerge commit.Note: do not use rebase&merge/squash&merge options to avoid commits duplication during master→develop synchronization and to keep the history clean.All further steps according to the diagram will be performed automatically.Note: recheck that all pipelines finished successfully (GitHub tag & release created, develop updated with changes from master, packages published to NPM and GitHub packages registries).\n\n[examples repo](https://github.com/reportportal/examples-js)\n\n[https://keepachangelog.com/en/1.1.0/](https://keepachangelog.com/en/1.1.0/)\n\nCreate a Pull Request from develop to master branch, name it as \"Release {Release version}\"\n\nRun the agent examples fromexamples repowith release candidate, ensure that everything is fine and attach the launch link in ReportPortal to the Pull Request description.Also provide some notes or screenshots if necessary.\n\n[examples repo](https://github.com/reportportal/examples-js)\n\nexamples repo\n\nFill in or update theCHANGELOG.md.Guide for changelog entries -https://keepachangelog.com/en/1.1.0/.\n\n[https://keepachangelog.com/en/1.1.0/](https://keepachangelog.com/en/1.1.0/)\n\nCHANGELOG.md\n\nhttps://keepachangelog.com/en/1.1.0/\n\nDo not forget to mention contributors here in case the Pull Request contains changes from them.\n\nUpdateREADME.mdif applicable.\n\nREADME.md\n\nUpdateversion_fragmentfile with necessary version fragment to bump next release version correctly (the default fragment ispatch).Note: do not change version inVERSIONfile orpackage.jsonmanually.\n\nversion_fragment\n\npatch\n\nVERSION\n\npackage.json\n\nReceive at least 1 approve from team members (preferably from Team Lead).\n\nMerge Pull Request to master viamerge commit.Note: do not use rebase&merge/squash&merge options to avoid commits duplication during master→develop synchronization and to keep the history clean.\n\nmerge commit.\n\nAll further steps according to the diagram will be performed automatically.Note: recheck that all pipelines finished successfully (GitHub tag & release created, develop updated with changes from master, packages published to NPM and GitHub packages registries).\n\nSemver versions guide:\n\nhttps://semver.org/\n\n[https://semver.org/](https://semver.org/)\n\nhttps://semver.org/",
            "attachments": []
          }
        ],
        "attachments": [],
        "last_modified": "2025-01-31T11:08:21.502Z",
        "last_modified_by": "Ilya Hancharyk",
        "child_pages": [],
        "project_name": "EPMRPP"
      }

    # Example usage
    hierarchy_test = test_chunk['hierarchy']
    text_test = test_chunk['page_content']
    attached_test = test_chunk['attachments']
    project_name_test = "ReportPortal"

    logger.info("Starting test chunking")

    # This will now return a list of Chunk objects
    chunked_text = chunk_page(text_test, hierarchy_test, attached_test, project_name_test)