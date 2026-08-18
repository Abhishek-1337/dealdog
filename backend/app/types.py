from dataclasses import dataclass, field


@dataclass
class RawListing:
    site: str
    title: str
    price: float
    currency: str = "USD"
    link: str = ""
    identifiers: dict = field(default_factory=dict)


@dataclass
class Listing:
    site: str
    title: str
    price: float
    currency: str = "USD"
    link: str = ""
    identifiers: dict = field(default_factory=dict)
    attributes: dict = field(default_factory=dict)
    group: str = ""


@dataclass
class Group:
    attributes: dict
    listings: list[Listing]
    canonical_title: str = ""


@dataclass
class GroupMatch:
    status: str
    existing_product_id: int | None
    candidate_product_id: int | None
    similarity: float | None
    confidence: float


@dataclass
class ProductRecord:
    id: int
    title: str
    attributes: dict
    identifiers: list


@dataclass
class TrackedRecord:
    id: int
    product_id: int


@dataclass
class PriceRecord:
    """One append-only price observation. ``price`` is None when the scrape failed."""

    site: str
    price: float | None
    currency: str
    link: str
    recorded_at: str
    scrape_success: bool = True


@dataclass
class Quote:
    """A single site's result for one scrape round, success or failure."""

    site: str
    price: float | None
    currency: str = "USD"
    link: str = ""
    scrape_success: bool = True


@dataclass
class PriceDrop:
    """A confirmed drop on one site, measured against that site's own recent average."""

    site: str
    current_price: float
    baseline_average: float
    percent: float
    absolute: float
    recorded_at: str


@dataclass
class SiteSeries:
    site: str
    points: list[PriceRecord]
    latest_price: float | None
    latest_at: str | None
    baseline_average: float | None
    drop: PriceDrop | None


@dataclass
class PriceHistory:
    product_id: int
    currency: str
    sites: list[SiteSeries]
    best_price: float | None
    best_site: str | None
    lowest_price: float | None
    lowest_site: str | None
    lowest_at: str | None
    drops: list[PriceDrop]
    records: list[PriceRecord]
