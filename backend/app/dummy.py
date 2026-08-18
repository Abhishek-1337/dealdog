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
    """Simulate re-scraping one site's listing for round `round_index`.

    Stands in for a real scraper until `dummy.py` is replaced. The result is a
    pure function of (site, link, round) — the same round always yields the same
    quote, so history built this way is reproducible and testable. Roughly one
    scrape in seventeen "fails", which exercises the failure-recording path.
    """
    digest = int(hashlib.sha256(f"{site}|{link}|{round_index}".encode()).hexdigest()[:12], 16)
    if digest % 17 == 0:
        return Quote(site=site, price=None, link=link, scrape_success=False)

    anchor = _BY_LINK[link].price if link in _BY_LINK else last_price
    if anchor is None:
        return Quote(site=site, price=None, link=link, scrape_success=False)

    # Wander within -12%..+6% of the catalog anchor, biased low so drops happen.
    percent = ((digest >> 16) % 1801) / 100.0 - 12.0
    return Quote(site=site, price=round(anchor * (1 + percent / 100.0), 2), link=link)
