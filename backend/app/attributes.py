"""Canonicalization of attributes that the LLM has already extracted.

There is deliberately no extraction logic here. Attributes come from one place
only — `llm.LLMClient.extract_attributes_batch` — so a scraped title and a
dummy-catalog title travel exactly the same path. This module just normalizes
what came back so two shops' wordings collapse onto one grouping key.
"""

import re

CORE_KEYS = ("brand", "category", "item", "model")

# `brand` is matched separately (a brandless listing must still group with its
# branded twin) and `group` is consumed by grouping directly, so neither belongs
# in the identity key.
NON_IDENTITY_KEYS = frozenset({"brand", "group"})

_UNIT_SPACE_RE = re.compile(r"(\d)\s+(?=[a-z])")
_WS_RE = re.compile(r"\s+")


def _normalize_value(value) -> str:
    """Fold the cosmetic differences between two shops' spellings of one value.

    Case and spacing only — "8 GB" and "8GB" are the same variant, "8GB" and
    "16GB" are not. Unit *names* are left alone; the extraction prompt already
    normalizes those, and stripping them here would make "1 TB" and "1 GB"
    collide.
    """
    v = _WS_RE.sub(" ", str(value).strip().lower())
    return _UNIT_SPACE_RE.sub(r"\1", v)


def group_key(attrs: dict) -> tuple:
    """The identity of a variant: every stated attribute except brand/group."""
    return tuple(
        sorted(
            (_WS_RE.sub(" ", str(key).strip().lower()), _normalize_value(value))
            for key, value in attrs.items()
            if str(key).strip().lower() not in NON_IDENTITY_KEYS and str(value).strip()
        )
    )


def canonical_title(attrs: dict) -> str:
    """The text a group is embedded as: brand, model, then its specs sorted.

    Sorted so that the same variant produces the same string regardless of the
    key order the model happened to emit, and without `category`/`item`, which
    describe the class rather than the variant.
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
