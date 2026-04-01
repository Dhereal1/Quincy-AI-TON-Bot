import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class AppConfig:
    telegram_bot_token: str
    telegram_webhook_secret: str
    cron_secret: str
    groq_api_key: str
    coingecko_api_key: str | None
    toncenter_api_key: str | None
    alerts_db_path: str
    log_level: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        load_dotenv()
        default_db_path = "/tmp/quincy.db" if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") else "quincy.db"
        return cls(
            telegram_bot_token=_require_env("TELEGRAM_BOT_TOKEN"),
            telegram_webhook_secret=_require_env("TELEGRAM_WEBHOOK_SECRET"),
            cron_secret=_require_env("CRON_SECRET"),
            groq_api_key=_require_env("GROQ_API_KEY"),
            coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
            toncenter_api_key=os.getenv("TONCENTER_API_KEY"),
            alerts_db_path=os.getenv("ALERTS_DB_PATH", default_db_path),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
