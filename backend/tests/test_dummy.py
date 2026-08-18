from app import dummy


def test_ranked_search_puts_rare_matches_first():
    results = dummy.search("macbook m3")
    titles = [r.title.lower() for r in results]
    assert results
    m3_idx = next(i for i, t in enumerate(titles) if "m3" in t)
    m2_idx = next(i for i, t in enumerate(titles) if "m2" in t)
    assert m3_idx < m2_idx


def test_partial_match_included():
    results = dummy.search("macbook")
    assert results
    assert any("m2" in r.title.lower() for r in results)
    assert any("m3" in r.title.lower() for r in results)


def test_single_token_filters_to_brand():
    results = dummy.search("iphone")
    assert results
    assert all("iphone" in r.title.lower() for r in results)


def test_no_results():
    assert dummy.search("zzzz") == []


def test_stopwords_ignored():
    results = dummy.search("the macbook")
    assert results
    assert all("macbook" in r.title.lower() for r in results)
