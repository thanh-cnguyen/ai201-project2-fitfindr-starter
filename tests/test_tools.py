from tools import search_listings

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert not results

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=45)
    assert len(results) > 0
    assert all(item["price"] <= 45 for item in results)

def test_search_size_filter():
    results = search_listings("graphic tee", size="M", max_price=25)
    assert len(results) > 0
    assert all("m" in item["size"].lower() for item in results)

def test_search_results_include_score_and_sorted():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert all("score" in item for item in results)
    assert results == sorted(results, key=lambda item: item["score"], reverse=True)
