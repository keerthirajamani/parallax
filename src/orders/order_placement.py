import logging
import os
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from dhanhq import dhanhq
# from kiteconnect import KiteConnect

from src.brokers import dhan as dhan_broker
# from src.orders.brokers import zerodha as zerodha_broker
from src.orders.account_registry import load_accounts
from src.orders.order_logger import log_executed_orders
from src.utils.common_utils import get_token_from_s3
from src.utils.position_sizer import flatten_signals, compute_qty

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")

US_ENTITIES = {"us_equity", "us_index"}

INDIA_OPEN  = dt_time(9, 15)
INDIA_CLOSE = dt_time(15, 30)

US_OPEN  = dt_time(9, 30)
US_CLOSE = dt_time(16, 0)
EST = ZoneInfo("America/New_York")


def _is_market_open(entity: str) -> bool:
    if entity.lower() in US_ENTITIES:
        now = datetime.now(EST).time()
        return US_OPEN <= now <= US_CLOSE
    now = datetime.now(IST).time()
    return INDIA_OPEN <= now <= INDIA_CLOSE


# ── broker factory ────────────────────────────────────────────────────────────

def _build_client(account: dict, token: str):
    """Return the broker client instance based on account's broker field."""
    broker = account.get("broker")

    if broker == "dhan":
        return dhanhq(account["client_id"], token)

    # if broker == "zerodha":
    #     kite = KiteConnect(api_key=account["api_key"])
    #     kite.set_access_token(token)
        
    #     return kite

    raise ValueError(f"Unsupported broker: {broker!r} for account={account['account_id']}")


def _prefetch_clients(accounts: list[dict]) -> dict[str, object]:
    """
    Fetch all tokens from S3 and build broker clients upfront.
    One S3 call per account, before any order is placed.
    """
    clients = {}
    for account in accounts:
        account_id = account["account_id"]
        token = get_token_from_s3(S3_BUCKET, account["token_s3_key"])
        clients[account_id] = _build_client(account, token)
        print(f"place_orders: client ready account={account_id} broker={account['broker']}")
    return clients


# ── broker-specific order dispatch ───────────────────────────────────────────

_BROKER_MODULES = {
    "dhan": dhan_broker,
    # "zerodha": zerodha_broker,
}


def _place_order(client, broker: str, sig: dict, side: str, qty: int) -> str:
    module = _BROKER_MODULES.get(broker)
    if module is None:
        raise ValueError(f"Unsupported broker: {broker!r}")
    return module.place_order(client, sig, side, qty)


class OrderPlacer:
    def __init__(self, market: str):
        self._market   = market
        self._accounts, self._clients = self._load(market)

    def _load(self, market: str):
        accounts = load_accounts(market=market)
        clients  = _prefetch_clients(accounts)
        print(f"OrderPlacer: loaded {len(accounts)} accounts for market={market}")
        return accounts, clients

    def place_orders(self, signals: list[dict], entity: str) -> dict:
        if not _is_market_open(entity):
            tz = EST if entity.lower() in US_ENTITIES else IST
            print(f"OrderPlacer: market closed at {datetime.now(tz).strftime('%H:%M:%S')} for entity={entity}, skipping")
            return {"status": "skipped", "reason": "market_closed"}

        if not self._accounts:
            print(f"OrderPlacer: no accounts loaded for market={self._market}, skipping")
            return {"status": "skipped", "reason": "no_accounts"}

        print(f"OrderPlacer: entity={entity} market={self._market} accounts={len(self._accounts)}")
        results = {}
        for account in self._accounts:
            account_id = account["account_id"]
            print(f"OrderPlacer: processing account={account_id} broker={account['broker']}")
            try:
                summary = _place_orders_for_account(account, self._clients[account_id], signals, self._market)
                results[account_id] = {"status": "ok", "orders_placed": summary}
            except Exception as exc:
                print(f"OrderPlacer: account={account_id} failed: {exc}")
                results[account_id] = {"status": "error", "error": str(exc)}
        return results


def _resolve_capital(account: dict, market: str) -> float:
    """
    Returns max_trade_capital for the given market.
    Looks up market_config[market] first, falls back to top-level max_trade_capital.
    """
    market_config = account.get("market_config", {})
    if market in market_config:
        return float(market_config[market].get("max_trade_capital"))
    return float(account.get("max_trade_capital"))


def _place_orders_for_account(account: dict, client, signals: list[dict], market: str) -> list[dict]:
    account_id  = account["account_id"]
    broker      = account["broker"]
    max_capital = _resolve_capital(account, market)
    print(f"account={account_id} broker={broker} market={market} max_capital={max_capital}")

    executed_orders  = _execute(client, broker, account_id, signals, "buy",  max_capital)
    # executed_orders += _execute(client, broker, account_id, signals, "sell", max_capital)

    log_executed_orders(executed_orders, bucket=S3_BUCKET, account_id=account_id)
    return executed_orders


def _execute(client, broker: str, account_id: str, signals: list[dict], side: str, max_capital: float) -> list[dict]:
    flat = flatten_signals(signals, signal_type=side)
    if not flat:
        print(f"account={account_id} broker={broker} side={side} — no signals, skipping")
        return []

    print(f"account={account_id} broker={broker} side={side} signals={len(flat)}")
    executed = []

    for sig in flat:
        qty = compute_qty(sig["close"], max_capital=max_capital)

        if qty <= 0:
            print(f"account={account_id} skipping {sig['symbol']} — insufficient capital")
            continue

        print(
            f"account={account_id} broker={broker} placing {side.upper()} {sig['symbol']} | "
            f"indicator={sig['indicator']} | qty={qty} | "
            f"entry={sig['close']:.2f} | sl={sig['tsl']:.2f}"
        )

        try:
            order_id = _place_order(client, broker, sig, side, qty)
            print("order id ", order_id)
            print(f"account={account_id} order_id={order_id} symbol={sig['symbol']} side={side}")

            executed.append({
                "symbol":         sig["symbol"],
                "security_id":    sig["security_id"],
                "exchange":       sig["exchange"],
                "indicator":      sig["indicator"],
                "broker":         broker,
                "side":           side,
                "qty":            qty,
                "entry_price":    sig["close"],
                "stop_loss":      sig["tsl"],
                "target":         0,
                "order_id":       order_id,
                "forever_placed": False,
                "timestamp":      datetime.now(IST).isoformat(),
            })

        except Exception as exc:
            print(f"account={account_id} exception placing {sig['symbol']}: {exc}")
            continue

    return executed