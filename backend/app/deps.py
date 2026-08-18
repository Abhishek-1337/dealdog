from dataclasses import dataclass

from fastapi import Request

from .config import Settings
from .embeddings import Embedder
from .llm import LLMClient
from .repository import ProductRepo


@dataclass
class AppContext:
    repo: ProductRepo
    llm: LLMClient
    embedder: Embedder
    settings: Settings


def get_context(request: Request) -> AppContext:
    return request.app.state.context
