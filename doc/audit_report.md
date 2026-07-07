# Technical Audit Report & Bottlenecks

**Project:** FoodShot
**Type:** Commercial

*Note: Previously resolved issues have been removed from this document.*

## 1. Webhook Blocking & Retries (Critical)
- [x] **Issue:** The Telegram webhook in `api/webhook.py` processes updates synchronously. 
- **Risk:** If OpenAI or USDA APIs take longer than a few seconds, Telegram will time out and retry the webhook. This leads to duplicate processing of the same photo (spamming the user), hitting API rate limits, and exhausting FastAPI worker threads.
- **Recommendation:** Process updates in the background. In `api/webhook.py`, use FastAPI's `BackgroundTasks` to run `dp.feed_update(bot, telegram_update)` asynchronously so the webhook can return `{"status": "ok"}` immediately.

## 2. Unhandled API Errors in USDA Client (High)
- [x] **Issue:** `services/nutrition.py` does not catch HTTP or network exceptions.
- **Risk:** If the USDA API returns a 502, 503, or 429 status code, `response.json()` or the request itself will throw an exception (e.g., `httpx.RequestError`). This unhandled exception crashes the webhook handler, leading to a 500 Internal Server Error, which again causes Telegram to retry endlessly.
- **Recommendation:** Wrap the API call in a `try...except` block, use `response.raise_for_status()`, and gracefully return `None` or raise a custom exception that the bot can catch and notify the user about.

## 3. Missing Explicit Timeouts (Moderate)
- [x] **Issue:** `AsyncOpenAI` and `httpx.AsyncClient` do not have strict timeouts configured.
- **Risk:** The default timeout for OpenAI is 10 minutes. If their API hangs, the bot connection hangs with it, locking up resources.
- **Recommendation:** Set an explicit `timeout` parameter (e.g., 10-15 seconds) for both `httpx.AsyncClient()` and `AsyncOpenAI()`.

## 4. Misleading UX on AI Failure (Moderate)
- [x] **Issue:** In `services/vision.py`, any exception during OpenAI processing is caught and `None` is returned.
- **Risk:** The handler interprets `None` as "Food not found" (`not-found`). If OpenAI is down or out of credits, the user receives an incorrect message ("Food not found") instead of a proper error message ("Service unavailable").
- **Recommendation:** Distinguish between a successful API call where no food is detected, and a technical failure. Raise a specific exception for API failures and handle it in `photo.py` with a relevant error message to the user.

## 5. Database Connection Pool Configuration (Low)
- [ ] **Issue:** `db/database.py` initializes the async engine without specifying `pool_size` or `max_overflow`.
- **Risk:** The default pool size (5) is too small for a concurrent async bot under load. Spikes in user traffic could lead to database connection exhaustion and timeouts.
- **Recommendation:** Explicitly configure connection pool parameters in `create_async_engine`, e.g., `pool_size=20`, `max_overflow=10`.

## 6. No Exception Handling in Any Handler (Critical)
- [x] **Issue:** All bot handlers (`photo.py`, `start.py`, `settings.py`, `history.py`) have zero `try/except` blocks around DB operations, Telegram API calls, or service calls.
- **Risk:** Any `SQLAlchemyError`, `TelegramAPIError`, or network exception propagates unhandled → FastAPI returns 500 → Telegram retries endlessly. The user receives no error message, just silence or spam from retries.
- **Recommendation:** Register a global error handler via `dp.errors.register()` that catches all unhandled exceptions, logs them, and sends a user-friendly "Something went wrong, please try again" message. Additionally, wrap critical service calls in handlers with specific `try/except` blocks.

## 7. No Idempotency / Duplicate Protection (Critical)
- [x] **Issue:** There is no protection against processing the same Telegram `update_id` twice. Combined with webhook blocking (#1), Telegram retries cause duplicate processing.
- **Risk:** A single photo can trigger 2-3 identical OpenAI API calls (billed separately), 2-3 identical `meal_logs` saved to the database, and 2-3 duplicate result messages to the user.
- **Recommendation:** Track processed `update_id` values in a Redis set with a short TTL (e.g., 5 minutes) and skip duplicates at the webhook level before calling `dp.feed_update()`.

## 8. Division by Zero if AI Returns weight_g = 0 (High)
- [ ] **Issue:** In `bot/handlers/photo.py` (lines 67-70), `nutrition_data` values are divided by `weight_g` to get per-gram values. The `weight_g` value comes directly from GPT-4o with no validation.
- **Risk:** If the model returns `weight_g: 0`, all four divisions crash with `ZeroDivisionError`, which is unhandled (see #6).
- **Recommendation:** Validate `weight_g > 0` immediately after vision returns. If invalid, treat it as a failed recognition and notify the user.

## 9. No Range Validation on Medical Parameters (High)
- [ ] **Issue:** During registration (`bot/handlers/start.py`), ICR, ISF, and target_bg are only validated as `float()`. There are no range checks. *(DEFERRED: To be implemented as part of Diabetes Mode during the product pivot phase)*
- **Risk:** `ICR = 0` → `ZeroDivisionError` in `services/calc.py:11`. `ICR < 0` → negative bolus dose (dangerous medical output). `ISF = 0` → `ZeroDivisionError` in `services/calc.py:17`. Although `calc.py` raises `ValueError` for ICR/ISF ≤ 0, nobody catches that `ValueError` in `photo.py` (see #6).
- **Recommendation:** Validate input ranges at registration and settings update time: `ICR ∈ [1, 100]`, `ISF ∈ [0.1, 20]`, `target_bg ∈ [3.0, 10.0]`. Also catch `ValueError` from `calc.py` in the photo handler.

## 10. DB Middleware Has No Error/Rollback Handling (High)
- [x] **Issue:** `bot/middlewares.py` opens a DB session and passes it to the handler, but has no `try/except` and no explicit `rollback`.
- **Risk:** If a handler raises an exception mid-transaction, the session is closed by the context manager but uncommitted changes may be in an inconsistent state. Since `crud.py` calls `session.commit()` per operation, partial commits can occur — e.g., a meal log is committed but the user never sees the result because a subsequent Telegram call fails.
- **Recommendation:** Wrap the handler call in `try/except`, call `session.rollback()` on error, and consider using a single commit-at-the-end pattern instead of per-operation commits.

## 11. Redis Failure Crashes Nutrition Flow (Moderate)
- [x] **Issue:** `services/nutrition.py` calls `redis_client.get()` and `redis_client.setex()` with no exception handling. Redis is used as a cache.
- **Risk:** If Redis is temporarily down, `redis.ConnectionError` crashes the entire nutrition lookup, even though it should degrade gracefully to "no cache." This makes the bot fully dependent on Redis uptime for a feature that is purely a performance optimization.
- **Recommendation:** Wrap cache reads/writes in `try/except redis.RedisError` and fall through to the USDA API call on cache failure.

## 12. No Rate Limiting or Abuse Protection (Moderate)
- [ ] **Issue:** There is no throttling or rate limiting anywhere in the bot. Any user can send unlimited photos. *(DEFERRED: To be implemented during the payment and subscription integration phase)*
- **Risk:** A single malicious user or bot can flood the webhook with photos → unlimited OpenAI API calls ($$$) → exhaust DB connections → exhaust USDA rate limits → denial of service for all users.
- **Recommendation:** Use aiogram's built-in `Throttling` middleware or implement a Redis-based rate limiter (e.g., max 5 photos/minute per user, max 30/day for free tier).

## 13. No Health Check Endpoint (Moderate)
- [ ] **Issue:** `api/webhook.py` only exposes `/webhook`. There is no `/health` or `/ready` endpoint.
- **Risk:** Docker `restart: always` will restart the container on crash, but cannot distinguish between "running but stuck" (e.g., deadlocked event loop) and "healthy." Without a health check, a zombie container stays running indefinitely.
- **Recommendation:** Add a `GET /health` endpoint that verifies DB and Redis connectivity. Configure Docker `healthcheck` in `docker-compose.yml`.

## 14. Dockerfile Runs as Root (Moderate)
- [ ] **Issue:** The `Dockerfile` has no `USER` directive. The application runs as `root` inside the container.
- **Risk:** If an attacker finds a remote code execution vulnerability, they gain root access to the container, which can be used to pivot to the host or other containers.
- **Recommendation:** Add a non-root user: `RUN adduser --disabled-password --gecos '' appuser` and `USER appuser`.

## 15. `.env` May Be in Git History (Moderate)
- [x] **Issue:** `.env` file (1KB+) exists in the working directory. It may have been committed to git history with real API keys. *(VERIFIED: Checked git log history, .env was never committed and is correctly ignored by .gitignore)*
- **Risk:** Anyone with access to the git history can extract `BOT_TOKEN`, `OPENAI_API_KEY`, `USDA_API_KEY`, `DATABASE_URL`, and `WEBHOOK_SECRET_TOKEN`.
- **Recommendation:** Verify `.env` is in `.gitignore`. Run `git log --all --full-history -- .env` to check if it was ever committed. If so, rotate all credentials and use `git filter-repo` to remove it from history.

## 16. History May Exceed Telegram Message Limit (Low)
- [ ] **Issue:** `bot/handlers/history.py` concatenates up to 10 meal items into a single message. Telegram messages have a 4096 character limit. *(DEFERRED: To be implemented during the global import/export refactoring phase)*
- **Risk:** With long dish names or many items, the message can exceed 4096 characters → `TelegramBadRequest` exception → unhandled crash (see #6).
- **Recommendation:** Truncate the message or paginate results. Check `len(text) < 4096` before sending.

## 17. i18n Format Can Throw KeyError (Low)
- [ ] **Issue:** `core/i18n.py` line 89 calls `text.format(**kwargs)`. If a translation template contains `{dish}` but the caller doesn't pass `dish` in kwargs, it throws `KeyError`.
- **Risk:** Adding a new translation key with a placeholder but forgetting the kwarg in one call site causes an unhandled crash. No unit tests cover this.
- **Recommendation:** Use `str.format_map(defaultdict(str, kwargs))` or wrap in `try/except KeyError` to return the raw template on failure.
