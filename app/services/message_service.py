import logging
import re
from dataclasses import dataclass

from app.storage.alerts import Alert, AlertStore

logger = logging.getLogger(__name__)

USDT_MASTER_ADDRESS = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"
TON_ADDRESS_REGEX = re.compile(r"^[EUK0][Qq][A-Za-z0-9_-]{46}$")


@dataclass(frozen=True)
class OutboundMessage:
    chat_id: int
    text: str
    reply_markup: dict | None = None
    reply_to_message_id: int | None = None


class QuincyService:
    def __init__(self, ai_service, ton_service, alert_store: AlertStore):
        self._ai_service = ai_service
        self._ton_service = ton_service
        self._alert_store = alert_store

    def process_update(self, update: dict, telegram_api) -> None:
        if "callback_query" in update:
            self._process_callback_query(update["callback_query"], telegram_api)
            return

        message = update.get("message")
        if not message or "text" not in message:
            return

        self._process_message(message, telegram_api)

    def _process_message(self, message: dict, telegram_api) -> None:
        chat_id = message["chat"]["id"]
        text = message["text"].strip()
        message_id = message.get("message_id")

        if text.startswith("/start") or text.startswith("/dashboard"):
            telegram_api.send_message(self.build_dashboard(chat_id))
            return

        if text.startswith("/help"):
            telegram_api.send_message(self.build_help(chat_id))
            return

        if text.startswith("/price"):
            telegram_api.send_message(self.build_price_message(chat_id))
            return

        if text.startswith("/alert"):
            telegram_api.send_message(self.handle_alert_command(chat_id, text, message_id))
            return

        if text.startswith("/rewrite"):
            telegram_api.send_message(self.handle_rewrite_command(message))
            return

        if text.lower() in {"hi", "hello", "hey", "gm", "good morning", "good afternoon", "good evening"}:
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text=(
                        "Hi. I am Quincy, your TON communication assistant.\n\n"
                        "Reply to any message with /rewrite to improve it.\n"
                        "Use /start to open the dashboard."
                    ),
                    reply_to_message_id=message_id,
                )
            )
            return

        if TON_ADDRESS_REGEX.match(text):
            telegram_api.send_message(self.build_wallet_report(chat_id, text, message_id))
            return

        telegram_api.send_message(self.handle_ai_chat(chat_id, text, message_id))

    def _process_callback_query(self, callback_query: dict, telegram_api) -> None:
        data = callback_query.get("data", "")
        callback_id = callback_query["id"]
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        callback_message_id = message.get("message_id")
        replied_message = message.get("reply_to_message")

        if data == "how_to_rewrite":
            telegram_api.answer_callback_query(callback_id, "Instructions sent.")
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text=(
                        "How to improve messages:\n"
                        "1. Reply to a text message with /rewrite.\n"
                        "2. Choose a rewrite style.\n"
                        "3. Quincy returns a safer, cleaner version."
                    ),
                )
            )
            return

        if data == "draft_announcement":
            telegram_api.answer_callback_query(callback_id, "Template sent.")
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text=(
                        "Announcement template:\n"
                        "We are excited to announce [EVENT] on [DATE] at [TIME] UTC.\n"
                        "Key details: [DETAILS].\n"
                        "Next steps: [ACTION]."
                    ),
                )
            )
            return

        if data == "safety_tips":
            telegram_api.answer_callback_query(callback_id, "Safety tips sent.")
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text=(
                        "Crypto safety tips:\n"
                        "- Never share seed phrases, private keys, or recovery words.\n"
                        "- Ignore requests to send funds to verify a wallet.\n"
                        "- Treat urgency and guaranteed-profit claims as red flags."
                    ),
                )
            )
            return

        if data == "check_price":
            telegram_api.answer_callback_query(callback_id, "Price refreshed.")
            telegram_api.send_message(self.build_price_message(chat_id))
            return

        if data == "check_wallet":
            telegram_api.answer_callback_query(callback_id, "Send a wallet address.")
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text="Paste a TON wallet address to get a balance and recent transaction summary.",
                )
            )
            return

        if data == "set_alert_info":
            telegram_api.answer_callback_query(callback_id, "Instructions sent.")
            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text="Use /alert <target_price>. Example: /alert 3.50",
                )
            )
            return

        if data.startswith("rewrite:"):
            telegram_api.answer_callback_query(callback_id, "Rewriting...")
            if not replied_message or not replied_message.get("text"):
                telegram_api.send_message(
                    OutboundMessage(
                        chat_id=chat_id,
                        text="Cannot rewrite this message because the original text is unavailable.",
                    )
                )
                return

            original_text = replied_message["text"]
            safety = self.check_crypto_safety(original_text)
            if safety["is_dangerous"]:
                telegram_api.send_message(
                    OutboundMessage(
                        chat_id=chat_id,
                        text=(
                            "Security warning:\n"
                            f"{safety['warning']}\n\n"
                            "Rewrite blocked for user protection."
                        ),
                        reply_to_message_id=replied_message.get("message_id"),
                    )
                )
                telegram_api.clear_inline_keyboard(chat_id, callback_message_id)
                return

            rewrite_type = data.split(":", 1)[1]
            try:
                rewritten = self._ai_service.rewrite_text(original_text, rewrite_type)
            except Exception:
                logger.exception("Rewrite request failed")
                telegram_api.send_message(
                    OutboundMessage(chat_id=chat_id, text="The AI rewrite service is unavailable. Try again later.")
                )
                return

            response_text = f"Quincy rewrite:\n\n{rewritten}"
            if safety["has_warning"]:
                response_text += f"\n\nWarning: {safety['warning']}"

            telegram_api.send_message(
                OutboundMessage(
                    chat_id=chat_id,
                    text=response_text,
                    reply_to_message_id=replied_message.get("message_id"),
                )
            )
            telegram_api.clear_inline_keyboard(chat_id, callback_message_id)
            return

        telegram_api.answer_callback_query(callback_id, "Unsupported action.")

    def build_dashboard(self, chat_id: int) -> OutboundMessage:
        price = self._ton_service.get_ton_price()
        price_text = f"${price:.2f}" if price else "Unavailable"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Improve Message", "callback_data": "how_to_rewrite"},
                    {"text": "Draft Announcement", "callback_data": "draft_announcement"},
                ],
                [{"text": "Safety Tips", "callback_data": "safety_tips"}],
                [
                    {"text": "Check Wallet", "callback_data": "check_wallet"},
                    {"text": "TON Price", "callback_data": "check_price"},
                ],
                [{"text": "Price Alert", "callback_data": "set_alert_info"}],
            ]
        }
        return OutboundMessage(
            chat_id=chat_id,
            text=(
                "Quincy Communication Hub\n\n"
                "Main tools:\n"
                "- Improve messages\n"
                "- Draft announcements\n"
                "- Flag risky crypto language\n\n"
                f"TON price: {price_text}\n"
                "Choose an option below."
            ),
            reply_markup=keyboard,
        )

    def build_help(self, chat_id: int) -> OutboundMessage:
        return OutboundMessage(
            chat_id=chat_id,
            text=(
                "Quincy commands:\n"
                "/start or /dashboard - open the dashboard\n"
                "/price - check the current TON price\n"
                "/alert <price> - set a price alert\n"
                "/rewrite - reply to a message and choose a rewrite style\n\n"
                "You can also paste a TON wallet address to get a wallet summary."
            ),
        )

    def build_price_message(self, chat_id: int) -> OutboundMessage:
        price = self._ton_service.get_ton_price()
        if not price:
            return OutboundMessage(chat_id=chat_id, text="TON price is currently unavailable.")
        return OutboundMessage(chat_id=chat_id, text=f"TON price: ${price:.2f} USD")

    def handle_alert_command(self, chat_id: int, text: str, message_id: int | None) -> OutboundMessage:
        parts = text.split()
        if len(parts) < 2:
            return OutboundMessage(chat_id=chat_id, text="Usage: /alert <target_price>", reply_to_message_id=message_id)

        try:
            target_price = float(parts[1])
        except ValueError:
            return OutboundMessage(chat_id=chat_id, text="Invalid price format. Example: /alert 2.50", reply_to_message_id=message_id)

        if target_price <= 0:
            return OutboundMessage(chat_id=chat_id, text="Price must be greater than zero.", reply_to_message_id=message_id)

        current_price = self._ton_service.get_ton_price()
        if not current_price:
            return OutboundMessage(chat_id=chat_id, text="Unable to fetch the current TON price right now.", reply_to_message_id=message_id)

        direction = "above" if target_price > current_price else "below"
        direction_text = "rises to" if direction == "above" else "drops to"

        self._alert_store.upsert_alert(
            Alert(
                chat_id=chat_id,
                target_price=target_price,
                initial_price=current_price,
                direction=direction,
            )
        )

        return OutboundMessage(
            chat_id=chat_id,
            text=(
                f"Alert set.\n"
                f"You will be notified when TON {direction_text} ${target_price:.2f}.\n"
                f"Current price: ${current_price:.2f}"
            ),
            reply_to_message_id=message_id,
        )

    def handle_rewrite_command(self, message: dict) -> OutboundMessage:
        reply_to_message = message.get("reply_to_message")
        chat_id = message["chat"]["id"]
        message_id = message.get("message_id")
        if not reply_to_message or not reply_to_message.get("text"):
            return OutboundMessage(
                chat_id=chat_id,
                text="Reply to a text message with /rewrite, then choose a rewrite style.",
                reply_to_message_id=message_id,
            )

        keyboard = {
            "inline_keyboard": [
                [{"text": "Fix Grammar", "callback_data": "rewrite:fix_grammar"}],
                [{"text": "Make Professional", "callback_data": "rewrite:make_pro"}],
                [{"text": "Announcement Style", "callback_data": "rewrite:make_announcement"}],
                [{"text": "Simplify", "callback_data": "rewrite:simplify"}],
            ]
        }
        return OutboundMessage(
            chat_id=chat_id,
            text="Choose a rewrite style.",
            reply_markup=keyboard,
            reply_to_message_id=reply_to_message.get("message_id"),
        )

    def build_wallet_report(self, chat_id: int, address: str, message_id: int | None) -> OutboundMessage:
        try:
            price = self._ton_service.get_ton_price()
            ton_balance = self._ton_service.get_ton_balance(address)
            usdt_balance = self._ton_service.get_usdt_balance(address, USDT_MASTER_ADDRESS)
            transactions = self._ton_service.get_last_transactions(address)
        except ValueError:
            return OutboundMessage(
                chat_id=chat_id,
                text="Invalid TON address. Please paste a valid user-friendly TON wallet address.",
                reply_to_message_id=message_id,
            )
        except Exception:
            logger.exception("Wallet lookup failed")
            return OutboundMessage(
                chat_id=chat_id,
                text="Wallet lookup failed. Please verify the address and try again later.",
                reply_to_message_id=message_id,
            )

        if ton_balance is None:
            return OutboundMessage(
                chat_id=chat_id,
                text="Wallet lookup failed. Please verify the address and try again later.",
                reply_to_message_id=message_id,
            )

        ton_value_usd = round(ton_balance * price, 2) if price else 0.0
        total_value_usd = ton_value_usd + usdt_balance
        tx_text = "\n".join(transactions) if transactions else "No recent transactions found."

        lines = [
            "Quincy Wallet Report",
            "",
            f"Address: {address}",
            f"Portfolio value: ${total_value_usd:.2f} USD",
            f"TON balance: {ton_balance:.4f} TON",
            f"USDT balance: {usdt_balance:.2f} USDT",
            "",
            "Last transactions:",
            tx_text,
        ]
        if price:
            lines.append("")
            lines.append(f"TON price: ${price:.2f} USD")

        return OutboundMessage(
            chat_id=chat_id,
            text="\n".join(lines),
            reply_to_message_id=message_id,
        )

    def handle_ai_chat(self, chat_id: int, text: str, message_id: int | None) -> OutboundMessage:
        try:
            reply = self._ai_service.chat_reply(text)
            return OutboundMessage(chat_id=chat_id, text=reply, reply_to_message_id=message_id)
        except Exception:
            logger.exception("AI chat request failed")
            return OutboundMessage(
                chat_id=chat_id,
                text="The AI service is currently unavailable. Try again later or use /help.",
                reply_to_message_id=message_id,
            )

    def run_alert_check(self, telegram_api) -> dict:
        alerts = self._alert_store.list_alerts()
        if not alerts:
            return {"checked": 0, "triggered": 0, "price": None}

        current_price = self._ton_service.get_ton_price()
        if not current_price:
            return {"checked": len(alerts), "triggered": 0, "price": 0, "error": "price_unavailable"}

        triggered_chat_ids: list[int] = []
        for alert in alerts:
            should_trigger = (
                alert.direction == "above" and alert.initial_price < alert.target_price <= current_price
            ) or (
                alert.direction == "below" and alert.initial_price > alert.target_price >= current_price
            )

            if not should_trigger:
                continue

            try:
                telegram_api.send_message(
                    OutboundMessage(
                        chat_id=alert.chat_id,
                        text=(
                            "Price alert.\n"
                            f"TON crossed ${alert.target_price:.2f}.\n"
                            f"Current price: ${current_price:.2f}\n"
                            f"Alert set at: ${alert.initial_price:.2f}"
                        ),
                    )
                )
                triggered_chat_ids.append(alert.chat_id)
            except Exception:
                logger.exception("Failed to send price alert", extra={"chat_id": alert.chat_id})

        self._alert_store.delete_alerts(triggered_chat_ids)
        return {"checked": len(alerts), "triggered": len(triggered_chat_ids), "price": current_price}

    @staticmethod
    def check_crypto_safety(text: str) -> dict:
        text_lower = text.lower()
        dangerous_phrases = [
            "seed phrase",
            "mnemonic",
            "private key",
            "recovery phrase",
            "12 word",
            "24 word",
            "secret phrase",
            "wallet backup",
            "send me your",
            "share your key",
            "give me access",
            "verify your wallet by sending",
            "unlock wallet by transferring",
        ]
        warning_phrases = [
            "buy now",
            "act fast",
            "limited time",
            "urgent",
            "send ton to",
            "transfer to this address",
            "guaranteed profit",
            "double your",
            "risk free",
            "can't lose",
        ]

        for phrase in dangerous_phrases:
            if phrase in text_lower:
                return {
                    "is_dangerous": True,
                    "has_warning": True,
                    "warning": "This message requests sensitive wallet information. Never share seed phrases or private keys.",
                }

        for phrase in warning_phrases:
            if phrase in text_lower:
                return {
                    "is_dangerous": False,
                    "has_warning": True,
                    "warning": "Be cautious of urgency-based or guaranteed-return language in crypto messages.",
                }

        return {"is_dangerous": False, "has_warning": False, "warning": None}
