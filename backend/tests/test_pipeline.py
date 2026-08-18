from app import pipeline
from app.schemas import TrackRequest


def test_search_groups_macbook_m3(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    assert result.query == "macbook m3"
    assert len(result.groups) == 2
    assert all(g.attributes.get("item") == "laptop" for g in result.groups)

    eight = next(
        g for g in result.groups
        if g.attributes.get("chip") == "M3"
        and g.attributes.get("ram") == "8GB"
        and g.attributes.get("storage") == "256GB"
    )
    assert len(eight.listings) == 3
    assert eight.match_status == "new"

    sixteen = next(g for g in result.groups if g.attributes.get("storage") == "512GB" and g.attributes.get("chip") == "M3")
    assert len(sixteen.listings) == 2


def test_search_macbook_excludes_accessory(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    assert all("case" not in (g.attributes.get("item") or "") for g in result.groups)


def test_best_listing_flagged(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    eight = next(
        g for g in result.groups if g.attributes.get("chip") == "M3" and g.attributes.get("ram") == "8GB" and g.attributes.get("storage") == "256GB"
    )
    best = [item for item in eight.listings if item.best]
    assert len(best) == 1
    assert best[0].price == min(item.price for item in eight.listings)


def test_search_filters_to_query_chip(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    chips = {g.attributes.get("chip") for g in result.groups}
    assert chips <= {"M3"}


def test_vague_query_returns_all_chips(ctx):
    result = pipeline.search("macbook m", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    chips = {g.attributes.get("chip") for g in result.groups}
    assert "M2" in chips and "M3" in chips and "M3 Pro" in chips


def test_track_then_search_finds_existing(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    eight = next(
        g for g in result.groups if g.attributes.get("chip") == "M3" and g.attributes.get("ram") == "8GB" and g.attributes.get("storage") == "256GB"
    )
    payload = TrackRequest(attributes=eight.attributes, listings=eight.listings, product_id=None)
    tracked = pipeline.track(payload, ctx.repo, ctx.embedder)
    assert tracked.reused_existing is False

    again = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    eight_again = next(
        g for g in again.groups if g.attributes.get("chip") == "M3" and g.attributes.get("ram") == "8GB" and g.attributes.get("storage") == "256GB"
    )
    assert eight_again.match_status == "matched"
    assert eight_again.existing_product_id == tracked.product_id


def test_track_reuses_existing_product(ctx):
    result = pipeline.search("macbook m3", ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    eight = next(
        g for g in result.groups if g.attributes.get("chip") == "M3" and g.attributes.get("ram") == "8GB" and g.attributes.get("storage") == "256GB"
    )
    first = pipeline.track(TrackRequest(attributes=eight.attributes, listings=eight.listings, product_id=None), ctx.repo, ctx.embedder)

    second = pipeline.track(
        TrackRequest(attributes=eight.attributes, listings=eight.listings, product_id=first.product_id),
        ctx.repo,
        ctx.embedder,
    )
    assert second.reused_existing is True
    assert second.product_id == first.product_id
