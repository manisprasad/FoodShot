# FoodShot Architecture

Below is the complete architecture diagram of the FoodShot project, including all active modules, background jobs, Admin TUI, integrations, and the main bot pipeline.

```mermaid
flowchart TD
    %% Define Styles
    classDef user fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
    classDef external fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;
    classDef bot fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000;
    classDef service fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000;
    classDef db fill:#ffebee,stroke:#d32f2f,stroke-width:2px,color:#000;
    classDef core fill:#eceff1,stroke:#607d8b,stroke-width:2px,color:#000;
    classDef admin fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000;
    classDef jobs fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#000;
    classDef dev fill:#f3f3f3,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray: 5 5,color:#000;

    %% Actors & External Entities
    User(("User\n(Telegram)")):::user
    Admin(("Admin\n(Terminal)")):::admin
    TG["Telegram API"]:::external

    %% Development & QA Layer
    subgraph DevQA ["Development & QA Layer"]
        Tests["pytest\n(tests/)"]:::dev
        Ruff["Ruff\n(Linting & Formatting)"]:::dev
        Taskfile["Taskfile.yml\n(Task Runner)"]:::dev
    end

    %% Config & Localization (Core)
    subgraph Core ["0. Core (Config, Utils, i18n)"]
        Config["config.py\n(Pydantic Settings)"]:::core
        I18n["i18n.py & locales/\n(Translations)"]:::core
        Logger["logger.py (Loguru)"]:::core
        TimeUtils["time_utils.py\n(Timezone & Dates)"]:::core
    end

    %% Admin & Ops Layer
    subgraph Ops ["Admin / Ops (TUI)"]
        TUI["Textual UI Dashboard\n(ops/tui.py, views.py)"]:::admin
        Alembic["Alembic Migrations\n(migrations/)"]:::admin
    end

    %% Web Server & Entrypoints Layer
    subgraph Entrypoints ["1. Entrypoints"]
        Webhook["Webhook Endpoint\n(api/webhook.py)"]:::bot
        Polling["Dev Polling\n(bot_polling.py)"]:::bot
    end

    %% Bot Application Layer
    subgraph Bot_Layer ["2. Bot Application Layer (aiogram)"]
        Router["Message Router / Dispatcher"]:::bot
        
        subgraph Middlewares_Group ["Middlewares"]
            M_User["middlewares.py\n(User/Session Inject)"]:::bot
            M_I18n["i18n_middleware.py\n(Locale Inject)"]:::bot
        end
        
        subgraph Handlers ["Bot Handlers & UI"]
            H_Start["/start (Onboarding)"]:::bot
            H_Photo["photo.py (Analysis Flow)"]:::bot
            H_Settings["settings.py (Profile)"]:::bot
            H_History["history.py (DB View)"]:::bot
            H_Export["export.py (Data Export)"]:::bot
            H_Common["common.py"]:::bot
            States["states.py (FSM Definitions)"]:::bot
            Keyboards["keyboards.py (UI)"]:::bot
        end
    end

    %% Core Services Layer
    subgraph Service_Layer ["3. Core Services Layer (Business Logic)"]
        S_PhotoFlow["photo_flow.py\n(Pipeline Orchestrator)"]:::service
        S_Vision["vision.py\n(AI Wrapper & Image Compression via Pillow)"]:::service
        S_Nutrition["nutrition.py\n(Macro Fetcher)"]:::service
        S_Calc["calc.py\n(Bolus Formula)"]:::service
        S_Security["security.py\n(Rate-limiting & Anomaly)"]:::service
        S_Freemium["freemium.py\n(Daily Quota Logic)"]:::service
    end

    %% Background Jobs & Scripts Layer
    subgraph Background_Jobs ["Background Jobs & Scripts"]
        J_Daily["daily_report.py\n(Sends Daily Summaries)"]:::jobs
        J_Retention["retention.py\n(Data cleanup & Export generation)"]:::jobs
        J_Broadcast["broadcast.py / scripts/\n(Mass Messaging)"]:::jobs
        J_KeepAlive["keep_alive.py"]:::jobs
    end

    %% Data Access Layer
    subgraph Data_Layer ["4. Data Access Layer"]
        DB_Engine["database.py\n(Async Engine & Sessions)"]:::core
        CRUD["crud.py\n(Async DB Operations)"]:::core
        Models["models.py\n(SQLAlchemy Schemas)"]:::core
    end

    %% Infrastructure & DBs
    subgraph Infrastructure ["5. Infrastructure (Docker Compose)"]
        PostgreSQL[("PostgreSQL\n(users, meal_logs)")]:::db
        Redis[("Redis\n(FSM State & Limits)")]:::db
        Cloudflared["Cloudflare Tunnel\n(cloudflared)"]:::db
    end

    %% External APIs
    subgraph External_APIs ["6. External APIs"]
        OpenAI["OpenAI\n(GPT-4o Vision)"]:::external
        Gemini["Google Gemini\n(Fallback Vision)"]:::external
        USDA["USDA FoodData Central\n(Primary)"]:::external
        Nutritionix["Nutritionix\n(Fallback)"]:::external
        Langfuse["Langfuse\n(LLM Observability / Tracing)"]:::external
    end

    %% ==========================================
    %% Relationships & Flow
    %% ==========================================

    %% Config injection (virtual)
    Config -. "Loads Env Vars" .-> Entrypoints
    Config -. "Provides DB URI" .-> DB_Engine
    Config -. "Provides API Keys" .-> External_APIs

    %% Admin & DB Management
    Admin -- "CLI / Terminal" --> TUI
    Admin -- "Applies schema" --> Alembic
    Alembic -. "Migrates DB" .-> PostgreSQL
    TUI -. "Reads/Writes via DB Engine" .-> DB_Engine

    %% User to Bot
    User -- "Sends Photo/Text" --> TG
    TG -- "1a. Webhook Event via Tunnel" --> Cloudflared
    Cloudflared -- "Routes to localhost" --> Webhook
    TG -- "1b. Long Polling" --> Polling
    Webhook -- "Forwards Update" --> Router
    Polling -- "Fetches Updates" --> Router
    
    %% Router to Handlers
    Router --> Middlewares_Group
    Middlewares_Group --> H_Start
    Middlewares_Group --> H_Photo
    Middlewares_Group --> H_Settings
    Middlewares_Group --> H_History
    Middlewares_Group --> H_Export
    Middlewares_Group --> H_Common
    
    %% Bot responding
    Handlers -- "Replies (bot.send_message)" --> TG

    %% Background Jobs Flow
    J_Daily -. "Sends scheduled reports" .-> TG
    J_Daily -. "Fetches logs" .-> CRUD
    J_Retention -. "Cleans & Exports" .-> CRUD
    J_Broadcast -. "Sends updates" .-> TG
    J_Broadcast -. "Fetches users" .-> CRUD
    
    %% Localization
    I18n -. "Provides strings" .-> M_I18n
    M_I18n -. "Translates UI" .-> Handlers
    
    %% Handler to Service
    H_Photo -- "Initiates Analysis Pipeline" --> S_PhotoFlow
    
    %% Security & Freemium checks
    H_Photo -. "Rate Limit Check" .-> S_Security
    H_Photo -. "Quota Check" .-> S_Freemium
    
    %% Photo Flow Orchestration
    S_PhotoFlow -- "1. Identify & Weigh" --> S_Vision
    S_Vision -- "Traced via API" --> Langfuse
    S_Vision -- "REST API" --> OpenAI
    S_Vision -. "Fallback" .-> Gemini
    
    S_PhotoFlow -- "2. Fetch Macros" --> S_Nutrition
    S_Nutrition -- "REST API" --> USDA
    S_Nutrition -- "REST API" --> Nutritionix
    
    S_PhotoFlow -- "3. Calculate Insulin" --> S_Calc
    
    %% State & Data Operations
    Router -. "Reads/Writes FSM State" .-> Redis
    States -. "Defines Flow" .-> H_Start
    States -. "Defines Flow" .-> H_Photo
    States -. "Defines Flow" .-> H_Settings
    Keyboards -. "Renders Buttons" .-> Handlers
    S_Security -. "Token Bucket / Limits" .-> Redis
    
    %% DB Interactions via CRUD
    H_Start -. "Create Profile" .-> CRUD
    H_Settings -. "Update Profile" .-> CRUD
    H_History -. "Fetch 10 Logs" .-> CRUD
    H_Export -. "Fetch History for CSV" .-> CRUD
    S_PhotoFlow -. "Save Meal Log" .-> CRUD
    S_Freemium -. "Check Free Tier Usage" .-> CRUD
    
    CRUD --> DB_Engine
    DB_Engine --> Models
    Models --> PostgreSQL
````
