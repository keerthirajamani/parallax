from dhanhq import dhanhq
import os
import sys
import logging
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.common_utils import get_token_from_s3
from src.utils.position_sizer import (
    flatten_signals,
    compute_qty,
)
from src.dhan.order_logger import log_executed_orders

logger = logging.getLogger(__name__)

IST        = ZoneInfo("Asia/Kolkata")
S3_BUCKET  = os.environ.get("BUCKET", "nse-artifacts")
S3_KEY     = "dhan/token.json"

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID", "1107245176")
access_token   = get_token_from_s3(S3_BUCKET, S3_KEY)
dhan           = dhanhq(DHAN_CLIENT_ID, access_token)


# ── sample signals (replace with real output from signal engine) ──────────────
signals = [
    {
        "mode": "EQUITY", "unit": "days", "interval": 1,
        "instrument": {"exchange": "NSE_EQ", "isin": "INE795G01014", "security_id": "467"},
        "signals": [{"symbol": "HDFCLIFE", "indicator": "2ut", "close": 616.45,
                     "tsl": np.float64(637.255), "timestamp": "2026-04-17T00:00:00+05:30",
                     "signal_type": "sell"}],
    },
    {
        "mode": "EQUITY", "unit": "days", "interval": 1,
        "instrument": {"exchange": "NSE_EQ", "isin": "INE154A01025", "security_id": "1660"},
        "signals": [
            {"symbol": "ITC", "indicator": "3hc", "close": 306.8,
             "tsl": np.float64(300.55), "timestamp": "2026-04-17T00:00:00+05:30",
             "signal_type": "buy"},
            {"symbol": "ITC", "indicator": "2ut", "close": 306.8,
             "tsl": np.float64(301.775), "timestamp": "2026-04-17T00:00:00+05:30",
             "signal_type": "buy"},
        ],
    },
    {
        "mode": "EQUITY", "unit": "days", "interval": 1,
        "instrument": {"exchange": "NSE_EQ", "isin": "INE002A01018", "security_id": "2885"},
        "signals": [{"symbol": "RELIANCE", "indicator": "3hc", "close": 1365.0,
                     "tsl": np.float64(1330.0), "timestamp": "2026-04-17T00:00:00+05:30",
                     "signal_type": "buy"}],
    },
]

# ── position sizing ───────────────────────────────────────────────────────────
buy_signals = flatten_signals(signals, signal_type="buy")
print("buy_signals:", buy_signals)

# sys.exit("Planned Exit")

# ── order execution ───────────────────────────────────────────────────────────
executed_orders = []

for sig in buy_signals:
    qty = compute_qty(sig["close"])

    # print("sig",sig,"qty",qty)
    # sys.exit("Planned Exit")

    if qty <= 0:
        print("Skipping %s — insufficient capital for even 1 share", sig["symbol"])
        continue

    print(f"Placing BUY {sig['symbol']} | indicator={sig['indicator']} | qty={qty} | entry={sig['close']:.2f} | sl={sig['tsl']:.2f}")

    # resp = dhan.place_order(
    #     security_id=sig["security_id"],
    #     exchange_segment=sig["exchange"],
    #     transaction_type=dhan.BUY,
    #     quantity=qty,
    #     order_type=dhan.MARKET,
    #     product_type=dhan.CNC,
    #     price=0,
    # )
    # print(resp)

    # order_id = resp.get("data", {}).get("orderId", "")

    executed_orders.append({
        "symbol":        sig["symbol"],
        "security_id":   sig["security_id"],
        "exchange":      sig["exchange"],
        "indicator":     sig["indicator"],
        "qty":           qty,
        "entry_price":   sig["close"],
        "stop_loss":     sig["tsl"],
        "target":        None,          # TODO: wire in target from position_sizer when ready
        # "order_id":      order_id,
        "forever_placed": False,        # Phase 2: set True after forever order is placed
        "timestamp":     datetime.now(IST).isoformat(),
    })

log_executed_orders(executed_orders, bucket=S3_BUCKET)
