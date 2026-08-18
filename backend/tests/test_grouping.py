from app.attributes import extract_attributes_fallback
from app.grouping import group_listings
from app.types import Listing


def make_listing(site, title, price, identifiers=None):
    attrs = extract_attributes_fallback(title)
    return Listing(site=site, title=title, price=price, identifiers=identifiers or {}, attributes=attrs)


def test_same_hard_identifier_grouped():
    a = make_listing("amazon", "Apple MacBook Air M3 8GB Memory 256GB SSD", 1099, {"asin": "A1"})
    b = make_listing("bestbuy", "MacBook Air M3 8GB 256GB", 1049, {"asin": "A1"})
    groups = group_listings([a, b])
    assert len(groups) == 1
    assert len(groups[0].listings) == 2


def test_same_attributes_grouped_without_identifier():
    a = make_listing("amazon", "Apple MacBook Air M3 8GB Memory 256GB SSD", 1099)
    b = make_listing("walmart", 'MacBook Air 13" M3 8/256GB', 1029)
    groups = group_listings([a, b])
    assert len(groups) == 1


def test_different_specs_separated():
    a = make_listing("amazon", "Apple MacBook Air M3 8GB Memory 256GB SSD", 1099)
    b = make_listing("amazon", "Apple MacBook Air M3 16GB Memory 512GB SSD", 1399)
    groups = group_listings([a, b])
    assert len(groups) == 2


def test_accessory_not_grouped_with_laptop():
    laptop = make_listing("amazon", "Apple MacBook Air M3 8GB Memory 256GB SSD", 1099)
    case = make_listing("amazon", "Apple MacBook Air M3 13-inch Clear Case Cover", 19)
    groups = group_listings([laptop, case])
    assert len(groups) == 2
