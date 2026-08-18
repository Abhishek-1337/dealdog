import pytest

from app.config import Settings
from app.deps import AppContext
from app.embeddings import Embedder
from app.llm import LLMClient
from app.repository import InMemoryProductRepo


@pytest.fixture
def settings():
    return Settings(openai_api_key="", database_url="")


@pytest.fixture
def embedder(settings):
    return Embedder(settings)


@pytest.fixture
def llm(settings):
    return LLMClient(settings)


@pytest.fixture
def repo():
    return InMemoryProductRepo()


@pytest.fixture
def ctx(repo, llm, embedder, settings):
    return AppContext(repo=repo, llm=llm, embedder=embedder, settings=settings)
