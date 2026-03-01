# Personal Agents

FastAPI monorepo for personal Telegram bot agents: podcast summarizer, nutrition tracker, and social accountability.

## Local Development

```bash
# Install dependencies
uv sync

# Copy and fill in env vars
cp .env.example .env

# Start Postgres + app
docker-compose up --build

# Or run just Postgres and start the app locally
docker-compose up -d postgres
uv run uvicorn app.main:app --reload
```

## Telegram Setup

### 1. Create bots via BotFather

Message [@BotFather](https://t.me/BotFather) on Telegram and create 3 bots:
- Podcast bot
- Nutrition bot
- Social bot

Copy each bot token into `.env`.

### 2. Get your chat ID

Send any message to one of your bots, then visit:

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

Find `"chat": {"id": ...}` in the response — that's your `OWNER_CHAT_ID`.

### 3. Set up ngrok for local webhook testing

```bash
ngrok http 8000
```

Copy the HTTPS URL into `.env` as `TELEGRAM_WEBHOOK_BASE_URL`. Restart the app — it will register webhooks on startup.

## Tests

```bash
# With Postgres running:
uv run pytest
```
