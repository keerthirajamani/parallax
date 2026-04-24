import logging
import os
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from dhanhq import dhanhq

from src.dhan.account_registry import load_accounts
from src.dhan.order_logger import log_executed_orders
from src.utils.common_utils import get_token_from_s3
from src.utils.position_sizer import flatten_signals, compute_qty

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")

MARKET_OPEN  = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)


def _is_market_open() -> bool:
    now = datetime.now(IST).time()
    return MARKET_OPEN <= now <= MARKET_CLOSE


def place_orders(signals: list[dict]) -> dict:
    """
    Fan out signals to every enabled Dhan account.
    Returns a summary keyed by account_id.
    """
    if not _is_market_open() or 1:
        now_str = datetime.now(IST).strftime("%H:%M:%S")
        print(f"place_orders: market is closed at {now_str} IST, skipping")
        return {"status": "skipped", "reason": "market_closed"}

    accounts = load_accounts(broker="dhan")
    results = {}

    for account in accounts:
        account_id = account["account_id"]
        print(f"place_orders: processing account={account_id}")
        try:
            summary = _place_orders_for_account(account, signals)
            results[account_id] = {"status": "ok", "orders_placed": summary}
        except Exception as exc:
            print(f"place_orders: account={account_id} failed: {exc}")
            results[account_id] = {"status": "error", "error": str(exc)}

    return results


def _place_orders_for_account(account: dict, signals: list[dict]) -> list[dict]:
    account_id  = account["account_id"]
    client_id   = account["client_id"]
    token_key   = account["token_s3_key"]
    max_capital = float(account.get("max_trade_capital", 10000))

    access_token = get_token_from_s3(S3_BUCKET, token_key)
    dhan_client  = dhanhq(client_id, access_token)

    executed_orders = []

    executed_orders += _execute(dhan_client, account_id, signals, "buy",  max_capital)
    executed_orders += _execute(dhan_client, account_id, signals, "sell", max_capital)

    log_executed_orders(executed_orders, bucket=S3_BUCKET, account_id=account_id)
    return executed_orders


def _execute(dhan_client, account_id: str, signals: list[dict], side: str, max_capital: float) -> list[dict]:
    flat = flatten_signals(signals, signal_type=side)
    print(f"account={account_id} side={side} signals={len(flat)}")

    transaction_type = dhan_client.BUY if side == "buy" else dhan_client.SELL
    executed = []

    for sig in flat:
        qty = compute_qty(sig["close"], max_capital=max_capital)

        if qty <= 0:
            print(f"account={account_id} skipping {sig['symbol']} — insufficient capital")
            continue

        print(
            f"account={account_id} placing {side.upper()} {sig['symbol']} | "
            f"indicator={sig['indicator']} | qty={qty} | "
            f"entry={sig['close']:.2f} | sl={sig['tsl']:.2f}"
        )

        try:
            resp = dhan_client.place_order(
                security_id=sig["security_id"],
                exchange_segment=sig["exchange"],
                transaction_type=transaction_type,
                quantity=qty,
                order_type=dhan_client.MARKET,
                product_type=dhan_client.CNC,
                price=0,
            )

            if resp.get("status") == "failure":
                print(f"account={account_id} order FAILED {sig['symbol']}: {resp.get('remarks')}")
                continue

            order_id = resp.get("data", {}).get("orderId", "")
            print(f"account={account_id} order_id={order_id} symbol={sig['symbol']} side={side}")

            executed.append({
                "symbol":         sig["symbol"],
                "security_id":    sig["security_id"],
                "exchange":       sig["exchange"],
                "indicator":      sig["indicator"],
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
