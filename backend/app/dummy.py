"""A stand-in for the scrapers, and nothing more.

Every entry is exactly what a scraper would hand back — the shop's own title
string, a price and whatever identifier the page exposed. No attributes are
recorded here: they are read out of the title by the LLM in `llm.py`, the same
call a real scrape would make, so swapping this module for real scraping
changes nothing downstream.
"""

import hashlib
import re
from collections import Counter
from math import log

from .types import Quote, RawListing

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

    RawListing("nike", "Nike Pegasus 41 Men's Running Shoes Black White Size 10", 139.99, link="https://nike.com/peg41-bw-10", identifiers={"sku": "NK-P41-BW-10"}),
    RawListing("footlocker", "Nike Air Zoom Pegasus 41 Mens Running Shoes Black/White 10", 134.99, link="https://footlocker.com/nk-p41-10", identifiers={"sku": "NK-P41-BW-10"}),
    RawListing("amazon", "Nike Pegasus 41 Mens Running Shoes Size 10 Black/White", 144.95, link="https://amazon.com/dp/peg41-10"),
    RawListing("nike", "Nike Pegasus 41 Women's Running Shoes Blue Size 8", 139.99, link="https://nike.com/peg41-blue-8", identifiers={"sku": "NK-P41-BL-8"}),
    RawListing("amazon", "Nike Pegasus 41 Womens Running Shoes Size 8 Blue", 137.50, link="https://amazon.com/dp/peg41-w-8"),

    RawListing("bestbuy", "LG C4 65\" Class OLED evo 4K Smart TV (2024)", 1999.99, link="https://bestbuy.com/lg-c4-65", identifiers={"sku": "LG-C4-65"}),
    RawListing("amazon", "LG 65 inch C4 OLED evo 4K Smart TV 2024 Model", 1949.00, link="https://amazon.com/dp/lg-c4-65", identifiers={"asin": "LG-C4-65"}),
    RawListing("walmart", "LG C4 65\" 4K OLED TV 2024", 1929.00, link="https://walmart.com/ip/lg-c4-65"),
    RawListing("bestbuy", "LG C4 77\" Class OLED evo 4K Smart TV (2024)", 3299.99, link="https://bestbuy.com/lg-c4-77", identifiers={"sku": "LG-C4-77"}),
    RawListing("amazon", "Samsung 65\" S95D OLED 4K Smart TV 2024", 2599.99, link="https://amazon.com/dp/s95d-65", identifiers={"asin": "SAM-S95D-65"}),

    RawListing("ikea", "Kallax Shelf Unit White 77x35 cm", 69.99, link="https://ikea.com/kallax-white", identifiers={"sku": "KALLAX-WHT"}),
    RawListing("ikea", "Kallax Shelf Unit Black 77x35 cm", 69.99, link="https://ikea.com/kallax-black", identifiers={"sku": "KALLAX-BLK"}),
    RawListing("wayfair", "Kallax 5-Cube Shelf White 30.5\"", 74.99, link="https://wayfair.com/kallax-5-white"),
    RawListing("ikea", "Kallax Shelf Unit White 147x35 cm", 129.99, link="https://ikea.com/kallax-white-tall", identifiers={"sku": "KALLAX-WHT-TALL"}),

    RawListing("amazon", "Instant Pot Duo 7-in-1 Electric Pressure Cooker 6 Quart", 89.99, link="https://amazon.com/dp/ip-duo-6", identifiers={"asin": "IP-DUO-6"}),
    RawListing("walmart", "Instant Pot Duo 6 Qt 7-in-1 Pressure Cooker", 84.99, link="https://walmart.com/ip/ip-duo-6"),
    RawListing("target", "Instant Pot Duo 7-in-1 6 Quart Pressure Cooker", 94.99, link="https://target.com/ip-duo-6"),
    RawListing("amazon", "Instant Pot Duo 8 Quart 7-in-1 Pressure Cooker", 109.99, link="https://amazon.com/dp/ip-duo-8", identifiers={"asin": "IP-DUO-8"}),

    RawListing("amazon", "Dyson V15 Detect Cordless Vacuum Yellow", 749.99, link="https://amazon.com/dp/dyson-v15", identifiers={"asin": "DYS-V15"}),
    RawListing("bestbuy", "Dyson V15 Detect Cordless Stick Vacuum", 729.99, link="https://bestbuy.com/dyson-v15", identifiers={"sku": "DYS-V15"}),
    RawListing("amazon", "Dyson V12 Detect Slim Cordless Vacuum", 599.99, link="https://amazon.com/dp/dyson-v12", identifiers={"asin": "DYS-V12"}),

    RawListing("home depot", "Milwaukee M18 Fuel 1/2\" Impact Wrench Kit", 349.00, link="https://homedepot.com/m18-fuel-iw", identifiers={"sku": "MIL-M18-IW"}),
    RawListing("lowes", "Milwaukee M18 Fuel 1/2 in Impact Wrench Kit", 339.00, link="https://lowes.com/m18-fuel-iw"),
    RawListing("amazon", "Milwaukee M18 Fuel Impact Wrench 1/2\" Kit", 359.00, link="https://amazon.com/dp/m18-fuel-iw", identifiers={"asin": "MIL-M18-IW"}),

    RawListing("amazon", "Cuisinart 14-Cup Food Processor Stainless Steel", 199.95, link="https://amazon.com/dp/cuisinart-fp14", identifiers={"asin": "CUI-FP14"}),
    RawListing("williams sonoma", "Cuisinart 14 Cup Food Processor", 219.95, link="https://williams-sonoma.com/cuisinart-fp14"),
    RawListing("amazon", "Cuisinart 11-Cup Food Processor", 159.95, link="https://amazon.com/dp/cuisinart-fp11", identifiers={"asin": "CUI-FP11"}),

    RawListing("amazon", "Weber Genesis E-325s 3-Burner Gas Grill Black", 899.00, link="https://amazon.com/dp/weber-genesis-325", identifiers={"asin": "WEB-GEN-325"}),
    RawListing("home depot", "Weber Genesis E-325S 3 Burner Liquid Propane Grill", 879.00, link="https://homedepot.com/weber-genesis-325"),
    RawListing("amazon", "Weber Spirit II E-310 3-Burner Gas Grill", 599.00, link="https://amazon.com/dp/weber-spirit-310", identifiers={"asin": "WEB-SPI-310"}),

    RawListing("amazon", "Herman Miller Aeron Ergonomic Chair Size B Graphite", 1195.00, link="https://amazon.com/dp/aeron-b", identifiers={"asin": "HER-AERON-B"}),
    RawListing("herman miller", "Aeron Chair Size B Graphite Standard", 1150.00, link="https://hermanmiller.com/aeron-b"),
    RawListing("amazon", "Herman Miller Aeron Ergonomic Chair Size C Graphite", 1295.00, link="https://amazon.com/dp/aeron-c", identifiers={"asin": "HER-AERON-C"}),

    RawListing("amazon", "Spigen Ultra Hybrid Case for iPhone 15 Matte Black", 19.99, link="https://amazon.com/dp/spigen-iph15", identifiers={"asin": "SPG-IP15-MB"}),
    RawListing("bestbuy", "Spigen Ultra Hybrid iPhone 15 Case Matte Black", 21.99, link="https://bestbuy.com/spigen-iph15", identifiers={"sku": "SPG-IP15-MB"}),
    RawListing("amazon", "Spigen Ultra Hybrid Case for iPhone 15 Pro Clear", 19.99, link="https://amazon.com/dp/spigen-iph15p", identifiers={"asin": "SPG-IP15P-CL"}),
]

STOPWORDS = {"the", "a", "an", "with", "and", "for", "of", "in", "on", "at", "to", "by"}

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS}

_DOC_COUNT = len(CATALOG)
_DF: Counter = Counter()
for _item in CATALOG:
    _DF.update(_tokens(_item.title))

def _idf(token: str) -> float:
    df = _DF.get(token, 0)
    if df == 0:
        return 0.0
    return log((_DOC_COUNT + 1) / df) + 1.0

def _score(q_tokens: set[str], item_tokens: set[str]) -> float:
    return sum(_idf(t) for t in (q_tokens & item_tokens))

def search(query: str) -> list[RawListing]:
    q_tokens = _tokens(query)
    if not q_tokens:
        return []
    scored: list[tuple[float, RawListing]] = []
    for item in CATALOG:
        score = _score(q_tokens, _tokens(item.title))
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].price))
    return [item for _, item in scored]

_BY_LINK = {item.link: item for item in CATALOG if item.link}

def quote(site: str, link: str, last_price: float | None, round_index: int) -> Quote:
    digest = int(hashlib.sha256(f"{site}|{link}|{round_index}".encode()).hexdigest()[:12], 16)
    if digest % 17 == 0:
        return Quote(site=site, price=None, link=link, scrape_success=False)

    anchor = _BY_LINK[link].price if link in _BY_LINK else last_price
    if anchor is None:
        return Quote(site=site, price=None, link=link, scrape_success=False)

    percent = ((digest >> 16) % 1801) / 100.0 - 12.0
    return Quote(site=site, price=round(anchor * (1 + percent / 100.0), 2), link=link)
