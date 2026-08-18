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


def test_category_conflict_overrides_similarity():
    # A phone case and the phone it fits can embed close together once every
    # category shares one vector space; the stated category must rule it out.
    case = ProductRecord(
        id=4, title="t", attributes={"brand": "apple", "category": "phone case"}, identifiers=[]
    )
    repo = FakeRepo([(case, 0.96)])
    m = resolve_group(
        group(attrs={"brand": "apple", "category": "smartphone"}), [0.0], repo, settings()
    )
    assert m.status == "new"


def test_item_conflict_overrides_similarity():
    sleeve = ProductRecord(
        id=5, title="t", attributes={"brand": "apple", "item": "laptop sleeve"}, identifiers=[]
    )
    repo = FakeRepo([(sleeve, 0.97)])
    m = resolve_group(group(attrs={"brand": "apple", "item": "laptop"}), [0.0], repo, settings())
    assert m.status == "new"


def test_missing_category_is_not_a_conflict():
    # Silence is not evidence: a listing that never named its category still matches.
    tracked = ProductRecord(
        id=6, title="t", attributes={"brand": "apple", "category": "laptop"}, identifiers=[]
    )
    repo = FakeRepo([(tracked, 0.95)])
    m = resolve_group(group(attrs={"brand": "apple"}), [0.0], repo, settings())
    assert m.status == "matched"
    assert m.existing_product_id == 6


def test_same_category_still_matches():
    tracked = ProductRecord(
        id=8, title="t", attributes={"brand": "apple", "category": "laptop"}, identifiers=[]
    )
    repo = FakeRepo([(tracked, 0.95)])
    m = resolve_group(group(attrs={"brand": "apple", "category": "laptop"}), [0.0], repo, settings())
    assert m.status == "matched"
