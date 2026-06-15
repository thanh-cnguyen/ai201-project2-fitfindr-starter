from tools import search_listings, suggest_outfit

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

# Additional tests for suggest_outfit() are in test_tools.py, since it depends on search_listings() and the listings data.
def test_suggest_outfit_with_wardrobe():
    new_item = {
        "title": "Vintage Band Tee — Faded Grey",
        "description": "Faded grey band-style tee with distressed graphic.",
        "category": "tops",
        "style_tags": ["vintage", "grunge", "streetwear"],
        "size": "L",
        "condition": "fair",
        "price": 19.00,
        "colors": ["grey", "charcoal"],
        "brand": None,
        "platform": "depop",
    }
    wardrobe = {
        "items": [
            {
                "id": "1",
                "name": "Baggy Jeans",
                "category": "bottoms",
                "colors": ["blue"],
                "style_tags": ["casual", "streetwear"],
                "notes": "",
            },
            {
                "id": "2",
                "name": "Chunky Sneakers",
                "category": "shoes",
                "colors": ["white"],
                "style_tags": ["casual", "streetwear"],
                "notes": "",
            },
        ]
    }

    result = suggest_outfit(new_item, wardrobe)

    assert isinstance(result, str)
    assert result.strip()
    assert "Vintage Band Tee" in result or "vintage band tee" in result.lower() or "faded grey band-style tee" in result.lower()
    assert "Baggy Jeans" in result or "baggy jeans" in result.lower()


def test_suggest_outfit_empty_wardrobe():
    new_item = {
        "title": "Black Combat Boots",
        "description": "Chunky black lace-up boots.",
        "category": "shoes",
        "style_tags": ["grunge", "streetwear"],
        "size": "8",
        "condition": "good",
        "price": 35.00,
        "colors": ["black"],
        "brand": None,
        "platform": "poshmark",
    }

    result = suggest_outfit(new_item, {"items": []})

    assert isinstance(result, str)
    assert result.strip()
    assert "Black Combat Boots" in result or "combat boots" in result.lower() or "black lace-up boots" in result.lower()
