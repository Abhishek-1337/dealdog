from fastapi import APIRouter, Depends, HTTPException

from . import pipeline
from .deps import AppContext, get_context
from .schemas import (
    PricePointOut,
    ProductDetail,
    SearchResponse,
    TrackedProductOut,
    TrackRequest,
    TrackResponse,
)

router = APIRouter(prefix="/api")


def _history_out(history):
    return [PricePointOut(**h.__dict__) for h in history]


def _best_price(history):
    if not history:
        return None, "USD"
    return min(h.price for h in history), history[0].currency


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/search", response_model=SearchResponse)
def search(q: str, ctx: AppContext = Depends(get_context)):
    return pipeline.search(q, ctx.repo, ctx.llm, ctx.embedder, ctx.settings)


@router.post("/track", response_model=TrackResponse)
def track(payload: TrackRequest, ctx: AppContext = Depends(get_context)):
    try:
        return pipeline.track(payload, ctx.repo, ctx.embedder)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"product {exc.args[0]} not found") from exc


@router.get("/tracked", response_model=list[TrackedProductOut])
def tracked(ctx: AppContext = Depends(get_context)):
    out = []
    for _tracked, product in ctx.repo.get_tracked():
        history = ctx.repo.get_price_history(product.id)
        best, currency = _best_price(history)
        out.append(
            TrackedProductOut(
                product_id=product.id,
                title=product.title,
                attributes=product.attributes,
                best_price=best,
                currency=currency,
                history=_history_out(history),
            )
        )
    return out


@router.get("/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: int, ctx: AppContext = Depends(get_context)):
    product = ctx.repo.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    history = ctx.repo.get_price_history(product.id)
    best, currency = _best_price(history)
    return ProductDetail(
        id=product.id,
        title=product.title,
        attributes=product.attributes,
        best_price=best,
        currency=currency,
        history=_history_out(history),
    )
