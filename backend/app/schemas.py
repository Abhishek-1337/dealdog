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
    price: float | None
    currency: str
    link: str
    recorded_at: str
    scrape_success: bool = True


class PriceDropOut(BaseModel):
    site: str
    current_price: float
    baseline_average: float
    percent: float
    absolute: float
    recorded_at: str


class SiteSeriesOut(BaseModel):
    """One retailer's own price line, plus its own independent drop verdict."""

    site: str
    points: list[PricePointOut]
    latest_price: float | None
    latest_at: str | None
    baseline_average: float | None
    drop: PriceDropOut | None


class PriceHistoryOut(BaseModel):
    product_id: int
    currency: str
    sites: list[SiteSeriesOut]
    best_price: float | None
    best_site: str | None
    lowest_price: float | None
    lowest_site: str | None
    lowest_at: str | None
    drops: list[PriceDropOut]
    records: list[PricePointOut]


class TrackedProductOut(BaseModel):
    product_id: int
    title: str
    attributes: dict
    price_history: PriceHistoryOut


class ProductDetail(BaseModel):
    id: int
    title: str
    attributes: dict
    price_history: PriceHistoryOut
