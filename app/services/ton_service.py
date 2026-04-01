import logging
import time

import requests

logger = logging.getLogger(__name__)


class TonService:
    def __init__(self, toncenter_api_key: str | None, coingecko_api_key: str | None):
        self._toncenter_api_key = toncenter_api_key
        self._coingecko_api_key = coingecko_api_key
        self._session = requests.Session()
        self._cached_price = 0.0
        self._cached_price_at = 0.0

    def get_ton_price(self) -> float:
        now = time.time()
        if self._cached_price and now - self._cached_price_at < 120:
            return self._cached_price

        headers = {}
        if self._coingecko_api_key:
            headers["x-cg-demo-api-key"] = self._coingecko_api_key

        try:
            response = self._session.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "the-open-network", "vs_currencies": "usd"},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            price = float(data["the-open-network"]["usd"])
            self._cached_price = price
            self._cached_price_at = now
            return price
        except Exception:
            logger.exception("Failed to fetch TON price")
            return self._cached_price

    def get_ton_balance(self, address: str) -> float | None:
        try:
            response = self._session.get(
                "https://toncenter.com/api/v2/getAddressBalance",
                params={"address": address},
                headers=self._toncenter_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok") or "result" not in data:
                return None
            return round(int(data["result"]) / 1_000_000_000, 4)
        except Exception:
            logger.exception("Failed to fetch TON balance")
            return None

    def get_usdt_balance(self, address: str, usdt_master_address: str) -> float:
        try:
            response = self._session.get(
                "https://toncenter.com/api/v3/jetton/wallets",
                params={
                    "owner_address": address,
                    "jetton_address": usdt_master_address,
                    "limit": 1,
                },
                headers=self._toncenter_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            wallets = data.get("jetton_wallets", [])
            if not wallets:
                return 0.0
            return round(int(wallets[0].get("balance", "0")) / 1_000_000, 2)
        except Exception:
            logger.exception("Failed to fetch USDT balance")
            return 0.0

    def get_last_transactions(self, address: str, limit: int = 5) -> list[str]:
        try:
            response = self._session.get(
                "https://toncenter.com/api/v2/getTransactions",
                params={"address": address, "limit": limit},
                headers=self._toncenter_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            transactions = data.get("result", [])
            if not data.get("ok") or not transactions:
                return []

            formatted = []
            for index, tx in enumerate(transactions[:limit], start=1):
                in_msg = tx.get("in_msg", {})
                value = int(in_msg.get("value", "0")) / 1_000_000_000
                destination = in_msg.get("destination", "")
                direction = "IN" if destination == address else "OUT"
                timestamp = tx.get("utime", 0)
                time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp)) if timestamp else "Unknown"
                if value > 0:
                    formatted.append(f"{index}. {direction} {value:.4f} TON at {time_str}")
                else:
                    formatted.append(f"{index}. {direction} smart contract call at {time_str}")
            return formatted
        except Exception:
            logger.exception("Failed to fetch transaction history")
            return []

    def _toncenter_headers(self) -> dict:
        if not self._toncenter_api_key:
            return {}
        return {"X-API-Key": self._toncenter_api_key}
