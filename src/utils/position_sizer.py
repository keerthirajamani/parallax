import math
import logging
import os

logger = logging.getLogger(__name__)

# ── config ────────────────────────────────────────────────────────────────────

# When multiple indicators fire on the same symbol, this one wins.
# Fall back to whichever fired if this one didn't.
# TODO: list the indicators you want to trade. Orders are placed for signals
# whose indicator appears here. e.g. ["3hc"] or ["3hc", "2ut"]
PREFERRED_INDICATORS = ["3hc"]

# Max capital to deploy per trade regardless of total balance
MAX_TRADE_CAPITAL = float(os.environ.get("MAX_TRADE_CAPITAL", "10000"))


# ── capital ───────────────────────────────────────────────────────────────────

def get_available_capital(dhan) -> float:
    resp = dhan.get_fund_limits()
    capital = float(resp["data"]["available_balance"])
    print(f"position_sizer: available_capital={capital}")
    return capital


def flatten_signals(raw_signals: list[dict], signal_type: str) -> list[dict]:
    """
    Flatten the nested signal-generation output and filter by signal_type.

    Input shape (one element of raw_signals):
        {
          instrument: {exchange, isin, security_id},
          signals: [{symbol, indicator, close, tsl, signal_type, timestamp}, ...]
        }

    Output shape (one element):
        {symbol, security_id, exchange, indicator, signal_type, close, tsl}
    """
    flat = []
    for item in raw_signals:
        exchange    = item["instrument"]["exchange"]
        security_id = item["instrument"]["security_id"]

        for sig in item["signals"]:
            if sig["signal_type"] != signal_type:
                continue
            if sig["indicator"] not in PREFERRED_INDICATORS:
                continue
            flat.append({
                "symbol":      sig["symbol"],
                "security_id": security_id,
                "exchange":    exchange,
                "indicator":   sig["indicator"],
                "signal_type": sig["signal_type"],
                "close":       float(sig["close"]),
                "tsl":         float(sig["tsl"]),
                "timestamp":   sig["timestamp"],
            })
    return flat


# ── sizing ────────────────────────────────────────────────────────────────────

def compute_qty(close: float, max_capital: float = MAX_TRADE_CAPITAL) -> int:
    """
    Allocate max_capital per trade.
    Returns 0 if price exceeds the allocation cap.
    """
    return math.floor(max_capital / close)

def calculate_percentage(avgCostPrice: float, percentage: float = 3.0) -> int:
    return (percentage / 100) * avgCostPrice
