from .config import Settings
from .types import Group, GroupMatch, Listing


def _shared_identifier_values(listings: list[Listing]) -> set[str]:
    values: set[str] = set()
    for listing in listings:
        for key, value in listing.identifiers.items():
            values.add(f"{key}:{str(value).lower()}")
    return values


def _brand_rule(group_attrs: dict, product_attrs: dict, similarity: float) -> float:
    gb = str(group_attrs.get("brand", "")).lower()
    pb = str(product_attrs.get("brand", "")).lower()
    if gb and pb and gb != pb:
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
    sim = _brand_rule(group.attributes, best_product.attributes, best_sim)

    if sim >= settings.match_threshold:
        return GroupMatch("matched", best_product.id, None, sim, sim)
    if sim >= settings.pending_low:
        return GroupMatch("needs_confirmation", None, best_product.id, sim, sim)
    return GroupMatch("new", None, None, sim, sim)
