import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
from dhanhq import dhanhq

from src.dhan.account_registry import load_accounts
from src.dhan.order_logger import log_executed_orders
from src.utils.common_utils import get_token_from_s3
from src.utils.position_sizer import flatten_signals, compute_qty

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")


def place_orders(signals: list[dict]) -> dict:
    """
    Fan out signals to every enabled account.

    Returns a summary keyed by account_id.
    """
    accounts = load_accounts()
    results = {}

    for account in accounts:
        account_id = account["account_id"]
        logger.info("place_orders: processing account=%s", account_id)

        try:
            summary = _place_orders_for_account(account, signals)
            results[account_id] = {"status": "ok", "orders_placed": summary}
        except Exception as exc:
            logger.error("place_orders: account=%s failed: %s", account_id, exc)
            results[account_id] = {"status": "error", "error": str(exc)}

    return results


def _place_orders_for_account(account: dict, signals: list[dict]) -> list[dict]:
    account_id = account["account_id"]
    client_id = account["client_id"]
    token_key = account["token_s3_key"]
    max_capital = float(account.get("max_trade_capital", 10000))

    access_token = get_token_from_s3(S3_BUCKET, token_key)
    dhan_client = dhanhq(client_id, access_token)

    buy_signals = flatten_signals(signals, signal_type="buy")
    logger.info("account=%s buy_signals=%d", account_id, len(buy_signals))

    executed_orders = []

    for sig in buy_signals:
        qty = compute_qty(sig["close"], max_capital=max_capital)

        if qty <= 0:
            logger.info("account=%s skipping %s — insufficient capital", account_id, sig["symbol"])
            continue

        logger.info(
            "account=%s placing BUY %s | indicator=%s | qty=%d | entry=%.2f | sl=%.2f",
            account_id, sig["symbol"], sig["indicator"], qty, sig["close"], sig["tsl"],
        )

        resp = dhan_client.place_order(
            security_id=sig["security_id"],
            exchange_segment=sig["exchange"],
            transaction_type=dhan_client.BUY,
            quantity=qty,
            order_type=dhan_client.MARKET,
            product_type=dhan_client.CNC,
            price=0,
        )
        logger.info("account=%s order_response=%s", account_id, resp)

        order_id = resp.get("data", {}).get("orderId", "")

        executed_orders.append({
            "symbol":         sig["symbol"],
            "security_id":    sig["security_id"],
            "exchange":       sig["exchange"],
            "indicator":      sig["indicator"],
            "qty":            qty,
            "entry_price":    sig["close"],
            "stop_loss":      sig["tsl"],
            "target":         0,
            "order_id":       order_id,
            "forever_placed": False,
            "timestamp":      datetime.now(IST).isoformat(),
        })

    log_executed_orders(executed_orders, bucket=S3_BUCKET, account_id=account_id)
    return executed_orders
