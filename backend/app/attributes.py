import re

BRANDS = [
    "apple",
    "samsung",
    "google",
    "sony",
    "dell",
    "hp",
    "lenovo",
    "asus",
    "microsoft",
    "oneplus",
    "motorola",
    "lg",
    "bose",
    "logitech",
]

# Attributes every category has. Everything else is an open-ended spec whose
# keys depend on the category — "chip"/"ram"/"storage" for a laptop,
# "screen_size"/"panel" for a TV, "size"/"color" for a shoe.
CORE_KEYS = ("brand", "category", "item", "model")

# Not part of a product's identity: the model's own grouping hint (grouping
# consumes it separately) and brand, which is deliberately excluded so a
# brand-less listing still groups with its siblings and cross-brand conflicts
# are caught later by the matching brand rule instead.
NON_IDENTITY_KEYS = frozenset({"brand", "group"})


def _brand(t: str) -> str | None:
    return next((b for b in BRANDS if b in t), None)


def _model(t: str) -> str | None:
    m = re.search(r"\b(macbook\s+(?:air|pro))\b", t)
    if m:
        return f"MacBook {m.group(1).split()[-1].title()}"
    m = re.search(r"\biphone\s+(\d+)\b", t)
    if m:
        return f"iPhone {m.group(1)}"
    m = re.search(r"\bgalaxy\s+s(\d+)\s*(ultra|plus)?", t)
    if m:
        suffix = f" {m.group(2).title()}" if m.group(2) else ""
        return f"Galaxy S{m.group(1)}{suffix}"
    m = re.search(r"\bpixel\s+(\d+)\b", t)
    if m:
        return f"Pixel {m.group(1)}"
    return None


def _chip(t: str) -> str | None:
    if re.search(r"\bm3\s+pro\b", t):
        return "M3 Pro"
    if re.search(r"\bm3\s+max\b", t):
        return "M3 Max"
    if re.search(r"\bm3\b", t):
        return "M3"
    if re.search(r"\bm2\s+pro\b", t):
        return "M2 Pro"
    if re.search(r"\bm2\b", t):
        return "M2"
    if re.search(r"\bm1\b", t):
        return "M1"
    if re.search(r"\bsnapdragon\b", t):
        return "Snapdragon"
    m = re.search(r"\bintel\s+core\s+(i\d)\b", t)
    if m:
        return f"Intel Core {m.group(1).upper()}"
    return None


def _ram_storage(t: str) -> tuple[str | None, str | None]:
    ram = None
    storage = None
    m = re.search(r"(\d+)\s*gb\s*/\s*(\d+)\s*gb", t)
    if m:
        ram, storage = m.group(1), m.group(2)
    else:
        m = re.search(r"(\d+)\s*/\s*(\d+)\s*gb", t)
        if m:
            ram, storage = m.group(1), m.group(2)
    if not ram:
        m = re.search(r"(\d+)\s*gb\s*(?:ram|memory)", t)
        if m:
            ram = m.group(1)
    if not storage:
        m = re.search(r"(\d+)\s*gb\s*(?:ssd|storage|flash|drive)", t)
        if m:
            storage = m.group(1)
    return (f"{ram}GB" if ram else None, f"{storage}GB" if storage else None)


# Words that mean "this is a thing made for another thing". Category-agnostic:
# a mount, a strap and a filter are accessories in any department.
ACCESSORY_WORDS = (
    "case",
    "cover",
    "sleeve",
    "skin",
    "protector",
    "bumper",
    "mount",
    "stand",
    "strap",
    "band",
    "charger",
    "cable",
    "adapter",
    "filter",
    "bag",
    "pouch",
)

_ACCESSORY_RE = re.compile(r"\b(" + "|".join(ACCESSORY_WORDS) + r")\b")


def _item(t: str) -> str | None:
    """Best-effort product class for the no-API-key path.

    Only recognizes the handful of categories the regexes below know about; the
    LLM extractor is what generalizes. Returning None is the honest answer for
    anything else, and callers treat it as "unknown", not "irrelevant".
    """
    accessory = _ACCESSORY_RE.search(t)
    if accessory:
        return accessory.group(1)
    if re.search(r"\bmacbook\b", t):
        return "laptop"
    if re.search(r"\b(iphone|galaxy|pixel|oneplus|motorola)\b", t):
        return "smartphone"
    if re.search(r"\bipad\b", t):
        return "tablet"
    return None


def extract_attributes_fallback(title: str) -> dict:
    t = title.lower()
    attrs: dict = {}
    brand = _brand(t)
    if brand:
        attrs["brand"] = brand
    model = _model(t)
    if model:
        attrs["model"] = model
    chip = _chip(t)
    if chip:
        attrs["chip"] = chip
    ram, storage = _ram_storage(t)
    if ram:
        attrs["ram"] = ram
    if storage:
        attrs["storage"] = storage
    item = _item(t)
    if item:
        attrs["item"] = item
    return attrs


def extract_query_constraints(query: str) -> dict:
    t = query.lower()
    constraints: dict = {}
    brand = _brand(t)
    if brand:
        constraints["brand"] = brand
    model = _model(t)
    if model:
        constraints["model"] = model
    chip = _chip(t)
    if chip:
        constraints["chip"] = chip
    ram, storage = _ram_storage(t)
    if ram:
        constraints["ram"] = ram
    if storage:
        constraints["storage"] = storage
    return constraints


def matches_constraints(attrs: dict, constraints: dict) -> bool:
    for key, value in constraints.items():
        attr = str(attrs.get(key, "") or "").strip().lower()
        if not attr or value.lower() != attr:
            return False
    return True


def filter_relevant_fallback(query: str, attrs_list: list[dict]) -> list[bool]:
    """Regex stand-in for the LLM relevance pass, used when there is no API key.

    Drops listings that contradict a constraint the query states outright, and
    drops accessories — but only when the shopper wasn't asking for one. A query
    for "macbook case" wants the cases.
    """
    wants_accessory = bool(_ACCESSORY_RE.search(query.lower()))
    constraints = extract_query_constraints(query)
    if not constraints and not wants_accessory:
        return [True] * len(attrs_list)

    result: list[bool] = []
    for attrs in attrs_list:
        if not matches_constraints(attrs, constraints):
            result.append(False)
            continue
        item = str(attrs.get("item", "") or "").strip().lower()
        is_accessory = bool(item) and bool(_ACCESSORY_RE.fullmatch(item))
        result.append(wants_accessory if is_accessory else not wants_accessory)
    return result


def group_key(attrs: dict) -> tuple:
    """A category-agnostic identity key: every attribute that isn't brand.

    Reads whatever keys the extraction produced rather than a fixed list, so a
    TV's screen size separates variants exactly as a laptop's storage does.
    Sorted, so two listings that named the same attributes in a different order
    still land on the same key.

    This is the *fallback* signal for grouping. Listings that share a hard
    identifier or the model's `group` slug are merged regardless of it, which is
    what covers retailers whose titles mention different subsets of the specs.
    """
    return tuple(
        sorted(
            (str(key).strip().lower(), str(value).strip().lower())
            for key, value in attrs.items()
            if str(key).strip().lower() not in NON_IDENTITY_KEYS and str(value).strip()
        )
    )


def canonical_title(attrs: dict) -> str:
    """The text a product's embedding is built from.

    Brand and model lead, then the specs in sorted key order so the same product
    always renders the same string. `category`/`item` are deliberately left out:
    they describe the class rather than the variant, and including them would
    change the wording of every title and so invalidate stored embeddings.
    """
    parts = [str(attrs[key]).strip() for key in ("brand", "model") if attrs.get(key)]
    parts += [
        str(value).strip()
        for key, value in sorted(attrs.items())
        if str(key).strip().lower() not in NON_IDENTITY_KEYS
        and key not in CORE_KEYS
        and str(value).strip()
    ]
    return " ".join(part for part in parts if part).strip()
