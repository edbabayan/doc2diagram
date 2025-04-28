import os
import json
from typing import Any
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.config import CFG
from langgraph.graph import StateGraph, START, END


load_dotenv(dotenv_path=CFG.env_variable_file)

api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini")


# Read the JSON data
with open(CFG.tree_file_path, "r") as file:
    data = json.load(file)

page_content = data[0]['child_pages'][-2]


@dataclass
class PageState:
    title: str
    content: list[dict[str, Any]]


@dataclass
class Output:
    title: str


def extract_title(page_content: PageState) -> Output:
    title = page_content.title
    # You can process content if necessary
    return Output(title=title)


builder = StateGraph(input=PageState, output=Output)  # Specify both input and output types
builder.add_node(extract_title, "extract_title")

builder.add_edge(START, "extract_title")
builder.add_edge("extract_title", END)

graph = builder.compile()

# Pass the entire PageState object as input
print(graph.invoke(PageState(title=page_content['title'], content=page_content['content'])))