"""Read-side analytics over the append-only price history.

Every function here is pure: it takes `PriceRecord`s and returns values. Nothing
mutates or rewrites history — a price is only ever added, so "current price" is
always "the newest successful observation", never an overwritten cell.

Three numbers come out of a product's history, and they answer different questions:

* **best price** — cheapest place to buy *right now*: the minimum over each
  site's own latest successful observation. A site that hasn't been scraped
  since last week still contributes its last known price; a site whose latest
  scrape failed falls back to its most recent successful one.
* **lowest price** — the all-time floor across every site and every point in
  time. Used as "this has been as low as $X", never as a buy link.
* **drops** — computed per site, each site compared only against its own
  recent history, so a sale at one retailer never masks or manufactures a drop
  at another.
"""

from .config import Settings
from .types import PriceDrop, PriceHistory, PriceRecord, SiteSeries


def _sort_key(record: PriceRecord) -> str:
    return record.recorded_at


def successful(records: list[PriceRecord]) -> list[PriceRecord]:
    return [r for r in records if r.scrape_success and r.price is not None]


def group_by_site(records: list[PriceRecord]) -> dict[str, list[PriceRecord]]:
    """Split history per site, each series oldest → newest.

    The sort is stable, so records written in the same scrape round keep their
    insertion order rather than being shuffled by an equal timestamp.
    """
    by_site: dict[str, list[PriceRecord]] = {}
    for record in sorted(records, key=_sort_key):
        by_site.setdefault(record.site, []).append(record)
    return by_site


def latest_successful(site_records: list[PriceRecord]) -> PriceRecord | None:
    """The newest observation for a site that actually returned a price."""
    for record in reversed(site_records):
        if record.scrape_success and record.price is not None:
            return record
    return None


def current_best(records: list[PriceRecord]) -> tuple[float | None, str | None]:
    """Cheapest site right now — min over each site's latest successful price."""
    candidates = [
        (latest.price, site)
        for site, site_records in group_by_site(records).items()
        if (latest := latest_successful(site_records)) is not None
    ]
    if not candidates:
        return None, None
    price, site = min(candidates, key=lambda pair: pair[0])
    return price, site


def all_time_low(records: list[PriceRecord]) -> tuple[float | None, str | None, str | None]:
    """The lowest price ever observed, across all sites and all time."""
    ok = successful(records)
    if not ok:
        return None, None, None
    # Ties go to the earliest observation — the floor was first reached then.
    best = min(sorted(ok, key=_sort_key), key=lambda r: r.price)
    return best.price, best.site, best.recorded_at


def rolling_baseline(site_records: list[PriceRecord], settings: Settings) -> float | None:
    """Average of the prices a site reported *before* its latest one.

    Averages up to `drop_window` prior observations and needs at least
    `drop_min_history` of them, so a single fluke reading can neither set the
    baseline nor be mistaken for a trend.
    """
    ok = successful(site_records)
    prior = ok[:-1][-settings.drop_window :]
    if len(prior) < settings.drop_min_history:
        return None
    return sum(r.price for r in prior) / len(prior)


def detect_drop(site_records: list[PriceRecord], settings: Settings) -> PriceDrop | None:
    """Flag a drop on one site, using only that site's own history.

    Both gates must be met: the fall from the rolling baseline is at least
    `drop_percent_threshold` percent *and* at least `drop_absolute_threshold`
    in absolute currency. Noisy dips clear one gate but not both.
    """
    latest = latest_successful(site_records)
    baseline = rolling_baseline(site_records, settings)
    if latest is None or baseline is None or baseline <= 0:
        return None

    absolute = baseline - latest.price
    if absolute <= 0:
        return None
    percent = absolute / baseline * 100.0
    if percent < settings.drop_percent_threshold or absolute < settings.drop_absolute_threshold:
        return None

    return PriceDrop(
        site=latest.site,
        current_price=latest.price,
        baseline_average=round(baseline, 2),
        percent=round(percent, 2),
        absolute=round(absolute, 2),
        recorded_at=latest.recorded_at,
    )


def build_history(product_id: int, records: list[PriceRecord], settings: Settings) -> PriceHistory:
    """Assemble everything the UI needs from one product's raw history."""
    ordered = sorted(records, key=_sort_key)
    by_site = group_by_site(ordered)

    series: list[SiteSeries] = []
    drops: list[PriceDrop] = []
    for site in sorted(by_site):
        site_records = by_site[site]
        latest = latest_successful(site_records)
        drop = detect_drop(site_records, settings)
        baseline = rolling_baseline(site_records, settings)
        if drop is not None:
            drops.append(drop)
        series.append(
            SiteSeries(
                site=site,
                points=site_records,
                latest_price=latest.price if latest else None,
                latest_at=latest.recorded_at if latest else None,
                baseline_average=round(baseline, 2) if baseline is not None else None,
                drop=drop,
            )
        )

    best_price, best_site = current_best(ordered)
    lowest_price, lowest_site, lowest_at = all_time_low(ordered)
    currency = next((r.currency for r in ordered if r.currency), "USD")

    return PriceHistory(
        product_id=product_id,
        currency=currency,
        sites=series,
        best_price=best_price,
        best_site=best_site,
        lowest_price=lowest_price,
        lowest_site=lowest_site,
        lowest_at=lowest_at,
        drops=sorted(drops, key=lambda d: -d.percent),
        records=ordered,
    )
