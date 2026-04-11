import requests, sys, os, json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd

from src.utils.common_utils import (
    apply_trailing_sl,
    fetch_candles,
    nse_market_status,
    convert_candles_to_df
)
from src.utils.indicators import three_horse_crow, ut_bot_alerts
from src.utils.webhook_trigger import webhook_handler
from src.config.symbols import resolve_symbol_map, SYMBOL_REGISTRY

IST = ZoneInfo("Asia/Kolkata")

def candles_to_df(candles):
    df = pd.DataFrame(candles, columns=["datetime", "open", "high", "low", "close", "volume", "oi"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df.set_index("datetime", inplace=True)
    return df

def get_data(symbol: str, unit: str, interval: int, symbol_map: dict):
    instrument = symbol_map[symbol]
    print(f"------ instrument ------{symbol}------")
    all_candles = fetch_candles(instrument, unit, interval)
    df = convert_candles_to_df(all_candles)
    df = three_horse_crow(df)
    # df = ut_bot_alerts(df)
    df["symbol"] = symbol
    df = apply_trailing_sl(df)
    print(df.tail(60).to_string())
    signals = build_signals_from_last_row(df)
    # sys.exit("Planned Exit")
    return signals



def build_signals_from_last_row(df, prefixes=("3hc", "2ut")):

    if df.empty:
        return []

    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")
    else:
        df.index = pd.to_datetime(df.index)

    last = df.iloc[-6]
    signals = []

    for prefix in prefixes:
        tsl_col  = f"{prefix}_tsl"
        buy_col  = f"{prefix}_buy"
        sell_col = f"{prefix}_sell"
        sl_col   = f"{prefix}_sl"

        if tsl_col not in df.columns:
            continue

        base_payload = {
            "symbol": last["symbol"],
            "indicator": prefix,
            "close": float(last["close"]),
            "tsl": last[tsl_col],
            "timestamp": last.name.isoformat(),
        }

        if sl_col in df.columns and last[sl_col]:
            signals.append({**base_payload, "signal_type": "sl"})

        if buy_col in df.columns and last[buy_col]:
            signals.append({**base_payload, "signal_type": "buy"})

        elif sell_col in df.columns and last[sell_col]:
            signals.append({**base_payload, "signal_type": "sell"})

    return signals

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)



def lambda_handler(event, context):
    market_status = nse_market_status()
    print("market_status ",market_status)
    # if market_status != "NORMAL_OPEN":
    #     return {
    #         "status": "skipped",
    #         "message": f"Market status: {market_status}"
    #     }
    webhoook_results = []
    unit = event.get("unit")
    interval =  event.get("interval")
    entity =  event.get("entity")
    print("Unit is ",unit)
    print("interval is ",interval)

    Symbols = resolve_symbol_map(entity)
    print("Symbols", Symbols)
    print("current time:", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %Z"))
    
    for Symbol in Symbols:
        signals = get_data(Symbol, unit, interval, Symbols)
        if not signals:
            print("No Signal  for symbol ", Symbol)
            print("")
            print("")
            continue
        event_payload = {
            "mode": entity,
            "unit": unit,
            "instrument": Symbols[Symbol],
            "interval":interval,
            "signals": signals,
            }
        print("Event Payload is ",event_payload)
        
        webhoook_results.append(webhook_handler(event_payload, None))
        # webhoook_results.append(event_payload)
    print("Webhook results", json.dumps(webhoook_results, indent=2))
    return True
event = {"unit":"hours", "interval":1, "entity": "INDEX"}
# event = {"unit":"days", "interval":1, "entity": "EQUITY"}
# print(lambda_handler(event,None))