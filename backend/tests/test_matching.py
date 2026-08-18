from app.config import Settings
from app.matching import resolve_group
from app.types import Group, Listing, ProductRecord


class FakeRepo:
    def __init__(self, nearest, by_id=None):
        self.nearest = nearest
        self.by_id = by_id

    def find_nearest(self, embedding, top_k):
        return self.nearest

    def find_by_identifier(self, values):
        return self.by_id


def product(id_, brand="apple", identifiers=None):
    return ProductRecord(id=id_, title="t", attributes={"brand": brand}, identifiers=identifiers or [])


def group(attrs=None, identifiers=None):
    attrs = attrs or {"brand": "apple"}
    listing = Listing(site="amazon", title="t", price=1.0, identifiers=identifiers or {})
    return Group(attributes=attrs, listings=[listing])


def settings():
    return Settings(openai_api_key="", database_url="")


def test_new_when_nothing_tracked():
    m = resolve_group(group(), [0.0], FakeRepo([]), settings())
    assert m.status == "new"
    assert m.existing_product_id is None


def test_matched_by_hard_identifier():
    repo = FakeRepo([], by_id=product(7))
    m = resolve_group(group(identifiers={"asin": "A1"}), [0.0], repo, settings())
    assert m.status == "matched"
    assert m.existing_product_id == 7
    assert m.similarity == 1.0


def test_matched_by_embedding():
    repo = FakeRepo([(product(3), 0.95)])
    m = resolve_group(group(), [0.0], repo, settings())
    assert m.status == "matched"
    assert m.existing_product_id == 3


def test_needs_confirmation():
    repo = FakeRepo([(product(3), 0.85)])
    m = resolve_group(group(), [0.0], repo, settings())
    assert m.status == "needs_confirmation"
    assert m.candidate_product_id == 3


def test_new_on_low_similarity():
    repo = FakeRepo([(product(3), 0.3)])
    m = resolve_group(group(), [0.0], repo, settings())
    assert m.status == "new"


def test_brand_conflict_overrides_similarity():
    repo = FakeRepo([(product(3, brand="samsung"), 0.95)])
    m = resolve_group(group(attrs={"brand": "apple"}), [0.0], repo, settings())
    assert m.status == "new"
