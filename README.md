# FitFindr

FitFindr is a multi-tool AI agent that helps users find secondhand clothing pieces and figure out how to style them. The agent takes a natural language request, searches a mock secondhand listings dataset, selects the most relevant item, suggests an outfit using the user's wardrobe, and generates a short shareable fit card.

---

## Project Structure

```text
ai201-project2-fitfindr-starter/
├── app.py                    # Gradio app interface
├── agent.py                  # Planning loop and session state
├── tools.py                  # Three required tool functions
├── data/
│   ├── listings.json          # Mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe schema and examples
├── tests/
│   └── test_tools.py          # Tests for tools and failure modes
├── utils/
│   └── data_loader.py         # Data loading helpers
├── planning.md                # Agent planning/spec document
├── requirements.txt
└── README.md
```

---

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root and add your Groq API key:

```text
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Then open the local Gradio URL shown in the terminal.

Run tests:

```bash
pytest tests/
```

---

## Tool Inventory

### `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

Searches the mock secondhand listings dataset for items that match the user's request.

Inputs:

* `description` (`str`): Search keywords, such as `"vintage graphic tee"`.
* `size` (`str | None`): Optional size filter, such as `"M"` or `"8"`.
* `max_price` (`float | None`): Optional inclusive price ceiling.

Output:

* A list of listing dictionaries sorted by relevance.
* Each result includes listing fields such as `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`, and a generated `score`.

Failure behavior:

* If no listings match, the tool returns an empty list instead of raising an exception.

---

### `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Suggests an outfit using the selected listing and the user's wardrobe.

Inputs:

* `new_item` (`dict`): The selected listing from `search_listings`.
* `wardrobe` (`dict`): A wardrobe dictionary with an `"items"` key. The value can be an empty list.

Output:

* A non-empty outfit suggestion string.

Failure behavior:

* If the wardrobe is empty or no complementary pieces are found, the tool gives general styling advice using common basics.
* If the LLM call fails or returns empty content, the tool returns a fallback styling suggestion.

---

### `create_fit_card(outfit: str, new_item: dict) -> str`

Creates a short shareable caption for the completed outfit.

Inputs:

* `outfit` (`str`): The outfit suggestion from `suggest_outfit`.
* `new_item` (`dict`): The selected listing from `search_listings`.

Output:

* A 2–4 sentence fit card caption suitable for sharing.

Failure behavior:

* If `outfit` is empty or missing, the tool returns a clear error message instead of crashing.
* If the LLM call fails or returns empty content, the tool returns a fallback caption.

---

## Planning Loop

The agent uses a conditional planning loop in `run_agent()`.

First, the agent parses the user's natural language query using regular expressions. It extracts:

* `description`
* `size`
* `max_price`

Regex parsing was used instead of an LLM because the needed fields are predictable, such as `under $30`, `size M`, or `size 8`.

After parsing, the agent calls `search_listings()`.

If `search_listings()` returns no results, the agent stores an error message in `session["error"]` and stops early. It does not call `suggest_outfit()` or `create_fit_card()` without a selected item.

If listings are found, the agent stores the results in `session["search_results"]`, selects the top-ranked listing, and stores it in `session["selected_item"]`.

The selected item is passed into `suggest_outfit()` along with the user's wardrobe. The returned outfit idea is stored in `session["outfit_suggestion"]`.

Finally, the agent calls `create_fit_card()` using the outfit suggestion and selected item. The returned caption is stored in `session["fit_card"]`.

---

## State Management

The agent uses a session dictionary to pass information between tools.

Session keys:

```python
{
    "query": original user query,
    "parsed": parsed description, size, and max_price,
    "search_results": listings returned by search_listings,
    "selected_item": top-ranked listing,
    "wardrobe": user wardrobe,
    "outfit_suggestion": output from suggest_outfit,
    "fit_card": output from create_fit_card,
    "error": error message if the workflow stops early,
}
```

The most important state flow is:

```text
search_listings result → selected_item → suggest_outfit → outfit_suggestion → create_fit_card → fit_card
```

This allows the agent to reuse tool outputs without asking the user to re-enter information.

---

## Error Handling

| Tool              | Failure mode                                          | Agent response                                                                                                       |
| ----------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `search_listings` | No listings match the query                           | The agent stops early and tells the user to try broader keywords, remove the size filter, or increase the max price. |
| `suggest_outfit`  | Wardrobe is empty or no complementary items are found | The tool returns general styling advice using common basics.                                                         |
| `suggest_outfit`  | LLM call fails or returns empty content               | The tool returns a fallback outfit suggestion.                                                                       |
| `create_fit_card` | Outfit input is missing or blank                      | The tool returns a clear error message saying a fit card cannot be created without an outfit description.            |
| `create_fit_card` | LLM call fails or returns empty content               | The tool returns a fallback caption.                                                                                 |

---

## Complete Interaction Example

Example user query:

```text
vintage graphic tee under $30
```

Step 1: The agent parses the query.

```python
session["parsed"] = {
    "description": "vintage graphic tee",
    "size": None,
    "max_price": 30.0,
}
```

Step 2: The agent calls `search_listings()`.

Example result:

```python
session["selected_item"] = {
    "title": "Vintage Band Tee — Faded Grey",
    "category": "tops",
    "size": "L",
    "condition": "fair",
    "price": 19.00,
    "colors": ["grey", "charcoal"],
    "platform": "depop",
}
```

Step 3: The agent calls `suggest_outfit()`.

Example output:

```text
Pair the faded grey vintage band tee with baggy jeans and chunky sneakers for a casual, retro streetwear look.
```

Step 4: The agent calls `create_fit_card()`.

Example output:

```text
Found this faded grey vintage band tee for $19 on Depop, and it’s giving easy retro streetwear. Pair it with baggy jeans and chunky sneakers for a relaxed, lived-in look.
```

Final user-facing output in the app:

```text
Top listing found:
Vintage Band Tee — Faded Grey
Price: $19.00
Size: L
Condition: fair
Platform: depop
Colors: grey, charcoal

Outfit idea:
Pair the faded grey vintage band tee with baggy jeans and chunky sneakers for a casual, retro streetwear look.

Your fit card:
Found this faded grey vintage band tee for $19 on Depop, and it’s giving easy retro streetwear. Pair it with baggy jeans and chunky sneakers for a relaxed, lived-in look.
```

---

## Testing

Tests are located in:

```text
tests/test_tools.py
```

Run:

```bash
pytest tests/
```

The tests cover:

* `search_listings()` returning results
* `search_listings()` returning an empty list for no matches
* price filtering
* size filtering
* relevance scores and sorting
* `suggest_outfit()` with a populated wardrobe
* `suggest_outfit()` with an empty wardrobe
* `create_fit_card()` with a valid outfit
* `create_fit_card()` with a missing outfit

Manual failure-mode checks were also run from the terminal:

* impossible listing search: `designer ballgown`, size `XXS`, max price `$5`
* empty wardrobe outfit suggestion
* empty outfit string passed into `create_fit_card()`

---

## AI Usage Transparency

I used ChatGPT to review my `planning.md` against the rubric. I asked it to identify missing or weak sections, then I revised the planning document to make the tool interfaces, state management, planning loop, and error handling more specific.

I used GitHub Copilot to help draft implementation code for the tool functions and the agent loop. I provided Copilot with the relevant sections of `planning.md`, including the tool specs and architecture diagram. I reviewed and adjusted the generated code to make sure it matched the spec, especially the early stop when `search_listings()` returns no results and the fallback behavior when LLM calls fail. I tested the regular expression parsing logic separately to ensure it correctly extracts the description, size, and max price from various user query formats.

---

## Spec Reflection

One way the spec helped was by forcing the agent to be separated into three clear tools. This made the project easier to implement and test because search, outfit suggestion, and fit card generation could each be developed independently before being connected in the agent loop.

One way my implementation diverged from the starter example is that my agent automatically selects the top-ranked listing instead of asking the user to choose from multiple results. I made this choice because it keeps the demo end-to-end, avoids requiring another user input step, and clearly shows state passing from `search_listings()` to `suggest_outfit()` to `create_fit_card()`.
