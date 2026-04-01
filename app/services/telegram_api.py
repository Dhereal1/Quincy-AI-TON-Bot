import logging

import requests

logger = logging.getLogger(__name__)


class TelegramApi:
    def __init__(self, bot_token: str):
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._session = requests.Session()

    def send_message(self, message) -> dict:
        payload = {
            "chat_id": message.chat_id,
            "text": self._truncate(message.text),
        }
        if message.reply_markup:
            payload["reply_markup"] = message.reply_markup
        if message.reply_to_message_id:
            payload["reply_to_message_id"] = message.reply_to_message_id

        response = self._session.post(f"{self._base_url}/sendMessage", json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {data}")
        return data

    def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        response = self._session.post(
            f"{self._base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": self._truncate(text, 200)},
            timeout=15,
        )
        response.raise_for_status()

    def clear_inline_keyboard(self, chat_id: int | None, message_id: int | None) -> None:
        if not chat_id or not message_id:
            return
        response = self._session.post(
            f"{self._base_url}/editMessageReplyMarkup",
            json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            timeout=15,
        )
        if not response.ok:
            logger.warning("Failed to clear inline keyboard", extra={"chat_id": chat_id, "message_id": message_id})

    @staticmethod
    def _truncate(text: str, max_length: int = 4000) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 16] + "\n\n[truncated]"
