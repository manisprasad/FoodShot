# FoodShot AI Guidelines

This file contains the core context, architectural guidelines, and rules for all AI agents working in this project.

## What it does
User sends a food photo → bot recognizes the dish (OpenAI GPT-4o) → fetches nutrition from USDA → user adjusts portion → optionally enters blood glucose → bot calculates insulin bolus → saves meal to history.

## Critical design constraint
AI (GPT-4o) is ONLY used for food photo recognition (dish name, weight estimate, confidence score). All nutrition data comes from USDA FoodData Central. All calculations use transparent math formulas. The bot is NOT a medical device.

## Tech stack
- Python 3.11–3.13, Poetry
- aiogram 3.x (Telegram bot framework, FSM)
- FastAPI (webhook endpoint)
- PostgreSQL + async SQLAlchemy (users, meal_logs)
- Redis (FSM state storage)
- Docker + Docker Compose
- Taskfile for dev commands

## Project structure
.
├── api/webhook.py              # FastAPI app, Telegram webhook
├── bot/
│   ├── handlers/               # start, photo, settings, history, help
│   ├── keyboards/              # reply and inline keyboards
│   ├── states.py               # aiogram FSM states
│   └── i18n_middleware.py      # language detection
├── core/
│   ├── config.py               # pydantic settings
│   └── i18n.py                 # runtime translations
├── db/
│   ├── models.py               # SQLAlchemy models (users, meal_logs)
│   ├── crud.py                 # async DB operations
│   └── database.py             # engine and session setup
├── services/
│   ├── vision.py               # OpenAI vision wrapper
│   ├── nutrition.py            # USDA nutrition client
│   └── calc.py                 # bolus calculation
├── locales/                    # i18n (EN, UK)
├── doc/
│   ├── foodshot_architecture.svg
│   └── tg_fries.png
├── docker-compose.yml
├── Dockerfile
├── Taskfile.yml
└── pyproject.toml

## Data model
- `users`: telegram_id, username, ICR, ISF, target_glucose, insulin_type, language
- `meal_logs`: dish, portion, macros, suggested_bolus, current_glucose, photo_id, timestamp

## Bolus formula
carb_dose  = carbs_g / icr
correction = (current_bg - target_bg) / isf   # only if current > target
total      = carb_dose + correction

## MVP roadmap (not yet implemented)
- Diary with pattern detection (glucose spikes after specific meals)
- Data export to CSV/Excel for doctors
- Freemium: 2-3 free analyses/day, ~$2-3/month premium
- Out of scope for MVP: CGM integrations (Dexcom, Libre), complex multi-component meal splitting

## Documentation
- MVP spec: https://github.com/soroqn1/foodshot-docs/blob/main/MVP.md
- Architecture diagram: https://github.com/soroqn1/foodshot-docs/blob/main/foodshot_architecture.svg

## Working rules
- Keep the AI boundary strict: no LLM-generated nutrition data or medical advice.
- Localization: all user-facing strings go through i18n (EN + UK).
- Async everywhere: use async SQLAlchemy, aiohttp for external APIs.
- Follow existing code style and project structure.

## AI Development Workflow
1. **Always use Poetry and Taskfile:** All script executions, tests, and linting must be run via `Taskfile.yml`. If a required command is missing, add it to `Taskfile.yml` first.
2. **Post-Code Verification:** After writing code, ALWAYS run Ruff (linting and formatting) via the appropriate Taskfile commands.
3. **Problem Alignment:** Verify that the code precisely solves the user's intended problem. If something is ambiguous, unclear, or doesn't align with the project constraints, **STOP and ask the user** before proceeding.
4. **Commit (DO NOT PUSH):** If confident that the code is correct and all checks pass, commit the changes locally with a descriptive commit message explaining what was done. If the commit fails, resolve the issue and try again. Do **NOT** push the code to remote; leave pushing to the user.
