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
signals = [{'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE467B01029', 'security_id': '11536'}, 'interval': 1, 'signals': [{'symbol': 'TCS', 'indicator': '3hc', 'close': 2545.0, 'tsl': np.float64(2614.0), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'buy'}, {'symbol': 'TCS', 'indicator': '2ut', 'close': 2545.0, 'tsl': np.float64(2605.89), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE009A01021', 'security_id': '1594'}, 'interval': 1, 'signals': [{'symbol': 'INFY', 'indicator': '2ut', 'close': 1269.4, 'tsl': np.float64(1304.0600000000002), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE669C01036', 'security_id': '13538'}, 'interval': 1, 'signals': [{'symbol': 'TECHM', 'indicator': '3hc', 'close': 1453.3, 'tsl': np.float64(1531.3), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}, {'symbol': 'TECHM', 'indicator': '2ut', 'close': 1453.3, 'tsl': np.float64(1495.9099999999999), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE860A01027', 'security_id': '7229'}, 'interval': 1, 'signals': [{'symbol': 'HCLTECH', 'indicator': '2ut', 'close': 1289.6, 'tsl': np.float64(1336.84), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE263A01024', 'security_id': '383'}, 'interval': 1, 'signals': [{'symbol': 'BEL', 'indicator': '3hc', 'close': 448.95, 'tsl': np.float64(464.4), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE917I01010', 'security_id': '16669'}, 'interval': 1, 'signals': [{'symbol': 'BAJAJ-AUTO', 'indicator': '3hc', 'close': 9678.0, 'tsl': np.float64(9874.0), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE018A01030', 'security_id': '11483'}, 'interval': 1, 'signals': [{'symbol': 'LT', 'indicator': '3hc', 'close': 4021.9, 'tsl': np.float64(4130.0), 'timestamp': '2026-04-22T00:00:00+05:30', 'signal_type': 'sell'}]}]

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
