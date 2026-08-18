import argparse

from .config import get_settings
from .db import make_engine
from .migrate import ensure_schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db"])
    args = parser.parse_args()

    settings = get_settings()
    if args.command == "init-db":
        if not settings.database_url:
            raise SystemExit("DATABASE_URL is not set")
        engine = make_engine(settings.database_url)
        ensure_schema(engine)
        print("schema ready")


if __name__ == "__main__":
    main()
