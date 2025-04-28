from typing import Any
from dataclasses import dataclass


@dataclass
class PageState:
    content: list[dict[str, Any]]


@dataclass
class Output:
    title: str