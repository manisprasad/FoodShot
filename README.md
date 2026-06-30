# FoodShot

Your smart diary for food, insulin, and blood glucose tracking, built to help you find repeating patterns in your body's behavior and seamlessly export data for your doctor.

**The Role of AI:** Artificial Intelligence in FoodShot is strictly limited to one task — **recognizing food from photos** (estimating dish name and weight). The AI **does not** manage your diary or calculate your insulin. All nutritional data is pulled from official US databases (USDA), and all calculations use transparent, hardcoded medical formulas.

## ✨ Core Philosophy
- **Diary & Patterns First:** The main goal is to log your meals, glucose, and insulin to find repeating patterns over time.
- **AI as a Simple Assistant:** GPT-4o is only used to save you time by identifying what's on your plate. It does not make decisions.
- **No Extra Apps:** Everything lives in Telegram, where you already spend your time.
- **Doctor-Friendly Exports:** Effortlessly export your history and patterns for medical professionals or personal spreadsheets.
- **Freemium & Accessible:** 2-3 free requests per day for everyone. A symbolic $2-3 premium tier exists purely to support the project and cover API costs.
- **Optional Insulin Bonus:** For those who need it, the bot provides a transparent bolus calculation based on your ICR and ISF. It's completely optional.

**Disclaimer:** The bot is an assistant, not a doctor. All calculations are transparent but serve as estimates. It does not replace professional medical advice or independent calculations.

## 🛠 Tech Stack

- **Bot Framework:** [aiogram 3.x](https://docs.aiogram.dev/)
- **Web Server:** [FastAPI](https://fastapi.tiangolo.com/) (Webhook handler)
- **Database:** PostgreSQL 15 + SQLAlchemy 2.0 (asyncpg)
- **State & Cache:** Redis 7
- **Integrations:** OpenAI GPT-4o Vision API, USDA FoodData Central API
- **Deployment:** Docker, Docker Compose

## 🏗 Architecture

The system operates strictly via webhooks. Telegram sends updates to the FastAPI endpoint, which routes them to aiogram handlers.

![FoodShot Architecture](./doc/foodshot_architecture.svg)

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- Taskfile (`go-task`)
- Python 3.11+ (for local development)
- Poetry

### Installation

1. **Clone and Configure:**
   ```bash
   git clone <repo_url> && cd foodshot
   cp .env.example .env
   ```
   *Edit `.env` and fill in `BOT_TOKEN`, `OPENAI_API_KEY`, and `USDA_API_KEY`.*

2. **Start Infrastructure (DB & Redis):**
   ```bash
   task infra
   ```

3. **Run Application (Docker):**
   ```bash
   task up
   ```

### Local Development

1. Install dependencies: `task install`
2. Start local server: `task dev`
3. Expose port using ngrok: `ngrok http 8000`
4. Update `WEBHOOK_URL` in `.env`.

## 📜 License
Commercial / Proprietary. Selected source files are made available for portfolio demonstration purposes only. All rights reserved.
