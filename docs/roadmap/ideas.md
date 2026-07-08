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
