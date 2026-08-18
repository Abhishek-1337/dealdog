from .attributes import group_key
from .types import Group, Listing


def _union_find(n: int):
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return find, union


def group_listings(listings: list[Listing]) -> list[Group]:
    n = len(listings)
    if n == 0:
        return []
    find, union = _union_find(n)

    by_id: dict[str, int] = {}
    by_key: dict[tuple, int] = {}
    for i, listing in enumerate(listings):
        for key, value in listing.identifiers.items():
            sig = f"{key}:{str(value).lower()}"
            if sig in by_id:
                union(i, by_id[sig])
            else:
                by_id[sig] = i
        key = group_key(listing.attributes)
        if key in by_key:
            union(i, by_key[key])
        else:
            by_key[key] = i

    buckets: dict[int, list[Listing]] = {}
    for i, listing in enumerate(listings):
        buckets.setdefault(find(i), []).append(listing)

    groups: list[Group] = []
    for members in buckets.values():
        members.sort(key=lambda item: item.price)
        attrs = _merge_attributes(members)
        groups.append(Group(attributes=attrs, listings=members))
    groups.sort(key=lambda g: g.listings[0].price)
    return groups


def _merge_attributes(members: list[Listing]) -> dict:
    merged: dict = {}
    for listing in members:
        for key, value in listing.attributes.items():
            if value and key not in merged:
                merged[key] = value
    return merged
