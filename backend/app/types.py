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
    site: str
    price: float
    currency: str
    link: str
    recorded_at: str
