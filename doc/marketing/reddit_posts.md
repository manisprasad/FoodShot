# Reddit Posts for FoodShot

## 1. Standalone Post for r/SideProject

**Title:** I built a Telegram bot that calculates insulin doses from food photos. Here is what I learned about building "dangerous" MVPs.

**Body:**
For a Type 1 Diabetic, eating a plate of fries involves: googling the carbs, estimating the weight, dividing by an Insulin-to-Carb Ratio, and adding a correction factor. It takes 3-5 minutes.

I built **FoodShot** to reduce this to 20 seconds. You send a photo → it recognizes the food → fetches macros from the USDA database → calculates the exact insulin dose. 

**The Golden Rule of this MVP:**
I used GPT-4o for the vision part. But I made a strict rule: **The AI is not allowed to do math or guess nutritional values.** 
It only identifies the food and estimates the weight. The macros come from an official database, and the dose calculation is pure Python code. If an LLM hallucinates 60g of carbs instead of 30g, the user could end up in a hospital. Determinism > Elegance.

**The Stack:** Python, aiogram 3.x, FastAPI, PostgreSQL, Redis. 

**Things that broke immediately:**
1.  **Comma vs Dot:** European users type "5,6" instead of "5.6". It crashed the bot on the first input. 
2.  **Database Quirks:** The USDA database returns calories in both `kcal` and `kJ` in the same array. I almost told a user that a bowl of rice had 1500 calories before I caught the unit difference.
3.  **Cross-language UI:** To show localized names to my users but search the English USDA database, I make the Vision model return both in one JSON payload.

It’s about 1,000 lines of Python. It has debug prints in production, zero API error handling, and only 7 tests. But the math works perfectly, and that's the only thing that matters right now.

You can check out the architecture and MVP docs here: https://github.com/soroqn1/foodshot-docs 
Would love to hear your thoughts or similar experiences integrating AI with rigid legacy databases!

---

## 2. Comment for r/Python (Monthly Showcase Thread)

*(Note: r/Python rules forbid standalone showcase posts for AI wrapper projects. Post this ONLY as a comment in the Monthly/Daily Showcase threads).*

**What My Project Does**
**FoodShot** is an aiogram 3.x / FastAPI Telegram bot that calculates insulin doses for Type 1 Diabetics. User sends a food photo → GPT-4o Vision identifies the dish/weight → Bot fetches macros from the USDA database → Bot calculates the insulin dose deterministically. I explicitly separated the AI from the math to prevent medical hallucinations.

**Target Audience**
Built as a personal MVP for diabetes management.

**Comparison**
Most AI calorie counters rely fully on LLMs to guess macros. For insulin dosing, a hallucinated carb count is literally dangerous. I restricted the LLM to only act as the "eyes", while nutritional facts come purely from the rigid USDA database and calculations are pure Python code.

**Stack & Lessons Learned:**
* Uses aiogram's FSM on Redis to survive server restarts mid-conversation.
* Parsing OpenAI's JSON without Structured Outputs means dealing with regex to strip markdown code blocks. Extremely brittle, migrating soon.
* The USDA DB returns mixed units (`kcal` and `kJ`) in the same array, which almost led to a 1500-calorie bowl of rice bug.

**Links:**
Architecture and MVP docs: https://github.com/soroqn1/foodshot-docs
