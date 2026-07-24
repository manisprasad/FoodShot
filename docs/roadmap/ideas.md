# FoodShot — Future Ideas

A running list of unstructured ideas for future features.
Not prioritized, not scoped — just captured for later review.

---

## 💡 Ideas

### Barcode Scanner
**Added:** 2026-07-08

User sends a photo of a product barcode (or scans it via the camera, like at a supermarket checkout) → bot looks up the product in a database (e.g., Open Food Facts, USDA branded foods) → returns nutrition info (calories, macros per 100g and per serving).

**Why it's valuable:** Covers packaged products where a photo-based food recognition wouldn't be as precise. Users could track snacks, drinks, yogurts, etc. with exact label data.

**Potential approach:**
- Use `pyzbar` or `python-barcode` to decode EAN/UPC codes from a photo.
- Query [Open Food Facts API](https://world.openfoodfacts.org/data) (free, no key needed) or USDA Branded Foods endpoint.
- Fallback to manual portion entry if product is not found in the DB.
- Same flow as photo recognition: user confirms portion → macros saved to meal log.

---

### Personalized AI Health & Nutrition Coach
**Added:** 2026-07-24

Deep personalization based on individual user parameters (ICR, ISF, target blood glucose, meal history, and daily glycemic patterns).
- **Personalized Context:** Dynamic AI prompts incorporating user profile metrics and recent meal logs.
- **Weekly Sunday Digest & AI Tips:** Automatic weekly report analyzing 7-day trends (average glucose, macro distribution, bolus stats) + 3 actionable, personalized AI tips (e.g. pattern detection such as late-night carb spikes).
- **Why it's valuable:** Transforms FoodShot from a simple photo calculator into an intelligent, personal daily/weekly health companion.

---

### RAG Knowledge Base (Medical & Glycemic Guidance)
**Added:** 2026-07-24

Retrieval-Augmented Generation (RAG) powered by PostgreSQL `pgvector`.
- **Functionality:** Seeds official diabetic guidance, glycemic index references, and nutrition rules into vector database. Answers user queries with strict zero-hallucination medical grounding.
- **Why it's valuable:** Solves LLM hallucination risks in high-stakes health decisions and grounds all recommendations in verified medical guidelines.

---

### Agentic Tool-Calling Engine & Multi-Component Plate Splitter
**Added:** 2026-07-24

Replaces rigid command flows with an autonomous Agentic execution loop using OpenAI Tool Calling.
- **Functionality:** Exposes backend functions (`query_medical_kb`, `search_usda_food`, `calculate_bolus_dose`, `log_water_intake`) as tools. Automatically splits multi-ingredient dinner photos (e.g. steak + potatoes + salad) into sub-items and calculates per-component macros.
- **Why it's valuable:** Allows flexible natural language/voice input and handles complex multi-step user requests seamlessly.

---

### AI Quality & Evaluation Framework (Evals)
**Added:** 2026-07-24

Automated evaluation test suite in `tests/evals/` running via `task test:evals`.
- **Functionality:** Measures RAG retrieval precision, context recall, zero-hallucination rate, and tool-routing accuracy against a curated gold-standard dataset.
- **Why it's valuable:** Establishes TDD/CI-CD discipline for AI components, ensuring high precision in high-stakes backend operations.

