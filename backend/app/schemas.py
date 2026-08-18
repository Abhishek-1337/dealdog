from pydantic import BaseModel


class ListingOut(BaseModel):
    site: str
    title: str
    price: float
    currency: str = "USD"
    link: str = ""
    best: bool = False


class GroupOut(BaseModel):
    attributes: dict
    canonical_title: str
    match_status: str
    existing_product_id: int | None = None
    candidate_product_id: int | None = None
    similarity: float | None = None
    confidence: float = 0.0
    listings: list[ListingOut]


class SearchResponse(BaseModel):
    query: str
    groups: list[GroupOut]


class TrackRequest(BaseModel):
    attributes: dict
    listings: list[ListingOut]
    product_id: int | None = None


class TrackResponse(BaseModel):
    product_id: int
    tracked_product_id: int
    reused_existing: bool
    title: str


class PricePointOut(BaseModel):
    site: str
    price: float
    currency: str
    link: str
    recorded_at: str


class TrackedProductOut(BaseModel):
    product_id: int
    title: str
    attributes: dict
    best_price: float | None
    currency: str
    history: list[PricePointOut]


class ProductDetail(BaseModel):
    id: int
    title: str
    attributes: dict
    best_price: float | None
    currency: str
    history: list[PricePointOut]
