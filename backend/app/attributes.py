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

KEYS = ["model", "chip", "ram", "storage"]

TITLE_ORDER = ["brand", "model", "chip", "ram", "storage"]


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


def _item(t: str) -> str | None:
    if re.search(r"\b(case|cover|sleeve|skin|protector|bumper|keyboard)\b", t):
        return "case"
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
    constraints = extract_query_constraints(query)
    if not constraints:
        return [True] * len(attrs_list)
    result: list[bool] = []
    for attrs in attrs_list:
        if not matches_constraints(attrs, constraints):
            result.append(False)
            continue
        item = str(attrs.get("item", "") or "").strip().lower()
        if item in {"case", "cover"}:
            result.append(False)
            continue
        result.append(True)
    return result


def group_key(attrs: dict) -> tuple:
    return tuple(str(attrs.get(k, "")).strip().lower() for k in KEYS)


def canonical_title(attrs: dict) -> str:
    parts = [str(attrs[k]) for k in TITLE_ORDER if attrs.get(k)]
    return " ".join(parts).strip()
