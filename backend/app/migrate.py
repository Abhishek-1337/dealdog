from sqlalchemy import text

from .db import Base
from .models import PricePoint, Product, TrackedProduct  # noqa: F401


def ensure_schema(engine) -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
