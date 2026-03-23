import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

from src.utils.common_utils import (
    apply_trailing_sl,
    fetch_candles
)
from src.utils.indicators import three_horse_crow_pandas
from src.utils.webhook_trigger import webhook_handler

IST = ZoneInfo("Asia/Kolkata")


def candles_to_df(candles):
    df = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume", "oi"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)
    return df

def get_nifty_2hr(Symbol, unit, interval):
    instrument = Symbols[Symbol]
    print("instrument", Symbol)
    all_candles = fetch_candles(instrument, unit, interval)
    df = three_horse_crow_pandas(all_candles, 3)
    df = apply_trailing_sl(df)
    df["symbol"] = Symbol
    print(df.tail(50))
    signals = build_signals_from_last_row(df)
    return signals

def build_signals_from_last_row(df):
    if df.empty:
        return []

    last = df.iloc[-1] # default value should be -1, for testing changed it to -3.
    signals = []

    base_payload = {
        "symbol": last["symbol"],
        # "exchange_token": last["exchange_token"],
        "close": float(last["close"]),
        "tsl": last["SL"],
        "timestamp": last.name.isoformat(),
    }

    if last["SL_HIT"]:
        signals.append({**base_payload, "signal_type": "sl"})

    if last["buy"]:
        signals.append({**base_payload, "signal_type": "buy"})

    elif last["sell"]:
        signals.append({**base_payload, "signal_type": "sell"})

    return signals


pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

Symbols = {
        "nifty50":   "NSE_INDEX%7CNifty%2050",
        "banknifty": "NSE_INDEX%7CNifty%20Bank",
        "finnifty":  "NSE_INDEX%7CNifty%20Fin%20Service"
    }
def lambda_handler(event, context):
    webhoook_results = []
    print("current time:", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z"))
    unit = event.get("unit")
    interval =  event.get("interval")
    print("Unit is ",unit)
    print("interval is ",interval)
    for Symbol in Symbols:
        signals = get_nifty_2hr(Symbol, unit, interval)
        if not signals:
            print("No Signal  for symbol ", Symbol)
            print("")
            print("")
            continue
        event_payload = {
            "mode": "INDEX",
            "unit": unit,
            "interval":interval,
            "signals": signals,
            }
        print("Event Payload is ",event_payload)
        
        # webhoook_results.append(webhook_handler(event_payload, None))
        webhoook_results.append(event_payload)
    print("Webhook results", webhoook_results)
    return True
event = {"unit":"hours", "interval":2}
lambda_handler(event,None)