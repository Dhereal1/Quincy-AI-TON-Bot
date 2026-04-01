# Quincy Telegram Bot

Production-ready Telegram bot for TON communication workflows, designed for webhook deployment on Vercel.

## Architecture

The app is now split into clear runtime layers:

- `index.py`: Vercel entry point
- `app/routes.py`: Flask routes for webhook and cron execution
- `app/services/`: Telegram API, AI, TON, and bot orchestration logic
- `app/storage/alerts.py`: SQLite-backed alert storage with locking and atomic writes
- `main.py`: local development runner

## Security Model

The app fails to start if any required secret is missing.

Required environment variables:

- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather
- `TELEGRAM_WEBHOOK_SECRET`: exact secret Telegram must send in `X-Telegram-Bot-Api-Secret-Token`
- `CRON_SECRET`: bearer token required by `/api/check-alerts`
- `GROQ_API_KEY`: Groq API key for rewrite and chat features

Optional environment variables:

- `TONCENTER_API_KEY`: improves TON Center rate limits
- `COINGECKO_API_KEY`: sent as a CoinGecko API header when configured
- `ALERTS_DB_PATH`: SQLite database path
- `LOG_LEVEL`: default `INFO`

## Local Setup

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env`.

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret
CRON_SECRET=your_cron_secret
GROQ_API_KEY=your_groq_api_key
TONCENTER_API_KEY=your_toncenter_key
COINGECKO_API_KEY=your_coingecko_key
ALERTS_DB_PATH=quincy.db
LOG_LEVEL=INFO
```

3. Run locally.

```bash
python main.py
```

## Vercel Deployment

This project uses a webhook-only execution model. It does not start polling loops, background threads, or long-running workers.

### Deploy

1. Import the repository into Vercel.
2. Add the required environment variables in the Vercel project settings.
3. Keep `index.py` as the serverless entry point.
4. Deploy.

### Configure Telegram Webhook

After deployment, set the webhook URL and secret with Bot API:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://<your-deployment>.vercel.app/api/telegram-webhook\",\"secret_token\":\"<TELEGRAM_WEBHOOK_SECRET>\"}"
```

### Cron Alerts

`vercel.json` is configured to call:

- `GET /api/check-alerts`

Your cron caller must send:

```text
Authorization: Bearer <CRON_SECRET>
```

If you use Vercel Cron Jobs, configure the cron request so it includes the bearer token. If that is not possible in your plan or setup, front this route with a scheduler that can send headers.

## Runtime Notes

- No `parse_mode` is used. User text and LLM output are sent as plain text to avoid formatting injection.
- Alert data is stored in SQLite using transactions and a process lock.
- Default SQLite path on Vercel is `/tmp/quincy.db`.

Important: `/tmp` on Vercel is ephemeral. This implementation is safe and atomic within a running instance, but long-term durable alert storage still requires an external database if you need persistence across cold starts and instance replacement.

## Endpoints

- `GET /`: service metadata
- `GET /api/health`: health check
- `POST /api/telegram-webhook`: Telegram update handler, requires `X-Telegram-Bot-Api-Secret-Token`
- `GET /api/check-alerts`: alert evaluation endpoint, requires `Authorization: Bearer <CRON_SECRET>`

## Commands

- `/start` or `/dashboard`
- `/help`
- `/price`
- `/alert <target_price>`
- `/rewrite` used as a reply to another message

Users can also paste a TON address for wallet inspection.

## Verification

Basic static verification:

```bash
python -m py_compile index.py main.py app\__init__.py app\config.py app\routes.py app\storage\alerts.py app\services\ai_service.py app\services\message_service.py app\services\telegram_api.py app\services\ton_service.py
```

## Production Checklist

- Set all required environment variables
- Configure the Telegram webhook secret token
- Protect cron calls with `Authorization: Bearer <CRON_SECRET>`
- Replace SQLite with external persistent storage if you need durable alerts on Vercel
