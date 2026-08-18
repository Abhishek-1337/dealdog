from sqlalchemy import text

from .db import Base
from .models import PricePoint, Product, TrackedProduct  # noqa: F401

# create_all() only creates missing tables, so columns added to an existing
# price_points table are patched in explicitly. Both statements are no-ops on a
# fresh database.
_PRICE_POINT_PATCHES = (
    "ALTER TABLE IF EXISTS price_points ADD COLUMN IF NOT EXISTS scrape_success BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE IF EXISTS price_points ALTER COLUMN price DROP NOT NULL",
)


def ensure_schema(engine) -> None:
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for statement in _PRICE_POINT_PATCHES:
                conn.execute(text(statement))
