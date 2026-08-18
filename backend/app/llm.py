import json

from .attributes import extract_attributes_fallback, filter_relevant_fallback
from .config import Settings

EXTRACT_PROMPT = (
    "Extract structured product attributes from each raw retailer title. "
    "Return ONLY a JSON array with one object per title, in the same order. "
    "Each object must have keys: brand, model, chip, ram, storage, item, group. "
    "Use null for anything missing. Normalize ram/storage to e.g. \"8GB\"/\"256GB\", "
    "and chip to e.g. \"M3\"/\"M3 Pro\"/\"Snapdragon\". "
    "\"item\" is a short noun phrase describing what the product actually is "
    "(e.g. \"laptop\", \"smartphone\", \"phone case\", \"earbuds\", \"tablet\"). "
    "\"group\" is a canonical key that identifies the exact product model/variant, so the same "
    "product sold across retailers gets the SAME group and a clearly different product gets a "
    "DIFFERENT group (e.g. \"macbook-air-m3-8gb-256gb\", \"macbook-air-case\"). "
    "Be sure the group separates accessories (cases, covers) from the device itself. "
    "Example: \"Apple 2024 MacBook Air 13-inch M3 8GB Memory 256GB SSD\" -> "
    '{"brand":"Apple","model":"MacBook Air","chip":"M3","ram":"8GB","storage":"256GB",'
    '"item":"laptop","group":"macbook-air-m3-8gb-256gb"}.'
)

FILTER_PROMPT = (
    "You are deciding which product listings match a user's search query. "
    "You will receive the user's query, then a numbered list of listings with their extracted "
    "attributes. For each listing, decide whether it is relevant to what the user is looking for, "
    "based on the attributes (brand, model, chip, ram, storage) and the \"item\" description of "
    "what the product actually is. A listing whose item is an accessory (case, cover, sleeve) is "
    "NOT relevant to a query for the device itself. "
    "If the query is vague and does not pin down a specific model, chip, ram, storage, or brand "
    "(e.g. \"macbook m\", \"laptop\", \"phone\"), mark ALL listings relevant. "
    'Return ONLY a JSON object of the form {"relevant": [true, false, ...]} with exactly one '
    "boolean per listing, in the same order."
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

    def filter_relevant(self, query: str, titles: list[str], attrs_list: list[dict]) -> list[bool]:
        if not self.client:
            return filter_relevant_fallback(query, attrs_list)
        numbered = "\n".join(
            f"{i}: {t} | attrs={json.dumps(a, sort_keys=True)}"
            for i, (t, a) in enumerate(zip(titles, attrs_list, strict=False))
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": FILTER_PROMPT},
                    {"role": "user", "content": f"QUERY: {query}\n\n{numbered}"},
                ],
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            relevant = data.get("relevant")
            if not isinstance(relevant, list) or len(relevant) != len(titles):
                raise ValueError("unexpected llm shape")
            return [bool(x) for x in relevant]
        except Exception:
            return [True] * len(titles)
