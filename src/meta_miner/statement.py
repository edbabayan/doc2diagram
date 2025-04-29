from typing import Any
from dataclasses import dataclass


@dataclass
class PageState:
    id: str
    title: str
    content: list[dict[str, Any]]


@dataclass
class Output:
    id: str
    title: str
    content: list[dict[str, Any]]
