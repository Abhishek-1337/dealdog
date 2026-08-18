import json

from .attributes import extract_attributes_fallback
from .config import Settings

EXTRACT_PROMPT = (
    "Extract structured product attributes from each raw retailer title. "
    "Return ONLY a JSON array with one object per title, in the same order. "
    "Each object must have keys: brand, model, chip, ram, storage. "
    "Use null for anything missing. Normalize ram/storage to e.g. \"8GB\"/\"256GB\", "
    "and chip to e.g. \"M3\"/\"M3 Pro\"/\"Snapdragon\". "
    "Example: \"Apple 2024 MacBook Air 13-inch M3 8GB Memory 256GB SSD\" -> "
    '{"brand":"Apple","model":"MacBook Air","chip":"M3","ram":"8GB","storage":"256GB"}.'
)


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        if settings.openai_api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=settings.openai_api_key)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def extract_attributes_batch(self, titles: list[str]) -> list[dict]:
        if not self.client:
            return [extract_attributes_fallback(t) for t in titles]
        numbered = "\n".join(f"{i}: {t}" for i, t in enumerate(titles))
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": EXTRACT_PROMPT},
                    {"role": "user", "content": numbered},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            items = data.get("attributes", data.get("items", data if isinstance(data, list) else []))
            if not isinstance(items, list) or len(items) != len(titles):
                raise ValueError("unexpected llm shape")
            return [
                {k: v for k, v in (item or {}).items() if v}
                for item in items
            ]
        except Exception:
            return [extract_attributes_fallback(t) for t in titles]
