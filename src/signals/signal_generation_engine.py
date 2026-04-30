import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from src.utils.common_utils import (
    fetch_candles,
    nse_market_status,
    convert_candles_to_df,
    write_signals_to_s3,
)
from src.utils.indicators import three_horse_crow, ut_bot_alerts
from src.config.symbols import resolve_symbol_map

# ── Constants ─────────────────────────────────────────────────────────────────

IST = ZoneInfo("Asia/Kolkata")


upstox_access_token = os.environ.get("UPSTOX_ACCESS_TOKEN","eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzUkNLNTYiLCJqdGkiOiI2OWM3N2JlMmVmZmU0ODJmNzA5NmM0YzIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc3NDY4MTA1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODA2MjcxMjAwfQ.tOVcAfz7htW1OPhPQdxvmu-Uc5HviBvDu3lFYTyUjdg")

HEADERS = {
    "Content-Type":  "application/json",
    "Accept":        "application/json",
    "Authorization": f"Bearer {upstox_access_token}",
}

US_ENTITIES = {"US_EQUITY", "US_INDEX"}

US_UNIT_TO_INTERVAL = {
    "days":  "1d",
    "weeks": "1wk",
}

US_INTERVAL_CONFIG = {
    "1d":  {"yf_interval": "1d",  "period": "1y",  "label": "days 1"},
    "1wk": {"yf_interval": "1wk", "period": "2y",  "label": "weeks 1"},
}

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)



def build_signals_from_last_row(df, prefixes=("3hc", "2ut")):
    if df.empty:
        return []
    print(df.tail(30))

    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")
    else:
        df.index = pd.to_datetime(df.index)

    last = df.iloc[-1]
    signals = []

    for prefix in prefixes:
        if f"{prefix}_tsl" not in df.columns:
            continue

        base = {
            "symbol":    last["symbol"],
            "indicator": prefix,
            "close":     float(last["close"]),
            "tsl":       last[f"{prefix}_tsl"],
            "timestamp": last.name.isoformat(),
        }

        if f"{prefix}_sl_hit" in df.columns and last[f"{prefix}_sl_hit"]:
            signals.append({**base, "signal_type": "sl"})

        if f"{prefix}_buy" in df.columns and last[f"{prefix}_buy"]:
            signals.append({**base, "signal_type": "buy"})
        elif f"{prefix}_sell" in df.columns and last[f"{prefix}_sell"]:
            signals.append({**base, "signal_type": "sell"})

    return signals


def _fetch_india_symbol(symbol: str, unit: str, interval: int, symbol_map: dict, entity: str):
    sym = symbol_map[symbol]
    instrument = f"{sym['exchange']}|{sym['isin']}" if "isin" in sym else sym["exchange"]
    df = convert_candles_to_df(fetch_candles(instrument, unit, interval, HEADERS, entity))
    df = three_horse_crow(df)
    # df = ut_bot_alerts(df)
    df["symbol"] = symbol
    return symbol, build_signals_from_last_row(df)


def get_india_signals(symbol_map: dict, unit: str, interval: int, entity: str) -> dict:
    print(f"Fetching {len(symbol_map)} India symbols [{unit} {interval}]")
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_india_symbol, sym, unit, interval, symbol_map, entity): sym
            for sym in symbol_map
        }
        for future in as_completed(futures):
            symbol, signals = future.result()
            results[symbol] = signals
    return results


def _process_us_ticker(symbol: str, df: pd.DataFrame):
    if df is None or df.empty:
        return symbol, []
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
    df.index = df.index.tz_localize(None)
    df.index.name = "datetime"
    df = df.round(4).dropna()
    df["symbol"] = symbol
    df = three_horse_crow(df)
    df = ut_bot_alerts(df)
    return symbol, build_signals_from_last_row(df)


def get_us_signals(symbol_map: dict, interval: str = "1d") -> dict:
    cfg = US_INTERVAL_CONFIG.get(interval, US_INTERVAL_CONFIG["1d"])
    tickers = [symbol_map[s]["ticker"] for s in symbol_map]
    print(f"Batch fetching {len(tickers)} US tickers [{cfg['label']}]")

    raw = yf.download(
        tickers,
        period=cfg["period"],
        interval=cfg["yf_interval"],
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    results = {}
    for symbol in symbol_map:
        ticker = symbol_map[symbol]["ticker"]
        ticker_df = raw[ticker] if len(tickers) > 1 else raw
        sym, signals = _process_us_ticker(symbol, ticker_df)
        results[sym] = signals
    return results


def signal_lambda_handler(event, _context):
    entity   = event.get("entity")
    unit     = event.get("unit")
    interval = event.get("interval")
    is_us    = entity.upper() in US_ENTITIES

    print(f"entity={entity} | unit={unit} | interval={interval} | time={datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if not is_us:
        print("market_status:", nse_market_status(HEADERS))
        # if market_status != "NORMAL_OPEN":
        #     return {"status": "skipped", "message": f"Market status: {market_status}"}

    symbol_map  = resolve_symbol_map(entity)
    us_interval = US_UNIT_TO_INTERVAL.get(unit) if is_us else None

    signals_map = (
        get_us_signals(symbol_map, interval=us_interval)
        if is_us else
        get_india_signals(symbol_map, unit, interval, entity)
    )

    results = []
    for symbol, signals in signals_map.items():
        if not signals:
            print(f"No signal: {symbol}")
            continue
        else:
            print(f"signal : {symbol}")
        results.append({
            "mode":       entity,
            "unit":       unit,
            "instrument": symbol_map[symbol],
            "interval":   us_interval if is_us else interval,
            "signals":    signals,
        })

    if results:
        SIGNALS_BUCKET = os.environ.get("SIGNALS_BUCKET", "us-east-1-parallax-bucket")
        key_prefix = f"signals/us-signals/{unit}" if is_us else f"signals/equity-signals/{unit}"
        write_signals_to_s3(results, bucket=SIGNALS_BUCKET, key_prefix=key_prefix)

    return results


# ── Local test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    event = {"unit": "hours",  "interval": 1, "entity": "INDEX"}
#     # event = {"unit": "weeks",   "interval": 1, "entity": "EQUITY"}
#     # event = {"unit": "days", "interval": 1, "entity": "US_EQUITY"}
#     # event = {"unit": "weeks",  "interval": 1, "entity": "US_EQUITY"}
    print(signal_lambda_handler(event, None))

