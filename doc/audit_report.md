# Technical Audit Report & Bottlenecks

**Project:** FoodShot
**Type:** Commercial

## 1. Database & Migrations
- **Critical Issue:** Absence of a migration tool. The project uses SQLAlchemy models (`db/models.py`) but lacks `alembic`. 
- **Risk:** Any changes to the database schema (e.g., adding a new field to `users`) will require dropping tables or manual SQL execution, which is unacceptable for production and will lead to data loss.
- **Recommendation:** Integrate `alembic` immediately. Add `alembic.ini` and a `migrations/` folder. Create a task in `Taskfile.yml` for running migrations automatically before application startup.

## 2. Quality Assurance & Testing
- **Critical Issue:** No `tests/` directory and no testing framework (`pytest`) in `pyproject.toml`.
- **Risk:** The project contains critical medical logic (`services/calc.py`). A bug in the bolus calculation formula could directly harm a user's health. 
- **Recommendation:** 
  - Add `pytest` and `pytest-asyncio`.
  - Achieve 100% test coverage strictly for `services/calc.py`.
  - Mock external dependencies (`OpenAI`, `USDA`) to test the webhook and aiogram handlers.

## 3. Security & Webhook Integrity
- **Moderate Issue:** Webhook vulnerability.
- **Risk:** If the `/webhook` endpoint is publicly accessible without validation, malicious actors can send spoofed Telegram updates to the API.
- **Recommendation:** Implement `X-Telegram-Bot-Api-Secret-Token` header validation in FastAPI (`api/webhook.py`) to guarantee that requests originate exclusively from Telegram servers.

## 4. AI Service Stability (`services/vision.py`)
- **Moderate Issue:** Fragile JSON parsing. The code relies on Regex (`re.search(r"\{.*\}", ...)`) to extract JSON from the GPT-4o response.
- **Risk:** LLMs can format outputs unpredictably. Regex parsing will inevitably break, causing application errors.
- **Recommendation:** Migrate to OpenAI's **Structured Outputs** (`response_format={ "type": "json_schema", "json_schema": {...} }`). This guarantees a valid JSON matching the exact expected schema at the API level, removing the need for manual regex parsing.

## 5. Observability (Logging & Monitoring)
- **Moderate Issue:** Lack of centralized/structured logging.
- **Risk:** Silent failures. If the USDA API times out, or GPT-4o rejects an image, diagnosing the issue via standard `print()` or basic `logging` inside Docker will be difficult.
- **Recommendation:** 
  - Integrate `structlog` or `loguru` for JSON-formatted logs.
  - Implement exception tracking (e.g., Sentry) to catch unhandled errors in async handlers and FastAPI routes.

## 6. Performance & Cost Management (Commercial Context)
- **Optimization Opportunity:** No caching for food nutrition lookups.
- **Risk:** Hitting rate limits on USDA/Nutritionix APIs and paying for redundant OpenAI vision requests for common foods (e.g., "Apple", "Fried eggs").
- **Recommendation:** Implement an application-level cache using the existing Redis instance. Cache nutrition data by normalized dish names (TTL ~7 days). Implement user-level rate limiting in FastAPI/aiogram middlewares to prevent API abuse and control costs.
