# Pivot Strategy: Shifting Focus from Diabetics to General Food Tracker

## Rationale
1. **Medical Liability & Regulation:** Providing direct insulin bolus recommendations exposes the application to strict medical device regulations (e.g., FDA in the US, CE mark in Europe) and legal liabilities. Any miscalculation or incorrect user input (like a negative ICR or zero ISF) could lead to dangerous health outcomes.
2. **Market Size:** Shifting the focus to a general food tracker, calorie counter, and nutrition diary dramatically increases the potential user base (fitness enthusiasts, people losing weight, healthy eaters) while keeping the diabetes features as an optional advanced setting.

---

## Strategic Changes

### 1. Core Focus Shift
- **Primary Mode:** A clean, easy-to-use food diary and calorie/macro tracker powered by AI photo recognition.
- **Optional Mode ("Diabetes Mode"):** An advanced toggle in `/settings` that enables blood glucose tracking, ICR/ISF parameters, and insulin dose calculation.

### 2. Onboarding Flow (`/start`)
- **Default Flow:** Guide the user to set up basic profile fields:
  - Language preference.
  - Optional daily calorie target.
- **Removed from Default Onboarding:** ICR, ISF, target blood glucose, and insulin type. These will not be requested unless the user explicitly enables "Diabetes Mode" in their profile.

### 3. Settings (`/settings`)
- Introduce a new toggle: **Enable Diabetes Mode (On/Off)**.
- If **Diabetes Mode** is **Off** (default):
  - Settings only show Language and Daily Calorie Target.
- If **Diabetes Mode** is **On**:
  - Show options to configure and edit ICR, ISF, Target BG, and Insulin Type.
  - **Validation:** Enforce strict, safe ranges for these medical parameters to prevent dangerous inputs:
    - `ICR` (Insulin-to-Carb Ratio): `[1.0, 100.0]` g/U
    - `ISF` (Insulin Sensitivity Factor): `[0.1, 20.0]` mmol/L/U
    - `Target BG` (Target Blood Glucose): `[3.0, 12.0]` mmol/L

### 4. Photo Analysis & Calculations
- By default, sending a food photo only returns the recognized dish, portion weight, and nutrition details (Carbs, Calories, Protein, Fat).
- The insulin dose calculation prompt ("What is your current blood glucose?") and the bolus suggestion on the result card are only active when **Diabetes Mode** is enabled.

---

## Action Plan (Summary)
1. **Create the Pivot Plan:** Document the step-by-step code changes in `doc/plans/06_pivot_food_tracker/`.
2. **Database Migration:** Modify the `users` table schema to make `icr`, `isf`, and `target_bg` nullable, and add a `diabetes_mode` boolean column (default `false`).
3. **Refactor Onboarding (`bot/handlers/start.py`):** Simplify the startup FSM flow to only ask for language and optional calorie targets.
4. **Refactor Settings (`bot/handlers/settings.py`):** Add the Diabetes Mode toggle and implement the new FSM flows with range validations for medical fields.
5. **Refactor Photo Handler (`bot/handlers/photo.py`):** Skip insulin calculations and glucose prompts unless Diabetes Mode is enabled.

---

## Future Monetization & Rate Limiting (Deferred)
- **Abuse Protection & Tier Limits (Issue 12):** Preventing OpenAI API budget exhaustion is directly tied to user tiers (Free vs. Premium). Rather than implementing a temporary rate limiting middleware now, it will be deferred to the payments/subscriptions implementation phase.
- **Proposed Limits:**
  - **Free Tier:** 3 photo analyses per day (tracked via Redis counter resetting daily).
  - **Premium Tier:** Unlimited photo analyses (validated via active subscription status check in PostgreSQL).
