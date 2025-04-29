import os
import json
from typing import Any

from tqdm import tqdm
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from src.meta_miner.config import MetaConfig, StructuredMetadata
from src.meta_miner.statement import PageState,Output


class MetadataExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(model=MetaConfig.model).bind_tools([StructuredMetadata])
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(input=PageState, output=Output)
        builder.add_node("extract_metadata", self._extract_metadata_node)
        builder.add_edge(START, "extract_metadata")
        builder.add_edge("extract_metadata", END)
        return builder.compile()

    def _extract_metadata_node(self, page_state: PageState) -> Output:
        extracted_objects = []

        for chunk in page_state.content:
            content_text = chunk["page_content"]
            result = self.llm.invoke(
                [MetaConfig.system_message, HumanMessage(content_text)]
            )
            structured_object = StructuredMetadata.model_validate(result.tool_calls[0]["args"])
            chunk["metadata"] = structured_object.key_topics
            chunk["content_type"] = structured_object.content_type

        return Output(
            id=page_state.id,
            title=page_state.title,
            content=page_state.content,
        )

    def extract(self, page: list[dict[str, Any]]) -> Output:
        """Public method to extract metadata from given PageState."""

        page_state = PageState(id=page['id'],
                               title=page['title'],
                               content=page['content'])

        return self.graph.invoke(page_state)


if __name__ == '__main__':
    from src.config import CFG

    load_dotenv(dotenv_path=CFG.env_variable_file)

    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model=MetaConfig.model)


    # Read the JSON data
    with open(CFG.tree_file_path, "r") as file:
        data = json.load(file)

    extractor = MetadataExtractor()

    page = data[0]['child_pages'][0]

    extractor.extract(page)