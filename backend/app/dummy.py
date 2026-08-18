import re

from .types import RawListing

CATALOG: list[RawListing] = [
    RawListing("amazon", "Apple 2024 MacBook Air 13-inch Laptop with M3 chip, 8GB Memory, 256GB SSD - Space Gray", 1099.0, link="https://amazon.com/dp/xm5a", identifiers={"asin": "A1001"}),
    RawListing("bestbuy", 'Apple MacBook Air 13.6" M3 8GB RAM 256GB SSD Space Gray (2024)', 1049.0, link="https://bestbuy.com/xm5a", identifiers={"asin": "A1001"}),
    RawListing("walmart", 'MacBook Air 13" M3 8/256GB Space Gray Laptop', 1029.0, link="https://walmart.com/ip/xm5a"),
    RawListing("amazon", "Apple 2024 MacBook Air 13-inch M3 16GB Memory 512GB SSD - Midnight", 1399.0, link="https://amazon.com/dp/xm5b", identifiers={"asin": "A1002"}),
    RawListing("newegg", "Apple MacBook Air M3 16GB/512GB 13.6-inch Midnight (2024)", 1369.0, link="https://newegg.com/xm5b", identifiers={"asin": "A1002"}),
    RawListing("amazon", "Apple 2023 MacBook Pro 14-inch M3 Pro chip 18GB 512GB SSD - Silver", 1999.0, link="https://amazon.com/dp/xm5c", identifiers={"asin": "A1003"}),
    RawListing("bestbuy", 'MacBook Pro 14" M3 Pro 18GB/512GB Silver (2023)', 1949.0, link="https://bestbuy.com/xm5c", identifiers={"asin": "A1003"}),
    RawListing("amazon", "Apple 2022 MacBook Air M2 chip 8GB 256GB SSD - Starlight", 949.0, link="https://amazon.com/dp/xm2a", identifiers={"asin": "A1004"}),
    RawListing("walmart", 'Apple MacBook Air 13" M2 8GB/256GB Starlight', 929.0, link="https://walmart.com/ip/xm2a"),
    RawListing("bestbuy", "Apple 2022 MacBook Air M2 8GB 256GB SSD - Midnight", 899.0, link="https://bestbuy.com/xm2b"),
    RawListing("amazon", "Apple iPhone 15 128GB Black - Unlocked", 799.0, link="https://amazon.com/dp/ip15a", identifiers={"asin": "A2001"}),
    RawListing("bestbuy", "Apple iPhone 15 128GB Black (Unlocked)", 789.0, link="https://bestbuy.com/ip15a", identifiers={"asin": "A2001"}),
    RawListing("amazon", "Apple iPhone 15 256GB Blue - Unlocked", 899.0, link="https://amazon.com/dp/ip15b"),
    RawListing("amazon", "Samsung Galaxy S24 Ultra 256GB Titanium Gray", 1199.0, link="https://amazon.com/dp/s24a", identifiers={"asin": "A3001"}),
    RawListing("bestbuy", "Samsung Galaxy S24 Ultra 12GB RAM 256GB Titanium Gray", 1179.0, link="https://bestbuy.com/s24a", identifiers={"asin": "A3001"}),
    RawListing("amazon", "Apple MacBook Air M3 13-inch Clear Case Cover", 19.0, link="https://amazon.com/dp/case1"),
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search(query: str) -> list[RawListing]:
    q = _tokens(query)
    if not q:
        return []
    scored: list[tuple[int, RawListing]] = []
    for item in CATALOG:
        item_tokens = _tokens(item.title)
        if q <= item_tokens:
            scored.append((len(q & item_tokens), item))
    scored.sort(key=lambda x: (-x[0], x[1].price))
    return [item for _, item in scored]
