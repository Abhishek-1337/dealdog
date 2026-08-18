from . import dummy
from .attributes import canonical_title
from .config import Settings
from .grouping import group_listings
from .matching import resolve_group
from .schemas import GroupOut, ListingOut, SearchResponse, TrackResponse
from .types import Listing, RawListing


def _to_listing(raw: RawListing) -> Listing:
    return Listing(
        site=raw.site,
        title=raw.title,
        price=raw.price,
        currency=raw.currency,
        link=raw.link,
        identifiers=raw.identifiers,
    )


def search(query: str, repo, llm, embedder, settings: Settings) -> SearchResponse:
    raw_results = dummy.search(query)
    listings = [_to_listing(r) for r in raw_results]
    if not listings:
        return SearchResponse(query=query, groups=[])

    titles = [item.title for item in listings]
    attrs_list = llm.extract_attributes_batch(titles)
    for listing, attrs in zip(listings, attrs_list, strict=False):
        listing.attributes = {k: v for k, v in attrs.items() if k != "group"}
        listing.group = str(attrs.get("group", "") or "").strip().lower()

    relevant = llm.filter_relevant(query, titles, attrs_list)
    listings = [item for item, keep in zip(listings, relevant, strict=False) if keep]
    if not listings:
        return SearchResponse(query=query, groups=[])

    groups = group_listings(listings)

    groups_out: list[GroupOut] = []
    for group in groups:
        group.canonical_title = canonical_title(group.attributes)
        embedding = embedder.embed(group.canonical_title)
        match = resolve_group(group, embedding, repo, settings)
        best = min(group.listings, key=lambda item: item.price)
        listings_out = [
            ListingOut(
                site=item.site,
                title=item.title,
                price=item.price,
                currency=item.currency,
                link=item.link,
                best=item is best,
            )
            for item in group.listings
        ]
        groups_out.append(
            GroupOut(
                attributes=group.attributes,
                canonical_title=group.canonical_title,
                match_status=match.status,
                existing_product_id=match.existing_product_id,
                candidate_product_id=match.candidate_product_id,
                similarity=match.similarity,
                confidence=match.confidence,
                listings=listings_out,
            )
        )

    return SearchResponse(query=query, groups=groups_out)


def track(payload, repo, embedder) -> TrackResponse:
    listings = [
        Listing(
            site=item.site,
            title=item.title,
            price=item.price,
            currency=item.currency,
            link=item.link,
        )
        for item in payload.listings
    ]

    if payload.product_id is not None:
        product = repo.get_product(payload.product_id)
        if product is None:
            raise KeyError(payload.product_id)
        repo.add_price_points(product.id, listings)
        tracked = repo.create_tracked(product.id)
        return TrackResponse(
            product_id=product.id,
            tracked_product_id=tracked.id,
            reused_existing=True,
            title=product.title,
        )

    title = canonical_title(payload.attributes)
    embedding = embedder.embed(title)
    identifiers = sorted({f"{k}:{str(v).lower()}" for item in listings for k, v in item.identifiers.items()})
    product = repo.create_product(title, payload.attributes, identifiers, embedding)
    repo.add_price_points(product.id, listings)
    tracked = repo.create_tracked(product.id)
    return TrackResponse(
        product_id=product.id,
        tracked_product_id=tracked.id,
        reused_existing=False,
        title=product.title,
    )

