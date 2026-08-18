from . import dummy, history
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


def record_scrape(product_id: int, repo, settings: Settings):
    """Run one scrape round for a tracked product and append the results.

    Every site the product has ever been seen on is re-quoted, and every quote
    is written — successes and failures alike. Nothing is overwritten, so calling
    this repeatedly is how a product's price history grows.
    """
    product = repo.get_product(product_id)
    if product is None:
        raise KeyError(product_id)

    records = repo.get_price_history(product_id)
    by_site = history.group_by_site(records)
    if not by_site:
        return history.build_history(product_id, records, settings)

    quotes = []
    for site in sorted(by_site):
        site_records = by_site[site]
        link = next((r.link for r in reversed(site_records) if r.link), "")
        latest = history.latest_successful(site_records)
        quotes.append(dummy.quote(site, link, latest.price if latest else None, len(site_records)))

    repo.add_price_points(product_id, quotes)
    return history.build_history(product_id, repo.get_price_history(product_id), settings)
