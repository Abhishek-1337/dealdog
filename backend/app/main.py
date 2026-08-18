import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import make_engine, make_session_factory
from .deps import AppContext
from .embeddings import Embedder
from .llm import LLMClient
from .migrate import ensure_schema
from .repository import InMemoryProductRepo, SqlProductRepo
from .routers import router

logger = logging.getLogger("dealdog")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_url and settings.database_url.startswith("postgresql"):
        engine = make_engine(settings.database_url)
        ensure_schema(engine)
        repo = SqlProductRepo(make_session_factory(engine))
    else:
        logger.warning("DATABASE_URL not set or not postgres; using in-memory store")
        repo = InMemoryProductRepo()

    app.state.context = AppContext(
        repo=repo,
        llm=LLMClient(settings),
        embedder=Embedder(settings),
        settings=settings,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="DealDog", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
