# Project Setup Prompt

## Context

I'm building a personal FastAPI monorepo that will serve as the backend for multiple Telegram bot agents. Each bot handles a different task (podcast summarization, research, etc.) and they all share a common Postgres database, shared LLM utilities (Anthropic Claude via LangChain), and a shared Telegram helper layer.

Some bots are **reactive** (respond to messages I send them, like the podcast bot), while others are **proactive** (reach out to me on a schedule with prompts/check-ins, like a nutrition tracker or social accountability bot). Proactive bots use a scheduler to send me messages at configured times and then handle my replies via webhooks.

This will be deployed on a single EC2 instance with Postgres installed locally on the same box. It's a personal project — I'm the only user. I'll use Caddy as a reverse proxy for HTTPS in production.

## What I need you to scaffold

Set up a clean, well-structured FastAPI project with the following:

### Project structure

```
app/
├── main.py                    # FastAPI app factory, include all routers
├── config.py                  # Pydantic Settings for env-based config
├── db/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy declarative base + shared models
│   └── session.py             # Async session factory, get_db dependency
├── common/
│   ├── __init__.py
│   ├── llm.py                 # Shared LangChain/Anthropic Claude client setup
│   ├── telegram.py            # Telegram webhook helpers (send_message, parse_update, etc.)
│   ├── scheduler.py           # APScheduler setup, lifespan integration
│   └── audio.py               # Placeholder for transcription utilities (Deepgram/AssemblyAI)
├── bots/
│   ├── __init__.py
│   ├── podcast/
│   │   ├── __init__.py
│   │   ├── router.py          # Webhook handler: manual URLs + "yes" replies to new episode alerts
│   │   ├── agent.py           # LangChain agent logic for podcast summarization
│   │   ├── feeds.py           # RSS feed checker, list of followed podcasts
│   │   ├── scheduler.py       # Periodic job to check RSS feeds for new episodes
│   │   └── models.py          # Podcast-specific DB models (episodes, summaries, etc.)
│   ├── nutrition/
│   │   ├── __init__.py
│   │   ├── router.py          # Webhook handler for replies to nutrition prompts
│   │   ├── scheduler.py       # Schedule config (e.g. daily at 6pm)
│   │   └── models.py          # Food log entries (prompt_sent_at, response, etc.)
│   └── social/
│       ├── __init__.py
│       ├── router.py          # Webhook handler for replies to social prompts
│       ├── scheduler.py       # Schedule config (every Sunday at 9am)
│       └── models.py          # Weekly social plans/reflections
└── webhooks/
    ├── __init__.py
    └── telegram.py            # Central Telegram webhook receiver that routes to the correct bot
tests/
├── conftest.py
├── test_health.py
pyproject.toml                 # Use poetry or uv — include all dependencies
Dockerfile
docker-compose.yml             # FastAPI app + Postgres for local dev
.env.example
README.md
```

### Tech stack and dependencies

- **Python 3.12+**
- **FastAPI** with async throughout
- **SQLAlchemy 2.0+** with async engine (asyncpg)
- **LangChain + langchain-anthropic** for Claude integration
- **python-telegram-bot** or just raw httpx calls to Telegram Bot API (prefer httpx for simplicity since we're webhook-based, not polling)
- **httpx** as the async HTTP client
- **Pydantic Settings** for configuration (.env based)
- **feedparser** for parsing podcast RSS feeds
- **APScheduler** (`apscheduler[asyncio]`) for scheduled/proactive bot messages
- **Docker + docker-compose** for local dev (Postgres container + app container)

### Configuration (.env.example)

Include placeholders for:
- `DATABASE_URL` (async postgres URL)
- `ANTHROPIC_API_KEY`
- `TELEGRAM_PODCAST_BOT_TOKEN` (one per bot, extensible pattern)
- `TELEGRAM_NUTRITION_BOT_TOKEN`
- `TELEGRAM_SOCIAL_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_BASE_URL` (the public HTTPS URL)
- `OWNER_CHAT_ID` (your Telegram chat ID — used by proactive bots to know where to send messages)
- `TIMEZONE` (e.g. `America/New_York` — for scheduling prompts at the right local time)
- `PODCAST_FEED_URLS` (comma-separated RSS feed URLs for followed podcasts)
- `PODCAST_CHECK_INTERVAL_MINUTES` (how often to check for new episodes, e.g. `30`)
- `DEEPGRAM_API_KEY` or `ASSEMBLYAI_API_KEY`
- `ENVIRONMENT` (local/production)
- `LOG_LEVEL`

### Key implementation details

1. **config.py**: Use `pydantic_settings.BaseSettings` with `.env` file support. Group related settings logically.

2. **db/session.py**: Create an async engine and async sessionmaker. Provide a `get_db` async generator dependency for FastAPI. Use `Base.metadata.create_all()` on startup to auto-create tables (no migration tool needed — just modify models and recreate tables during development).

3. **db/models.py**: Set up the declarative base. Include a `BaseModel` mixin with `id` (UUID), `created_at`, `updated_at` columns that all models inherit from.

4. **common/telegram.py**: 
   - A helper function to send messages back to a chat via the Telegram API using httpx
   - A helper to parse incoming Telegram webhook updates
   - A function to register/set webhooks with Telegram on app startup
   - Support for sending "typing" action and long messages (Telegram has a 4096 char limit)

5. **common/llm.py**:
   - Initialize a `ChatAnthropic` instance from langchain-anthropic
   - Expose a simple `async def ask_claude(prompt: str, system: str = None) -> str` helper
   - Keep it simple but extensible for agents later

6. **common/audio.py**:
   - Placeholder with a `transcribe_audio(url: str) -> str` function signature
   - Add a TODO comment noting this will integrate with Deepgram or AssemblyAI

7. **common/scheduler.py**:
   - Initialize an `AsyncIOScheduler` from APScheduler
   - Provide a `start_scheduler` / `stop_scheduler` pair for FastAPI lifespan
   - Each proactive bot registers its jobs during app startup by calling a shared `register_job` helper
   - Use the `TIMEZONE` setting for all cron triggers

8. **webhooks/telegram.py**:
   - Single POST endpoint that receives all Telegram webhook updates
   - Routes to the correct bot handler based on the URL path or bot token
   - Pattern: `POST /webhooks/telegram/{bot_name}`

9. **bots/podcast/feeds.py**:
   - Parse RSS feeds using `feedparser`
   - For each configured feed, extract the latest episode title, audio URL, and publish date
   - Compare against stored episodes to detect new ones
   - Return a list of new (unseen) episodes

10. **bots/podcast/scheduler.py**:
    - Register an interval job (every `PODCAST_CHECK_INTERVAL_MINUTES`, e.g. 30 min)
    - On each run, call `feeds.py` to check for new episodes
    - For each new episode, send a Telegram message to `OWNER_CHAT_ID`: "{Podcast Name} just dropped a new episode: {Episode Title}. Want me to generate the summary?"
    - Save the episode to the DB with status `notified` so it's not re-notified

11. **bots/podcast/router.py**:
    - Handle two types of incoming messages:
      1. **A URL** — manual submission, kick off summarization directly
      2. **A "yes" reply** — find the most recent `notified` episode and kick off summarization for it
    - Summarization background task:
      1. Sends a "working on it..." reply
      2. Downloads/transcribes the podcast audio
      3. Sends the transcript to Claude for summarization
      4. Sends the summary back to the user via Telegram
    - Use FastAPI `BackgroundTasks` for the async processing

12. **bots/podcast/agent.py**:
    - LangChain agent or chain that takes a transcript and returns a TL;DR
    - System prompt should instruct Claude to provide a concise summary with key topics, main arguments, and notable quotes

13. **bots/podcast/models.py**:
    - `PodcastEpisode` model: feed_url, episode_title, audio_url, published_at, transcript, summary, telegram_chat_id, status (notified/pending/transcribing/summarizing/complete/failed)
    - `PodcastFeed` model (optional, could also just be config): name, rss_url, last_checked_at

12. **bots/nutrition/scheduler.py**:
    - Register a daily cron job (e.g. 6pm local time)
    - Job sends a message to `OWNER_CHAT_ID` via the nutrition bot: "What did you eat today?"
    - Store a `NutritionEntry` record with `prompt_sent_at` so the reply handler knows a prompt is active

13. **bots/nutrition/router.py**:
    - Webhook handler for incoming replies
    - When a message comes in, save it as the response to the most recent unanswered prompt
    - Simple — no LLM processing needed, just log the response

14. **bots/nutrition/models.py**:
    - `NutritionEntry` model: prompt_sent_at, response_text, responded_at

15. **bots/social/scheduler.py**:
    - Register a weekly cron job (every Sunday at 9am local time)
    - Job sends a message to `OWNER_CHAT_ID` via the social bot: "What are your social plans for this week? Reminder that your social muscles can be exercised just like your software engineering knowledge — how are you going to exercise those muscles this week?"
    - Store a `SocialEntry` record with `prompt_sent_at`

16. **bots/social/router.py**:
    - Webhook handler for incoming replies
    - Save the response to the most recent unanswered prompt

17. **bots/social/models.py**:
    - `SocialEntry` model: prompt_sent_at, response_text, responded_at

18. **main.py**:
    - App factory pattern
    - Include a `/health` endpoint
    - Register all bot routers (podcast, nutrition, social)
    - On startup: register Telegram webhooks for all bots, start the APScheduler and register scheduled jobs for proactive bots
    - On shutdown: stop the scheduler gracefully
    - Include CORS middleware (for potential future web UIs)

19. **Dockerfile**: Multi-stage build, run with uvicorn

20. **docker-compose.yml**: App + Postgres, with volume for Postgres data persistence

### Code style

- Type hints everywhere
- Async/await throughout (no sync database calls)
- Docstrings on public functions
- Keep it clean but don't over-abstract — this is a personal project, not enterprise software
- Use `loguru` or standard `logging` for structured logs

### What NOT to do

- Don't set up authentication/API keys on endpoints — it's just me
- Don't add rate limiting
- Don't over-engineer error handling — basic try/except with logging is fine
- Don't add complex dependency injection beyond FastAPI's built-in `Depends`
- Don't use polling for Telegram — webhooks for inbound messages, scheduler for outbound prompts

After scaffolding, give me a summary of what was created and instructions for:
1. How to start the local dev environment with docker-compose
2. How to create a Telegram bot via BotFather and configure the token (need 3 bots: podcast, nutrition, social)
4. How to find your Telegram chat ID for `OWNER_CHAT_ID`
5. How to use ngrok to test webhooks locally
6. How to test the scheduled bots (trigger a job manually to verify it sends a message)