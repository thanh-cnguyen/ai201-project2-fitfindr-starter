"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    Notes:
        Relevance is based on keyword overlap between the query and the listing's
        title, description, category, and style tags.
    """
    listings = load_listings()

    query_tokens = set(re.findall(r"[a-z0-9]+", (description or "").lower()))
    normalized_size = size.strip().lower() if isinstance(size, str) else None

    results: list[dict] = []

    for listing in listings:
        # Apply optional inclusive max price filter.
        if max_price is not None and float(listing.get("price", 0)) > max_price:
            continue

        # Apply optional case-insensitive size substring filter.
        listing_size = str(listing.get("size", "")).lower()
        if normalized_size and normalized_size not in listing_size:
            continue

        searchable_text = " ".join(
            [
                str(listing.get("title", "")),
                str(listing.get("description", "")),
                str(listing.get("category", "")),
                " ".join(str(tag) for tag in listing.get("style_tags", [])),
            ]
        ).lower()
        listing_tokens = set(re.findall(r"[a-z0-9]+", searchable_text))

        score = float(len(query_tokens & listing_tokens))
        if score < 1:
            continue

        listing_with_score = dict(listing)
        listing_with_score["score"] = score
        results.append(listing_with_score)

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    Notes:
        If matching wardrobe pieces exist, the function asks the LLM to create
        outfit ideas using those pieces. If no usable wardrobe pieces exist, it asks
        for general styling advice based on the new item alone.
    """

    title = new_item.get("title", "the item")
    category = new_item.get("category", "")
    colors = ", ".join(new_item.get("colors") or []) or "unknown color"
    style_tags = ", ".join(new_item.get("style_tags") or []) or "no specific style"
    description = new_item.get("description", "")

    # Determine which wardrobe categories complement this item's category.
    complement_map: dict[str, list[str]] = {
        "top": ["bottoms", "shoes", "outerwear", "accessories"],
        "tops": ["bottoms", "shoes", "outerwear", "accessories"],
        "bottom": ["tops", "shoes", "outerwear", "accessories"],
        "bottoms": ["tops", "shoes", "outerwear", "accessories"],
        "shoe": ["tops", "bottoms"],
        "shoes": ["tops", "bottoms"],
        "outerwear": ["tops", "bottoms", "shoes"],
        "accessory": ["tops", "bottoms", "outerwear", "shoes"],
        "accessories": ["tops", "bottoms", "outerwear", "shoes"],
    }
    complement_categories = complement_map.get(category.lower(), [])

    wardrobe_items = wardrobe.get("items", []) or []

    # Filter wardrobe to complementary categories only.
    complementary = [
        item for item in wardrobe_items
        if item.get("category", "").lower() in complement_categories
    ]

    if not complementary:
        # Empty wardrobe path: general styling advice only.
        prompt = (
            f"You are a thrift-store fashion stylist.\n\n"
            f"A user is considering buying this thrifted item:\n"
            f"- Title: {title}\n"
            f"- Category: {category}\n"
            f"- Colors: {colors}\n"
            f"- Style: {style_tags}\n"
            f"- Description: {description}\n\n"
            f"Their wardrobe is empty. Give them 1–2 specific outfit ideas for this item using "
            f"common wardrobe basics (e.g., white tee, black jeans, white sneakers). "
            f"Be concrete and mention specific clothing types. Keep it to 3–5 sentences total. "
            f"End with a brief tip about adding wardrobe items for more personalized suggestions."
        )
        fallback = (
            f"Style {title} with simple basics that match its {colors} color palette "
            f"and {style_tags} vibe. Since your wardrobe is empty, try adding a few "
            f"tops, bottoms, shoes, and layering pieces for more personalized suggestions."
        )
    else:
        # Format complementary wardrobe items for the prompt.
        wardrobe_lines = "\n".join(
            f"- {item.get('name', 'unnamed')} "
            f"({item.get('category', '?')}, "
            f"{', '.join(item.get('colors') or [])})"
            + (f" — {item.get('notes')}" if item.get('notes') else "")
            for item in complementary
        )
        prompt = (
            f"You are a thrift-store fashion stylist.\n\n"
            f"A user is considering buying this thrifted item:\n"
            f"- Title: {title}\n"
            f"- Category: {category}\n"
            f"- Colors: {colors}\n"
            f"- Style: {style_tags}\n"
            f"- Description: {description}\n\n"
            f"They already own these complementary pieces:\n{wardrobe_lines}\n\n"
            f"Suggest 1–2 complete outfits that pair the new item with specific pieces from "
            f"the list above. Use the exact names of the wardrobe items. Be specific about "
            f"styling choices (tucked/untucked, layering, etc.). Keep it to 4–6 sentences."
        )
        fallback = (
            f"Style {title} with simple basics that match its {colors} color palette "
            f"and {style_tags} vibe. Try pairing it with balanced wardrobe staples like "
            f"clean shoes, simple bottoms, and a layering piece for a complete outfit."
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )

        content = response.choices[0].message.content
        if content:
            return content.strip()
    except Exception:
        pass

    return fallback


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    Notes:
        The function first validates that an outfit description exists. If the
        outfit is missing or blank, it returns a clear error message instead of
        calling the LLM. For valid input, it asks the LLM to create a short
        shareable caption and falls back to a deterministic caption if the LLM
        call fails or returns empty content.
    """
    if not isinstance(outfit, str) or not outfit.strip():
        return (
            "Cannot create a fit card: missing outfit description. "
            "Please provide a short outfit idea to generate a shareable caption."
        )

    title = new_item.get("title", "this thrifted piece")
    description = new_item.get("description", "")
    colors = ", ".join(new_item.get("colors") or []) or "mixed tones"
    style_tags = ", ".join(new_item.get("style_tags") or []) or "everyday style"
    price = new_item.get("price")
    platform = str(new_item.get("platform") or "a resale app")

    if isinstance(price, (int, float)):
        price_text = f"${float(price):.2f}"
    else:
        price_text = "a great price"

    prompt = (
        "You are writing a short social media fit card caption.\n\n"
        "Use these details:\n"
        f"- Item title: {title}\n"
        f"- Price: {price_text}\n"
        f"- Platform: {platform}\n"
        f"- Colors: {colors}\n"
        f"- Style tags: {style_tags}\n"
        f"- Item description: {description}\n"
        f"- Outfit idea: {outfit.strip()}\n\n"
        "Write exactly 2 to 4 sentences in a casual, authentic OOTD tone. "
        "Naturally mention the thrifted item, include the outfit idea, and mention "
        "the price and platform once each. Avoid hashtags and emojis."
    )

    fallback = (
        f"Just thrifted {title} for {price_text} on {platform} and built a look around it: "
        f"{outfit.strip()} "
        f"The {colors} palette and {style_tags} vibe make it feel easy but styled."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=220,
        )
        content = response.choices[0].message.content
        if isinstance(content, str) and content.strip():
            return content.strip()
    except Exception:
        pass

    return fallback
