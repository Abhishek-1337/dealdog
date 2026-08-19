from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

from . import history, pipeline
from .deps import AppContext, get_context
from .llm import LLMUnavailable
from .schemas import (
    PriceHistoryOut,
    ProductDetail,
    SearchResponse,
    TrackedProductOut,
    TrackRequest,
    TrackResponse,
)

router = APIRouter(prefix="/api")


def _history_out(ctx: AppContext, product_id: int) -> PriceHistoryOut:
    records = ctx.repo.get_price_history(product_id)
    return PriceHistoryOut(**asdict(history.build_history(product_id, records, ctx.settings)))


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/search", response_model=SearchResponse)
def search(q: str, ctx: AppContext = Depends(get_context)):
    try:
        return pipeline.search(q, ctx.repo, ctx.llm, ctx.embedder, ctx.settings)
    except LLMUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/track", response_model=TrackResponse)
def track(payload: TrackRequest, ctx: AppContext = Depends(get_context)):
    try:
        return pipeline.track(payload, ctx.repo, ctx.embedder)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"product {exc.args[0]} not found") from exc


@router.get("/tracked", response_model=list[TrackedProductOut])
def tracked(ctx: AppContext = Depends(get_context)):
    return [
        TrackedProductOut(
            product_id=product.id,
            title=product.title,
            attributes=product.attributes,
            price_history=_history_out(ctx, product.id),
        )
        for _tracked, product in ctx.repo.get_tracked()
    ]


@router.get("/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: int, ctx: AppContext = Depends(get_context)):
    product = ctx.repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    return ProductDetail(
        id=product.id,
        title=product.title,
        attributes=product.attributes,
        price_history=_history_out(ctx, product.id),
    )


@router.get("/products/{product_id}/history", response_model=PriceHistoryOut)
def product_history(product_id: int, ctx: AppContext = Depends(get_context)):
    """Per-site price series for the trend graph, plus best/lowest price and drops."""
    if ctx.repo.get_product(product_id) is None:
        raise HTTPException(status_code=404, detail="product not found")
    return _history_out(ctx, product_id)


@router.post("/products/{product_id}/history", response_model=PriceHistoryOut)
def refresh_history(product_id: int, ctx: AppContext = Depends(get_context)):
    """Run a scrape round and append its results, then return the grown history."""
    try:
        result = pipeline.record_scrape(product_id, ctx.repo, ctx.settings)
    except KeyError:
        raise HTTPException(status_code=404, detail="product not found") from None
    return PriceHistoryOut(**asdict(result))
