from app.attributes import (
    canonical_title,
    extract_attributes_fallback,
    extract_query_constraints,
    filter_relevant_fallback,
    group_key,
)


def test_extract_macbook_attributes():
    attrs = extract_attributes_fallback(
        "Apple 2024 MacBook Air 13-inch Laptop with M3 chip, 8GB Memory, 256GB SSD - Space Gray"
    )
    assert attrs["brand"] == "apple"
    assert attrs["model"] == "MacBook Air"
    assert attrs["chip"] == "M3"
    assert attrs["ram"] == "8GB"
    assert attrs["storage"] == "256GB"


def test_extract_slash_notation():
    attrs = extract_attributes_fallback('MacBook Air 13" M3 8/256GB Space Gray Laptop')
    assert attrs["ram"] == "8GB"
    assert attrs["storage"] == "256GB"


def test_extract_gb_slash_gb():
    attrs = extract_attributes_fallback("Apple MacBook Air M3 16GB/512GB 13.6-inch Midnight")
    assert attrs["ram"] == "16GB"
    assert attrs["storage"] == "512GB"


def test_group_key_normalizes():
    assert group_key({"brand": "Apple", "chip": "M3", "ram": "8GB"}) == ("", "m3", "8gb", "")


def test_canonical_title():
    attrs = {"brand": "Apple", "model": "MacBook Air", "chip": "M3", "ram": "8GB", "storage": "256GB"}
    assert canonical_title(attrs) == "Apple MacBook Air M3 8GB 256GB"


def test_query_constraints_specific_chip():
    assert extract_query_constraints("macbook m3") == {"chip": "M3"}


def test_query_constraints_vague():
    assert extract_query_constraints("macbook m") == {}


def test_filter_relevant_fallback():
    attrs = [{"chip": "M3"}, {"chip": "M2"}, {"chip": "M3 Pro"}]
    assert filter_relevant_fallback("macbook m3", attrs) == [True, False, False]
    assert filter_relevant_fallback("macbook m", attrs) == [True, True, True]
