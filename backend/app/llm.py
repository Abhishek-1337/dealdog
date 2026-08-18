import json

from .attributes import extract_attributes_fallback, filter_relevant_fallback
from .config import Settings

EXTRACT_PROMPT = """\
You extract structured attributes from raw retailer product titles, for any kind \
of product — electronics, appliances, apparel, groceries, furniture, tools, \
anything a shop sells.

Return ONLY a JSON object of the form {"items": [...]} holding one object per \
input title, in the same order. Each object has these keys:

  "brand"    The manufacturer or label. null if the title does not name one.
  "category" The broad product class, lowercase singular: "laptop",
             "smartphone", "television", "running shoe", "coffee maker",
             "office chair", "olive oil".
  "item"     What the object physically is, lowercase singular. Usually the same
             as category — but for an accessory it names the accessory, never the
             product it is made for: "phone case", "laptop sleeve", "charging
             cable", "screen protector", "tv wall mount".
  "model"    The manufacturer's model or product name as sold, without the
             variant details that go in "specs". null if there is none.
  "specs"    An object holding the attributes that distinguish THIS variant from
             other variants of the same model.
  "group"    A canonical slug naming the exact variant.

"specs" is open-ended on purpose — pick the keys that matter for the category, \
because they differ completely between a TV and a bag of coffee. Follow these \
rules:

  * lowercase snake_case keys: "screen_size", "ram", "storage", "capacity",
    "color", "size", "wattage", "count", "roast".
  * Include only what changes the physical thing the buyer receives. Leave out
    marketing language, condition, warranty, seller, bundle and shipping words.
  * Normalize the unit without changing the value: "8GB", "512GB", "1TB",
    "65 in", "1.5 L", "12 oz", "1200 W".
  * If the title does not support a spec, omit the key. Never guess a value.

"group" is what lets the same product from different shops be recognized as one \
product, so it carries the most weight:

  * The same physical variant at different retailers MUST get the same group,
    however differently the two titles are worded.
  * Any difference a buyer would care about — capacity, size, generation, or
    color where color is the point — MUST get a different group.
  * An accessory NEVER shares a group with the product it fits.
  * Format it lowercase and hyphenated, brand and model first, then the
    distinguishing specs.

Examples. Note that the spec keys differ per category — that is correct, not an \
inconsistency to smooth over:

  "Apple 2024 MacBook Air 13-inch Laptop with M3 chip, 8GB Memory, 256GB SSD"
  {"brand":"Apple","category":"laptop","item":"laptop",
   "model":"MacBook Air 13-inch",
   "specs":{"chip":"M3","ram":"8GB","storage":"256GB"},
   "group":"apple-macbook-air-13-m3-8gb-256gb"}

  "LG C4 65\\" Class OLED evo 4K Smart TV (2024 Model)"
  {"brand":"LG","category":"television","item":"television",
   "model":"C4 OLED evo",
   "specs":{"screen_size":"65 in","resolution":"4K","panel":"OLED"},
   "group":"lg-c4-oled-evo-65-4k"}

  "Nike Pegasus 41 Men's Road Running Shoes, Black/White, Size 10"
  {"brand":"Nike","category":"running shoe","item":"running shoe",
   "model":"Pegasus 41",
   "specs":{"gender":"men","color":"black/white","size":"10"},
   "group":"nike-pegasus-41-mens-black-white-10"}

  "Spigen Ultra Hybrid Case for iPhone 15, Matte Black"
  {"brand":"Spigen","category":"phone case","item":"phone case",
   "model":"Ultra Hybrid",
   "specs":{"fits":"iPhone 15","color":"matte black"},
   "group":"spigen-ultra-hybrid-iphone-15-matte-black"}

Use null for a missing brand, model, category or item, and {} for empty specs.\
"""

FILTER_PROMPT = """\
Decide which retailer listings actually answer a shopper's search query. You \
receive the query, then a numbered list of listings with the attributes \
extracted from each.

Mark a listing NOT relevant when:

  * Its "item" is an accessory for the thing the shopper asked for rather than
    the thing itself — a case for a phone query, a wall mount for a TV query, a
    lens cap for a camera query — unless the query asks for that accessory.
  * It contradicts something the query states outright: a different brand, a
    different model or generation, or a different value for a spec the query
    pins down.
  * It is a different product class than the query describes.

Otherwise mark it relevant. In particular:

  * A query naming no brand, model or spec ("laptop", "running shoes", "coffee
    maker") constrains nothing. Mark every listing of that class relevant and
    let price ranking sort them out.
  * A partial or ambiguous fragment ("macbook m", "galaxy s", "size 1") does not
    pin down a generation or value. Do not guess which one was meant — keep all
    the candidates.
  * Silence is not a contradiction. A listing that simply does not mention a spec
    the query asks about stays relevant; only a stated, different value rules it
    out.

Return ONLY {"relevant": [true, false, ...]} with exactly one boolean per \
listing, in the input order.\
"""


def _flatten(item: dict | None) -> dict:
    """Fold the model's nested `specs` up into one flat attribute dict.

    The rest of the pipeline treats attributes as an opaque flat mapping — it
    groups on them, renders them as chips and stores them as JSON — so the
    nesting only exists to make the prompt's intent clear to the model. Core
    keys win a name collision, and empty values are dropped so a missing spec
    never becomes the string "None".
    """
    item = item or {}
    attrs: dict = {}
    specs = item.get("specs")
    if isinstance(specs, dict):
        for key, value in specs.items():
            name = str(key).strip().lower().replace(" ", "_")
            if name and value:
                attrs[name] = value
    for key in ("brand", "category", "item", "model"):
        value = item.get(key)
        if value:
            attrs[key] = value
    group = item.get("group")
    if group:
        attrs["group"] = group
    return attrs


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
            if isinstance(data, list):
                items = data
            else:
                items = data.get("items", data.get("attributes", []))
            if not isinstance(items, list) or len(items) != len(titles):
                raise ValueError("unexpected llm shape")
            return [_flatten(item) for item in items]
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
