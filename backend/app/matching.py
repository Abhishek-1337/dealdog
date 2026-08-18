from .config import Settings
from .types import Group, GroupMatch, Listing


def _shared_identifier_values(listings: list[Listing]) -> set[str]:
    values: set[str] = set()
    for listing in listings:
        for key, value in listing.identifiers.items():
            values.add(f"{key}:{str(value).lower()}")
    return values


def _conflict_rule(key: str, group_attrs: dict, product_attrs: dict, similarity: float) -> float:
    """Veto a match when both sides state `key` and disagree.

    Only a stated disagreement vetoes; a missing value on either side is not
    evidence, so a listing that never named its brand still matches.
    """
    a = str(group_attrs.get(key, "") or "").strip().lower()
    b = str(product_attrs.get(key, "") or "").strip().lower()
    if a and b and a != b:
        return 0.0
    return similarity


def resolve_group(group: Group, embedding: list[float], repo, settings: Settings) -> GroupMatch:
    ids = _shared_identifier_values(group.listings)
    if ids:
        match = repo.find_by_identifier(ids)
        if match:
            return GroupMatch("matched", match.id, None, 1.0, 1.0)

    nearest = repo.find_nearest(embedding, settings.top_k)
    if not nearest:
        return GroupMatch("new", None, None, None, 1.0)

    best_product, best_sim = nearest[0]
    # Now that every category shares one embedding space, a phone case and the
    # phone it fits can sit close together. A stated category or item mismatch
    # rules the pair out before a near-miss similarity can merge two products.
    sim = best_sim
    for key in ("brand", "category", "item"):
        sim = _conflict_rule(key, group.attributes, best_product.attributes, sim)

    if sim >= settings.match_threshold:
        return GroupMatch("matched", best_product.id, None, sim, sim)
    if sim >= settings.pending_low:
        return GroupMatch("needs_confirmation", None, best_product.id, sim, sim)
    return GroupMatch("new", None, None, sim, sim)
