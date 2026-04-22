import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import time as date_time_time
import time
import json
import boto3
import csv
import pandas as pd
import numpy as np
from io import StringIO
import logging, requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)

CANDLE_BODY_THRESHOLD = 0.0015

IST = ZoneInfo("Asia/Kolkata")
API_CALLS_PER_SEC = 10

def load_instruments(TRADING_SYMBOLS, bucket, file_path):
    data = load_stock_symbols_from_s3(bucket, file_path)    

    instruments = []
    for item in data:
        if item.get("exchange") == "NSE" and item.get("trading_symbol") in TRADING_SYMBOLS:
            instruments.append((item["trading_symbol"], item["instrument_key"], item["exchange_token"]))
    
    return instruments

def candle_duration_timedelta(unit: str, interval: str) -> timedelta:
    interval = int(interval)

    if unit == "minutes":
        return timedelta(minutes=interval)
    if unit == "hours":
        return timedelta(hours=interval)
    if unit == "days":
        return timedelta(days=interval)
    if unit == "weeks":
        return timedelta(weeks=interval)
    if unit == "months":
        return timedelta(days=30 * interval)

    raise ValueError("Unsupported unit")

def get_date_range(unit: str, interval: str):
    end_date = datetime.now(IST)

    if unit == "minutes":
        start_date = end_date - timedelta(days=7)
    elif unit == "hours":
        start_date = end_date - timedelta(days=90)
    elif unit == "days":
        start_date = end_date - timedelta(days=730)
    else:
        start_date = datetime(2023, 1, 1)

    return start_date, end_date

# upstox_access_token ="eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzUkNLNTYiLCJqdGkiOiI2OWM3N2JlMmVmZmU0ODJmNzA5NmM0YzIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc3NDY4MTA1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODA2MjcxMjAwfQ.tOVcAfz7htW1OPhPQdxvmu-Uc5HviBvDu3lFYTyUjdg"
# HEADERS = {
#     'Content-Type': 'application/json',
#     'Accept': 'application/json',
#     'Authorization': f'Bearer {upstox_access_token}'
# }

def nse_market_status(HEADERS):
    url = 'https://api.upstox.com/v2/market/status/NSE'
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP error: {response.status_code} - {response.text}")
        data = response.json()
        status = data.get('data').get('status')
        return status
    except Exception as e:
        raise RuntimeError(f"NSE status check failed: {e}")

def get_historical(instrument, from_date, to_date, unit, interval,HEADERS):
    url = f"https://api.upstox.com/v3/historical-candle/{instrument}/{unit}/{interval}/{to_date}/{from_date}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["data"]["candles"]
    else:
        print(f"Historical Error: {response.status_code} - {response.text}")
        return []

def get_intraday(instrument, unit, interval,HEADERS):
    url = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument}/{unit}/{interval}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["data"]["candles"]
    else:
        print(f"Intraday Error: {response.status_code} - {response.text}")
        return []
    
def fetch_candles(instrument: str, unit: str, interval: str, headers, entity: str = None):
    start_date, end_date = get_date_range(unit, interval)

    resp = get_historical(
        instrument,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        unit,
        interval,
        headers
    )
    hist = resp

    if unit in ("minutes", "hours", "days"):
        resp_i = get_intraday(instrument, unit, interval, headers)
        intra = resp_i
        candles = hist + intra
    else:
        candles = hist

    logger.info("raw_candles instrument=%s total=%d hist=%d intra=%d",
                instrument, len(candles), len(hist), len(candles) - len(hist))

    if not candles:
        return []

    # ---------------------------------------
    # KEEP ONLY CLOSED CANDLES (IST)
    # ---------------------------------------
    now_ist = datetime.now(IST)
    duration = candle_duration_timedelta(unit, interval)

    closed = []
    for c in candles:
        ts = datetime.fromisoformat(c[0])  # Upstox gives TZ-aware ISO
        if ts + duration <= now_ist:
            closed.append(c)
        elif entity == "EQUITY" and ts <= now_ist:
            closed.append(c)

    logger.info("closed_candles instrument=%s closed=%d dropped=%d",
                instrument, len(closed), len(candles) - len(closed))

    if not closed:
        return []

    by_ts = {c[0]: c for c in closed}
    return [by_ts[t] for t in sorted(by_ts.keys())]

def load_stock_symbols_from_s3(bucket: str, key: str) -> set:
    s3 = boto3.client("s3")

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response["Body"].read().decode("utf-8")

    symbols = set()

    # Detect format
    if key.endswith(".csv") or response.get("ContentType") == "text/csv":
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            symbol = row.get("Symbol")
            if symbol:
                symbols.add(symbol.strip())

    else:  # assume JSON
        data = json.loads(content)

        # JSON list of objects
        if isinstance(data, list):
            for row in data:
                symbol = row.get("Symbol") or row.get("tradingsymbol")
                if symbol:
                    symbols.add(symbol.strip())

        # JSON dict containing list
        elif isinstance(data, dict):
            for row in data.values():
                if isinstance(row, dict):
                    symbol = row.get("Symbol") or row.get("tradingsymbol")
                    if symbol:
                        symbols.add(symbol.strip())

    return symbols

def convert_candles_to_df(candles: list) -> pd.DataFrame:
    """
    Convert raw candle data to a pandas DataFrame.

    Args:
        candles: List of candles, where each candle is typically
                 [timestamp, open, high, low, close, volume]

    Returns:
        pd.DataFrame with columns: timestamp, open, high, low, close, volume
    """
    df = pd.DataFrame(
        candles,
        columns=["ts", "open", "high", "low", "close", "volume","oi"]
    )
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    df["candleType"] = np.where(df["close"] > df["open"], "Bull", "Bear")
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["body_threshold"] = df["close"] * CANDLE_BODY_THRESHOLD
    df["is_strong"] = df["body_size"] >= df["body_threshold"]

    numeric_cols = ["open", "high", "low", "close", "volume", "oi"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("ts").reset_index(drop=True)

    return df

def write_to_s3(bucket: str, key: str, body: bytes, content_type: str) -> None:
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


def write_signals_to_s3(results: list, bucket: str, key_prefix: str = "signals") -> str:
    """
    Flatten signal generation output and write it as a CSV to S3.

    Each signal becomes one row. Parent fields (mode, unit, interval, exchange,
    security_id) are repeated on every row belonging to that instrument.

    Returns the S3 key where the file was written.
    """
    rows = []
    for item in results:
        mode       = item.get("mode", "")
        unit       = item.get("unit", "")
        interval   = item.get("interval", "")
        instrument = item.get("instrument", {})
        exchange   = instrument.get("exchange", "")
        security_id = instrument.get("security_id", "")

        for signal in item.get("signals", []):
            rows.append({
                "mode":        mode,
                "unit":        unit,
                "interval":    interval,
                "exchange":    exchange,
                "security_id": security_id,
                "symbol":      signal.get("symbol", ""),
                "indicator":   signal.get("indicator", ""),
                "close":       float(signal.get("close", float("nan"))),
                "tsl":         float(signal.get("tsl", float("nan"))),
                "timestamp":   signal.get("timestamp", ""),
                "signal_type": signal.get("signal_type", ""),
            })

    if not rows:
        print("write_signals_to_s3: no rows to write, skipping")
        return ""

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    now_ist = datetime.now(IST)
    date_str = now_ist.strftime("%Y-%m-%d")
    ts_str   = now_ist.strftime("%Y%m%dT%H%M%S")
    s3_key   = f"{key_prefix}/{date_str}/signals_{ts_str}.csv"

    write_to_s3(bucket, s3_key, buf.getvalue().encode("utf-8"), "text/csv")

    print(f"write_signals_to_s3: wrote {len(rows)} rows to s3://{bucket}/{s3_key}")
    return s3_key


def apply_trailing_sl(
    df: pd.DataFrame,
    ignore_time: str = "15:15:00",
    prefixes=("3hc", "2ut"),
) -> pd.DataFrame:
    """
    Row-by-row trailing stop-loss with position tracking and SL hit detection.

    For each prefix reads:
        {prefix}_tsl   — raw TSL indicator value
        {prefix}_buy   — entry signal (long)
        {prefix}_sell  — entry signal (short)

    Writes:
        {prefix}_pos      — 1 (long), -1 (short), 0 (flat)
        {prefix}_trail_sl — TSL ratcheted: cummax while long, cummin while short
        {prefix}_sl_hit   — True on the exact candle where close crosses trail_sl

    SL hit logic:
        Long  : close < trail_sl  → exit (and optionally flip short if sell signal on same candle)
        Short : close > trail_sl  → exit (and optionally flip long  if buy  signal on same candle)

    Trail update happens AFTER entry/SL check, so the entry candle records the
    raw tsl value and ratcheting starts from the next candle onward.
    """
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.set_index("ts")

    if ignore_time:
        ignore_time_obj = date_time_time.fromisoformat(ignore_time)
        df = df[df.index.time != ignore_time_obj]

    has_strong = "is_strong" in df.columns

    for prefix in prefixes:
        tsl_col   = f"{prefix}_tsl"
        buy_col   = f"{prefix}_buy"
        sell_col  = f"{prefix}_sell"
        pos_col   = f"{prefix}_pos"
        trail_col = f"{prefix}_trail_sl"
        sl_col    = f"{prefix}_sl_hit"

        if tsl_col not in df.columns:
            continue

        n = len(df)
        pos_arr   = np.zeros(n, dtype=np.int8)
        trail_arr = np.full(n, np.nan, dtype=float)
        sl_arr    = np.zeros(n, dtype=bool)

        tsl_vals  = df[tsl_col].to_numpy(dtype=float)
        close     = df["close"].to_numpy(dtype=float)
        buy_sig   = df[buy_col].to_numpy(dtype=bool)
        sell_sig  = df[sell_col].to_numpy(dtype=bool)
        strong    = df["is_strong"].to_numpy(dtype=bool) if has_strong else np.ones(n, dtype=bool)

        position = 0       # current position: 1, -1, or 0
        trail_sl = np.nan  # active trailing SL level

        for i in range(n):
            c = close[i]
            t = tsl_vals[i]

            # ── SL hit check ────────────────────────────────────────────────
            if position == 1 and c < trail_sl:
                sl_arr[i] = True
                position  = 0
                trail_sl  = np.nan
                # same-candle flip to short
                if sell_sig[i] and strong[i]:
                    position = -1
                    trail_sl = t
                pos_arr[i]   = position
                trail_arr[i] = trail_sl
                continue

            if position == -1 and c > trail_sl:
                sl_arr[i] = True
                position  = 0
                trail_sl  = np.nan
                # same-candle flip to long
                if buy_sig[i] and strong[i]:
                    position = 1
                    trail_sl = t
                pos_arr[i]   = position
                trail_arr[i] = trail_sl
                continue

            # ── Entry when flat ──────────────────────────────────────────────
            if position == 0:
                if buy_sig[i] and strong[i]:
                    position = 1
                    trail_sl = t
                elif sell_sig[i] and strong[i]:
                    position = -1
                    trail_sl = t

            # ── Ratchet trail SL ─────────────────────────────────────────────
            if position == 1:
                trail_sl = max(trail_sl, t)
            elif position == -1:
                trail_sl = min(trail_sl, t)

            pos_arr[i]   = position
            trail_arr[i] = trail_sl

        df[pos_col]   = pos_arr
        df[trail_col] = trail_arr
        df[sl_col]    = sl_arr

    return df

def get_token_from_s3(S3_BUCKET,S3_KEY):
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data["token"]