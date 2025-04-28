from typing import List
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage


class MetaConfig:
    model = "gpt-4o-mini"

    system_message =  SystemMessage(
        content="""
        You are a metadata extraction expert. Given page content from a technical documentation site, 
        extract key metadata in a structured format. Be precise and thorough.
        
        Return your analysis in JSON format with the following fields:
        - key_topics: A list key topics or concepts mentioned
        - content_type: Classification as one of: guideline, documentation, example, resource, promotional
        """
    )


class StructuredMetadata(BaseModel):
    """Always use this tool to structure extracted metadata from technical documentation page content."""
    key_topics: List[str] = Field(description="A list of up to 5 key topics or concepts mentioned in the content")
    content_type: str = Field(description="Classification of the content: guideline, documentation, example, resource, or promotional")
