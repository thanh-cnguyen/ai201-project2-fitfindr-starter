"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from re import search, sub, IGNORECASE
from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    Notes:
        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].
    """
    session = _new_session(query, wardrobe)

    raw_query = (query or "").strip()
    normalized_query = raw_query.lower()

    max_price = None
    price_match = None
    for pattern in (
        r"(?:under|below|less than|at most|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)",
        r"\$\s*(\d+(?:\.\d+)?)",
    ):
        price_match = search(pattern, normalized_query)
        if price_match:
            max_price = float(price_match.group(1))
            break

    size = None
    size_match = search(
        r"\b(?:size|sz)\s*[:=]?\s*([a-z0-9/\-]+(?:\s+[a-z0-9/\-]+)*)",
        normalized_query,
    )
    if size_match:
        size = size_match.group(1).strip().upper()
    else:
        waist_match = search(r"\b(w\d+(?:\s*l\d+)?)\b", normalized_query)
        if waist_match:
            size = waist_match.group(1).strip().upper()

    description = raw_query
    if max_price is not None:
        description = sub(
            r"(?:under|below|less than|at most|max(?:imum)?)\s*\$?\s*\d+(?:\.\d+)?",
            "",
            description,
            flags=IGNORECASE,
        )
        description = sub(
            r"\$\s*\d+(?:\.\d+)?",
            "",
            description,
        )
    if size is not None:
        description = sub(
            r"(?:size|sz)\s*[:=]??\s*[a-z0-9/\-]+(?:\s+[a-z0-9/\-]+)*",
            "",
            description,
            flags=IGNORECASE,
        )
        description = sub(
            r"\bw\d+(?:\s*l\d+)?\b",
            "",
            description,
            flags=IGNORECASE,
        )

    description = sub(r"[,$;:\-]+", " ", description)
    description = sub(r"\s+", " ", description).strip()
    if not description:
        description = raw_query

    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price,
    }

    results = search_listings(description, size, max_price)
    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings matched your query. Try using broader keywords, removing the size filter, "
            "or increasing the maximum price."
        )
        return session

    session["selected_item"] = results[0]
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"])
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        selected_item = session["selected_item"]
        if selected_item:
            print(f"Found: {selected_item['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Fit card: {session2['fit_card']}")
    print(f"Error message: {session2['error']}")
