from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    match_threshold: float = 0.90
    pending_low: float = 0.80
    top_k: int = 5

    # Browser origins allowed to call the API, comma-separated — the Vercel
    # production domain plus any preview domains. A plain "*" allows every
    # origin, which is the local-development default.
    cors_origins: str = "*"

    # Price-drop detection. A site's latest price is compared to the rolling
    # average of its own previous `drop_window` prices; a drop is only flagged
    # when it clears BOTH thresholds, so a $0.50 dip on a cheap item and a 0.2%
    # dip on an expensive one are both ignored.
    drop_percent_threshold: float = 10.0
    drop_absolute_threshold: float = 5.0
    drop_window: int = 3
    drop_min_history: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        """`cors_origins` split into the list CORSMiddleware expects.

        Blank entries and stray whitespace are dropped so a trailing comma in
        the env file cannot turn into an origin that matches nothing. An empty
        value falls back to "*" rather than to a list that blocks every browser.
        """
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        return [origin for origin in origins if origin] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
