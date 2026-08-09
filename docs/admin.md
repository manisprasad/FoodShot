# Operations Console (TUI)

FoodShot includes a built-in Terminal User Interface (TUI) powered by [Textual](https://textual.textualize.io/). 

Running a production Telegram bot often requires rapid manual interventions—granting premium access, checking why a user is stuck in a state, or reviewing the exact prompt sent to the LLM. Instead of building a heavy web dashboard or forcing developers to run raw SQL queries, FoodShot provides everything directly in the terminal.

## Key Features

- **User Management:** Quickly look up users by their Telegram ID or username. Toggle their Premium status or Diabetes Mode with a single keystroke.
- **FSM State Control:** Inspect the current state of any user in the aiogram Finite State Machine. If a user is stuck in a "waiting for input" state, you can force-reset their state from the console.
- **Live Monitoring:** Stream real-time logs and monitor system health (Redis connection, Database latency) without leaving your SSH session.
- **Meal History Inspection:** View the last logged meals and their raw macro data to debug AI miscalculations.

## How to use

The console runs locally or over SSH and connects directly to your Postgres and Redis instances.

To launch the dashboard, run:
```bash
task ops
```

*Note: Ensure your local environment is configured (`.env`) and services are running before launching the console.*
