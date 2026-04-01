import logging

from flask import Flask

from app.config import AppConfig
from app.routes import register_routes
from app.services.ai_service import AiService
from app.services.message_service import QuincyService
from app.services.telegram_api import TelegramApi
from app.services.ton_service import TonService
from app.storage.alerts import AlertStore


def create_app() -> Flask:
    config = AppConfig.from_env()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = Flask(__name__)
    app.config["QUINCY_CONFIG"] = config

    alert_store = AlertStore(config.alerts_db_path)
    telegram_api = TelegramApi(config.telegram_bot_token)
    ton_service = TonService(
        toncenter_api_key=config.toncenter_api_key,
        coingecko_api_key=config.coingecko_api_key,
    )
    ai_service = AiService(config.groq_api_key)
    quincy_service = QuincyService(
        ai_service=ai_service,
        ton_service=ton_service,
        alert_store=alert_store,
    )

    app.extensions["alert_store"] = alert_store
    app.extensions["telegram_api"] = telegram_api
    app.extensions["quincy_service"] = quincy_service

    register_routes(app)
    return app
