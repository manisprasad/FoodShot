# FoodShot — MVP Specification

> Telegram bot for general food tracking, calorie/macro logging, and nutrition diary, with an optional Diabetes Mode for insulin dose suggestions.

---

## Scope

This document defines the **minimum viable product** of FoodShot.
Everything outside this scope is post-MVP.

---

## Core User Flow

```
User sends food photo
  → Bot downloads the image
  → Vision AI identifies dish + estimates portion (g)
  → Nutrition API fetches macros (carbs, kcal, protein, fat)
  → Calc Engine computes insulin bolus based on user profile
  → Bot replies with structured result card
  → Log entry saved to PostgreSQL
```

---

## Features

### 1. Onboarding (`/start`)

On first start, the bot guides the user through a simplified onboarding flow to configure:
- Language preference (English or Ukrainian)
- Optional daily calorie target (can be skipped)

No medical or diabetes-related parameters (like ICR, ISF, or target blood glucose) are requested during onboarding.

- Profile is saved to the PostgreSQL `users` table.
- User can modify settings or enable Diabetes Mode anytime with `/settings`.

---

### 2. Food Photo Analysis

- User sends any photo in chat.
- Bot replies: *"Analyzing your meal…"* while processing.
- Vision AI (GPT-4o Vision) extracts:
  - Dish name
  - Estimated weight (grams)
  - Confidence level (high / medium / low)
- If confidence is **low** → bot asks user to confirm or correct the dish name.

---

### 3. Nutrition Lookup (REST API)

- Primary: **USDA FoodData Central** (free, no key required for basic use)
- Fallback: **Nutritionix** (free tier: 500 req/day)
- Data fetched per 100g, scaled to estimated portion.

| Macro | Unit |
|---|---|
| Carbohydrates | g |
| Calories | kcal |
| Protein | g |
| Fat | g |

---

### 4. Optional Insulin Dose Calculation (Diabetes Mode only)

If the user enables **Diabetes Mode** in `/settings`, the bot will calculate and suggest insulin bolus doses.

#### Bolus formula

```
carb_dose   = carbs_g / icr
correction  = (current_bg - target_bg) / isf   # only if user provides BG
total_dose  = carb_dose + correction
```

#### Input from user (optional)

- After the nutrition lookup, the bot asks: *"What is your current blood glucose? (skip with /skip)"*
- If skipped → correction dose = 0, only carb bolus is calculated.

#### Output card sent to user (with Diabetes Mode active)

```
🍝 Pasta Bolognese (~250g)

Carbs:    48 g
Calories: 390 kcal
Protein:  18 g
Fat:      12 g

💉 Suggested bolus: 4.8 U (NovoRapid)
   Carb dose:   4.8 U
   Correction:  0.0 U (no BG provided)

⚠️ This is an estimate. Always verify with your doctor.
```

If Diabetes Mode is disabled (default), the output card only displays the food nutrition details without any insulin dose suggestions or prompts for blood glucose.

---

### 5. Logging

Every analyzed meal is saved automatically:

```sql
meal_logs (
  id, user_id, created_at,
  dish_name, portion_g,
  carbs_g, kcal, protein_g, fat_g,
  bolus_dose, current_bg,
  photo_file_id
)
```

- `/history` — shows last 10 meals as a list.
- No charts or export in MVP.

---

### 6. Commands

| Command | Description |
|---|---|
| `/start` | Onboarding, choose language, and set optional calorie target |
| `/settings` | Edit settings: Language, Calorie Target, Diabetes Mode, and Medical Parameters (ICR / ISF / target BG) if Diabetes Mode is enabled |
| `/history` | Last 10 meal logs |
| `/help` | Short usage guide |

---

## Technical Stack

| Layer | Technology |
|---|---|
| Bot framework | aiogram 3.x |
| Web server | FastAPI (webhook handler) |
| Vision AI | OpenAI GPT-4o Vision API |
| Nutrition data | USDA FoodData Central REST API |
| Database | PostgreSQL + SQLAlchemy (async) |
| State management | Redis (aiogram FSMContext) |
| Environment | Docker + docker-compose |
| Config | `.env` via `pydantic-settings` |

---

## Project Structure

```
foodshot/
├── bot/
│   ├── handlers/
│   │   ├── start.py        # onboarding FSM
│   │   ├── photo.py        # photo handler → analysis pipeline
│   │   ├── history.py      # /history command
│   │   └── settings.py     # /settings FSM
│   ├── keyboards/          # inline keyboards
│   ├── states.py           # FSM state groups
│   └── middlewares.py      # user injection middleware
├── services/
│   ├── photo_flow.py       # photo analysis pipeline orchestration
│   ├── vision.py           # GPT-4o Vision wrapper & dynamic cascade
│   ├── nutrition.py        # USDA / Nutritionix client
│   ├── security.py         # burst rate-limiting & anomaly protection
│   ├── freemium.py         # daily quota checks & subscription logic
│   └── calc.py             # insulin bolus formula
├── db/
│   ├── models.py           # SQLAlchemy models
│   └── crud.py             # async DB queries
├── api/
│   └── webhook.py          # FastAPI app + /webhook endpoint
├── core/
│   └── config.py           # pydantic Settings
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Database Schema

```sql
CREATE TABLE users (
  id                   BIGINT PRIMARY KEY,   -- Telegram user_id
  username             TEXT,
  icr                  FLOAT,                -- g carbs / 1U (nullable)
  isf                  FLOAT,                -- mmol/L drop / 1U (nullable)
  target_bg            FLOAT,                -- mmol/L (nullable)
  insulin_type         TEXT,
  language             TEXT DEFAULT 'en',
  diabetes_mode        BOOLEAN DEFAULT FALSE,-- Toggle for advanced diabetes mode
  daily_calorie_target INTEGER,              -- Optional daily calorie target
  created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE meal_logs (
  id            SERIAL PRIMARY KEY,
  user_id       BIGINT REFERENCES users(id),
  created_at    TIMESTAMP DEFAULT NOW(),
  dish_name     TEXT,
  portion_g     FLOAT,
  carbs_g       FLOAT,
  kcal          FLOAT,
  protein_g     FLOAT,
  fat_g         FLOAT,
  bolus_dose    FLOAT,
  current_bg    FLOAT,              -- nullable
  photo_file_id TEXT
);
```

---

## Environment Variables

```env
BOT_TOKEN=
OPENAI_API_KEY=
USDA_API_KEY=          # optional, higher rate limits
NUTRITIONIX_APP_ID=    # optional fallback
NUTRITIONIX_API_KEY=   # optional fallback
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/foodshot
REDIS_URL=redis://redis:6379/0
WEBHOOK_URL=https://yourdomain.com/webhook
```

---

## Out of Scope (Post-MVP)

- Meal history charts / export to CSV
- CGM integration (Dexcom, Libre)
- Basal rate recommendations
- Multiple insulin types per user
- Web dashboard
- Internationalization (i18n)
- Push reminders

---

## Disclaimer

> FoodShot provides **estimates only**. It is not a medical device and does not replace advice from a qualified healthcare professional. Always consult your doctor before adjusting insulin doses.

---

*FoodShot MVP — v0.1*
*License: Business Source License 1.1 (BUSL-1.1)*
