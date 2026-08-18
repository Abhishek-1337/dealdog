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


def test_group_key_normalizes_and_drops_brand():
    assert group_key({"brand": "Apple", "chip": "M3", "ram": "8GB"}) == (
        ("chip", "m3"),
        ("ram", "8gb"),
    )


def test_group_key_ignores_attribute_order():
    a = {"chip": "M3", "ram": "8GB", "storage": "256GB"}
    b = {"storage": "256GB", "chip": "M3", "ram": "8GB"}
    assert group_key(a) == group_key(b)


def test_group_key_separates_variants_of_any_category():
    # A TV's screen size must split variants exactly as a laptop's storage does.
    small = {"brand": "LG", "category": "television", "screen_size": "55 in", "panel": "OLED"}
    large = {"brand": "LG", "category": "television", "screen_size": "65 in", "panel": "OLED"}
    assert group_key(small) != group_key(large)

    shoe_9 = {"brand": "Nike", "category": "running shoe", "size": "9", "color": "black"}
    shoe_10 = {"brand": "Nike", "category": "running shoe", "size": "10", "color": "black"}
    assert group_key(shoe_9) != group_key(shoe_10)


def test_group_key_ignores_the_grouping_hint():
    # `group` is consumed by grouping directly; it must not also leak into the key.
    with_hint = {"chip": "M3", "group": "apple-macbook-air-m3"}
    assert group_key(with_hint) == group_key({"chip": "M3"})


def test_canonical_title():
    attrs = {"brand": "Apple", "model": "MacBook Air", "chip": "M3", "ram": "8GB", "storage": "256GB"}
    assert canonical_title(attrs) == "Apple MacBook Air M3 8GB 256GB"


def test_canonical_title_is_stable_across_attribute_order():
    a = {"brand": "LG", "model": "C4", "screen_size": "65 in", "panel": "OLED"}
    b = {"panel": "OLED", "model": "C4", "screen_size": "65 in", "brand": "LG"}
    assert canonical_title(a) == canonical_title(b)


def test_canonical_title_omits_class_and_hint_keys():
    # category/item describe the class, not the variant, and would otherwise
    # reword every stored embedding's source text.
    attrs = {
        "brand": "Nike",
        "model": "Pegasus 41",
        "category": "running shoe",
        "item": "running shoe",
        "group": "nike-pegasus-41-black-10",
        "color": "black",
        "size": "10",
    }
    assert canonical_title(attrs) == "Nike Pegasus 41 black 10"


def test_query_constraints_specific_chip():
    assert extract_query_constraints("macbook m3") == {"chip": "M3"}


def test_query_constraints_vague():
    assert extract_query_constraints("macbook m") == {}


def test_filter_relevant_fallback():
    attrs = [{"chip": "M3"}, {"chip": "M2"}, {"chip": "M3 Pro"}]
    assert filter_relevant_fallback("macbook m3", attrs) == [True, False, False]
    assert filter_relevant_fallback("macbook m", attrs) == [True, True, True]


def test_accessory_query_keeps_accessories():
    # The old fallback dropped every case unconditionally, so "macbook case"
    # returned nothing at all.
    attrs = [{"item": "case", "model": "MacBook Air"}, {"item": "laptop", "model": "MacBook Air"}]
    assert filter_relevant_fallback("macbook case", attrs) == [True, False]


def test_device_query_drops_accessories():
    attrs = [{"item": "case", "chip": "M3"}, {"item": "laptop", "chip": "M3"}]
    assert filter_relevant_fallback("macbook m3", attrs) == [False, True]


def test_unknown_item_is_kept():
    # None means "the regexes did not recognize it", not "irrelevant".
    attrs = [{"chip": "M3"}]
    assert filter_relevant_fallback("macbook m3", attrs) == [True]


def test_keyboard_is_not_called_a_case():
    attrs = extract_attributes_fallback("Apple Magic Keyboard for iPad Pro")
    assert attrs.get("item") != "case"
