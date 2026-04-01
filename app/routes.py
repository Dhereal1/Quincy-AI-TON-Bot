import logging

from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


def _json_error(message: str, status_code: int):
    return jsonify({"ok": False, "error": message}), status_code


def _require_bearer(expected_secret: str) -> bool:
    auth_header = request.headers.get("Authorization", "")
    return auth_header == f"Bearer {expected_secret}"


def register_routes(app: Flask) -> None:
    @app.get("/")
    def home():
        return jsonify(
            {
                "service": "Quincy Telegram Bot",
                "status": "ok",
                "mode": "webhook",
                "webhook_path": "/api/telegram-webhook",
                "alerts_path": "/api/check-alerts",
            }
        )

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/telegram-webhook")
    def telegram_webhook():
        config = app.config["QUINCY_CONFIG"]
        telegram_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if telegram_secret != config.telegram_webhook_secret:
            return _json_error("unauthorized", 401)

        update = request.get_json(silent=True)
        if not update:
            return _json_error("invalid_payload", 400)

        try:
            app.extensions["quincy_service"].process_update(
                update=update,
                telegram_api=app.extensions["telegram_api"],
            )
            return jsonify({"ok": True})
        except Exception:
            logger.exception("Failed to process Telegram webhook update")
            return _json_error("internal_error", 500)

    @app.get("/api/check-alerts")
    def check_alerts():
        config = app.config["QUINCY_CONFIG"]
        if not _require_bearer(config.cron_secret):
            return _json_error("unauthorized", 401)

        try:
            result = app.extensions["quincy_service"].run_alert_check(
                telegram_api=app.extensions["telegram_api"]
            )
            return jsonify({"ok": True, **result})
        except Exception:
            logger.exception("Failed to execute alert check")
            return _json_error("internal_error", 500)
