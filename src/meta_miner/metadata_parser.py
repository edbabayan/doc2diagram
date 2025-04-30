import os
import json
from typing import Any

from tqdm import tqdm
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from src.config import CFG
from src.meta_miner.config import MetaConfig, StructuredMetadata
from src.meta_miner.statement import PageState,Output
from src.meta_miner.prompt_caching import CachedLLM


class MetadataExtractor:
    def __init__(self, use_cache=True, cache_dir=CFG.llm_cache_path, cache_ttl=86400):
        base_llm = ChatOpenAI(model=MetaConfig.model).bind_tools([StructuredMetadata])

        if use_cache:
            self.llm = CachedLLM(base_llm, cache_dir=cache_dir, ttl=cache_ttl)
        else:
            self.llm = base_llm

        self.graph = self._build_graph()
        self.use_cache = use_cache

    def _build_graph(self) -> StateGraph:
        builder = StateGraph(input=PageState, output=Output)
        builder.add_node("extract_metadata", self._extract_metadata_node)
        builder.add_edge(START, "extract_metadata")
        builder.add_edge("extract_metadata", END)
        return builder.compile()

    def _extract_metadata_node(self, page_state: PageState) -> Output:
        extracted_objects = []

        for chunk in tqdm(page_state.content, desc=f"Processing {page_state.title} chunks", unit="chunk"):
            content_text = chunk["page_content"]

            # Create the messages list
            messages = [MetaConfig.system_message, HumanMessage(content=content_text)]

            # Use our cached LLM if caching is enabled, otherwise use direct LLM
            if self.use_cache:
                result = self.llm.invoke(messages)
            else:
                result = self.llm.invoke(messages)

            structured_object = StructuredMetadata.model_validate(result.tool_calls[0]["args"])
            chunk["metadata"] = structured_object.key_topics
            chunk["content_type"] = structured_object.content_type

        # Print cache stats if available
        if self.use_cache:
            stats = self.llm.get_stats()
            print(f"Cache stats: {stats['hits']} hits, {stats['misses']} misses ({stats['hit_rate']} hit rate)")

        return Output(
            id=page_state.id,
            title=page_state.title,
            content=page_state.content,
        )

    def extract(self, page: dict[str, Any]) -> Output:
        """Public method to extract metadata from given PageState."""

        page_state = PageState(id=page['id'],
                               title=page['title'],
                               content=page['content'])

        return self.graph.invoke(page_state)

    def clear_cache(self):
        """Clear the cache directory if caching is enabled"""
        if hasattr(self.llm, 'cache_dir') and self.llm.cache_dir.exists():
            for cache_file in self.llm.cache_dir.glob('*.json'):
                cache_file.unlink()
            print(f"Cache cleared from {self.llm.cache_dir}")


if __name__ == '__main__':
    from src.config import CFG

    load_dotenv(dotenv_path=CFG.env_variable_file)

    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model=MetaConfig.model)


    # Read the JSON data
    with open(CFG.tree_file_path, "r") as file:
        data = json.load(file)

    extractor = MetadataExtractor(use_cache=True)

    page = data[0]['child_pages'][0]

    extractor.extract(page)