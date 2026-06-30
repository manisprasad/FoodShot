# Project Resources and Links

This document contains all external services, dashboards, and API keys required for FoodShot development and deployment.

## Telegram
* **BotFather:** [https://t.me/BotFather](https://t.me/BotFather)
  * *Purpose:* Bot creation, generating the `BOT_TOKEN`, and configuring the bot's profile and commands.

## AI and Vision
* **OpenAI API Dashboard:** [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
  * *Purpose:* Managing the `OPENAI_API_KEY` for GPT-4o Vision. You can also monitor API usage and billing here.

## Nutrition Databases
* **USDA FoodData Central:** [https://fdc.nal.usda.gov/api-key-signup.html](https://fdc.nal.usda.gov/api-key-signup.html)
  * *Purpose:* The primary free nutrition data source. Register here to get a `USDA_API_KEY` to increase your rate limits.
* **Nutritionix (Fallback):** [https://developer.nutritionix.com/](https://developer.nutritionix.com/)
  * *Purpose:* The secondary nutrition data source. Provides `NUTRITIONIX_APP_ID` and `NUTRITIONIX_API_KEY`.

## Infrastructure and Deployment
* **Cloudflare Dashboard:** [https://dash.cloudflare.com/](https://dash.cloudflare.com/)
  * *Purpose:* Domain management and Cloudflare Tunnels (Zero Trust) configuration for secure production deployment.
* **Cloudflare Tunnels Documentation:** [https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
  * *Purpose:* Command reference for `cloudflared`.

## Public Documentation
* **Public Docs Repository:** [https://github.com/soroqn1/foodshot-docs](https://github.com/soroqn1/foodshot-docs)
  * *Purpose:* Public-facing repository intended for recruiters and future users. Contains the high-level `MVP.md`.
