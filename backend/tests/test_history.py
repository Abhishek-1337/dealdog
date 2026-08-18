from datetime import datetime, timedelta, timezone

from app import history
from app.types import PriceRecord, Quote

BASE = datetime(2026, 8, 1, tzinfo=timezone.utc)


def rec(site: str, price, day: int, success: bool = True):
    """One observation `day` days after BASE. price=None means a failed scrape."""
    return PriceRecord(
        site=site,
        price=price,
        currency="USD",
        link=f"https://{site}.example/item",
        recorded_at=(BASE + timedelta(days=day)).isoformat(),
        scrape_success=success,
    )


def series(site: str, prices, start: int = 0):
    return [rec(site, price, start + i) for i, price in enumerate(prices)]


# ---------- append-only ----------


def test_repeated_scrapes_append_instead_of_overwriting(repo):
    product = repo.create_product("MacBook Air M3", {}, [], [0.0])
    for price in (1099.0, 1049.0, 999.0):
        repo.add_price_points(product.id, [Quote(site="amazon", price=price)])

    stored = repo.get_price_history(product.id)
    assert [r.price for r in stored] == [1099.0, 1049.0, 999.0]


def test_failed_scrape_is_recorded_but_ignored_by_analytics(repo, settings):
    product = repo.create_product("MacBook Air M3", {}, [], [0.0])
    repo.add_price_points(product.id, [Quote(site="amazon", price=1099.0)])
    repo.add_price_points(product.id, [Quote(site="amazon", price=None, scrape_success=False)])

    stored = repo.get_price_history(product.id)
    assert len(stored) == 2, "the failed scrape is part of the audit trail"
    assert stored[1].scrape_success is False

    result = history.build_history(product.id, stored, settings)
    assert result.best_price == 1099.0, "falls back to the last successful price"
    assert result.sites[0].latest_price == 1099.0


def test_failed_scrape_does_not_become_a_zero_low(settings):
    records = series("amazon", [1099.0, 1049.0]) + [rec("amazon", None, 2, success=False)]
    result = history.build_history(1, records, settings)
    assert result.lowest_price == 1049.0


# ---------- best vs lowest ----------


def test_best_price_is_cheapest_latest_not_cheapest_ever(settings):
    # walmart was once the cheapest thing on record, but has since gone up.
    records = series("amazon", [1099.0, 1020.0]) + series("walmart", [899.0, 1080.0])
    result = history.build_history(1, records, settings)

    assert result.best_price == 1020.0
    assert result.best_site == "amazon"
    assert result.lowest_price == 899.0
    assert result.lowest_site == "walmart"


def test_best_price_uses_each_sites_own_latest_even_at_different_times(settings):
    # bestbuy stopped being scraped on day 1; its last known price still counts.
    records = series("amazon", [1099.0, 1080.0, 1075.0]) + series("bestbuy", [1000.0], start=1)
    result = history.build_history(1, records, settings)

    assert (result.best_price, result.best_site) == (1000.0, "bestbuy")


def test_empty_history_yields_no_prices(settings):
    result = history.build_history(1, [], settings)
    assert result.best_price is None
    assert result.lowest_price is None
    assert result.sites == []
    assert result.drops == []


# ---------- drop detection ----------


def test_real_drop_is_flagged(settings):
    # baseline = mean(1000, 1000, 1000) = 1000; latest 850 is -15% and -$150.
    records = series("amazon", [1000.0, 1000.0, 1000.0, 850.0])
    result = history.build_history(1, records, settings)

    assert len(result.drops) == 1
    drop = result.drops[0]
    assert drop.site == "amazon"
    assert drop.baseline_average == 1000.0
    assert drop.current_price == 850.0
    assert drop.percent == 15.0
    assert drop.absolute == 150.0


def test_noisy_dip_below_percent_threshold_is_not_a_drop(settings):
    # -$40 clears the $5 gate but -4% misses the 10% gate.
    records = series("amazon", [1000.0, 1000.0, 1000.0, 960.0])
    assert history.build_history(1, records, settings).drops == []


def test_noisy_dip_below_absolute_threshold_is_not_a_drop(settings):
    # -20% clears the percent gate, but -$4 misses the $5 gate on a cheap item.
    records = series("cheapo", [20.0, 20.0, 20.0, 16.0])
    assert history.build_history(1, records, settings).drops == []


def test_price_rise_is_not_a_drop(settings):
    records = series("amazon", [900.0, 900.0, 900.0, 1100.0])
    assert history.build_history(1, records, settings).drops == []


def test_drop_needs_enough_prior_history(settings):
    # One prior observation is not a baseline, however large the fall.
    records = series("amazon", [1000.0, 500.0])
    result = history.build_history(1, records, settings)
    assert result.drops == []
    assert result.sites[0].baseline_average is None


def test_baseline_only_averages_the_recent_window(settings):
    # An ancient $2000 price must not inflate the baseline: the window is the
    # last 3 prior prices (1000, 1000, 1000), so 850 is a 15% drop, not 43%.
    records = series("amazon", [2000.0, 1000.0, 1000.0, 1000.0, 850.0])
    drop = history.build_history(1, records, settings).drops[0]
    assert drop.baseline_average == 1000.0
    assert drop.percent == 15.0


def test_drop_measured_against_a_falling_baseline(settings):
    # A steady slide is averaged, so the flag reflects the fall from trend.
    records = series("amazon", [1000.0, 950.0, 900.0, 750.0])
    drop = history.build_history(1, records, settings).drops[0]
    assert drop.baseline_average == 950.0
    assert drop.absolute == 200.0


# ---------- per-site independence ----------


def test_one_sites_drop_does_not_flag_another(settings):
    records = series("amazon", [1000.0, 1000.0, 1000.0, 850.0]) + series(
        "bestbuy", [990.0, 990.0, 990.0, 985.0]
    )
    result = history.build_history(1, records, settings)

    assert [d.site for d in result.drops] == ["amazon"]
    by_site = {s.site: s for s in result.sites}
    assert by_site["amazon"].drop is not None
    assert by_site["bestbuy"].drop is None


def test_a_cheap_rival_does_not_suppress_a_drop(settings):
    # walmart is cheaper in absolute terms, but amazon's own fall still counts.
    records = series("amazon", [1000.0, 1000.0, 1000.0, 850.0]) + series(
        "walmart", [700.0, 700.0, 700.0, 700.0]
    )
    result = history.build_history(1, records, settings)

    assert [d.site for d in result.drops] == ["amazon"]
    assert result.best_site == "walmart"


def test_baselines_are_computed_per_site(settings):
    records = series("amazon", [1000.0, 1000.0, 1000.0]) + series("bestbuy", [500.0, 500.0, 500.0])
    result = history.build_history(1, records, settings)
    by_site = {s.site: s.baseline_average for s in result.sites}
    assert by_site == {"amazon": 1000.0, "bestbuy": 500.0}


def test_each_site_keeps_its_own_series(settings):
    records = series("amazon", [1000.0, 900.0]) + series("bestbuy", [990.0, 980.0, 970.0])
    result = history.build_history(1, records, settings)
    points = {s.site: [p.price for p in s.points] for s in result.sites}
    assert points == {"amazon": [1000.0, 900.0], "bestbuy": [990.0, 980.0, 970.0]}


def test_thresholds_are_configurable(settings):
    records = series("amazon", [1000.0, 1000.0, 1000.0, 960.0])
    assert history.build_history(1, records, settings).drops == []

    settings.drop_percent_threshold = 2.0
    assert len(history.build_history(1, records, settings).drops) == 1
