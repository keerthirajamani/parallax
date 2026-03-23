import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import time as date_time_time
import time
import json
import boto3
import csv
import pandas as pd
from io import StringIO
import logging, requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': 'Bearer {your_access_token}'
}

def get_historical(instrument, from_date, to_date, unit, interval):
    url = f"https://api.upstox.com/v3/historical-candle/{instrument}/{unit}/{interval}/{to_date}/{from_date}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["data"]["candles"]
    else:
        print(f"Historical Error: {response.status_code} - {response.text}")
        return []

def get_intraday(instrument, unit, interval):
    url = f"https://api.upstox.com/v3/historical-candle/intraday/{instrument}/{unit}/{interval}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["data"]["candles"]
    else:
        print(f"Intraday Error: {response.status_code} - {response.text}")
        return []
    
def fetch_candles(instrument: str, unit: str, interval: str):
    start_date, end_date = get_date_range(unit, interval)
    print(f"Fetching historical: {start_date} → {end_date}")
    
    resp = get_historical(
        instrument,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        unit,
        interval
    )
    # print("resp", resp)
    hist = resp#.data.candles if resp and resp.data else []

    if unit in ("minutes", "hours", "days"):
        print("Fetching intraday (today)...")
        resp_i = get_intraday(instrument, unit, interval)
        # print("resp_i", resp_i)
        intra = resp_i#.data.candles if resp_i and resp_i.data else []
        candles = hist + intra
    else:
        candles = hist

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

def apply_trailing_sl(
    df: pd.DataFrame,
    ignore_time: str = "15:15:00",
) -> pd.DataFrame:
    """
    Removes specified candle time and applies trailing SL logic.
    """

    df = df.copy()
    df["candleType"] = df.apply(lambda r: "Bull" if r["close"] > r["open"] else "Bear",axis=1)
    df["ts"] = pd.to_datetime(df["ts"])
    df = df.set_index("ts")

    # ================= REMOVE TIME =================
    if ignore_time:
        ignore_time_obj = date_time_time.fromisoformat(ignore_time)
        df = df[df.index.time != ignore_time_obj]

    df["SL"] = None
    df["SL_HIT"] = False

    current_sl = None
    position = None

    for i in range(len(df)):
        row = df.iloc[i]
        buy = row["buy"] == True
        sell = row["sell"] == True
        close = row["close"]
        low = row["low"]
        high = row["high"]

        if position is None and buy:
            position = "LONG"
            current_sl = low
            df.at[df.index[i], "SL"] = current_sl
            continue

        elif position is None and sell:
            position = "SHORT"
            current_sl = high
            df.at[df.index[i], "SL"] = current_sl
            continue
        # prev_open = df.iloc[i-1]["open"] if i > 0 else open
        prev_high = df.iloc[i-1]["high"] if i > 0 else high
        prev_low = df.iloc[i-1]["low"] if i > 0 else low
        prev_close = df.iloc[i-1]["close"] if i > 0 else close
        bullish = close > prev_close
        bearish = close < prev_close

        if position == "LONG":
            if low < current_sl:
                bullish = close > prev_close
                if not bullish and close <= prev_low:
                    df.at[df.index[i], "SL_HIT"] = True
                    df.at[df.index[i], "SL"] = current_sl
                    position = None
                    current_sl = None
                    # continue
                        # ADD THIS ↓
                    if sell:
                        position     = "SHORT"
                        current_sl   = high
                        # sl_values[i] = current_sl
                        df.at[df.index[i], "SL"] = current_sl
            else:
                # current_sl = low
                current_sl = max(current_sl, low)
            df.at[df.index[i], "SL"] = current_sl
        elif position == "SHORT":
            if high > current_sl:
                if not bearish and close >= prev_high:
                    df.at[df.index[i], "SL_HIT"] = True
                    df.at[df.index[i], "SL"] = current_sl
                    position = None
                    current_sl = None
                    # continue
                    # ADD THIS ↓
                    if buy:
                        position     = "LONG"
                        current_sl   = low
                        # sl_values[i] = current_sl
                        df.at[df.index[i], "SL"] = current_sl
            else:
                # current_sl = high
                current_sl = min(current_sl, high)
            df.at[df.index[i], "SL"] = current_sl
    return df