import os
import logging
import pandas as pd
# from datetime import time
from utils.common_utils import (
    get_date_range,
    fetch_candles,
    create_upstox_api,
    load_instruments,
    load_stock_symbols_from_s3,
    apply_trailing_sl
)
from utils.indicators import three_horse_crow_pandas

from utils.webhook_trigger import index_signal_webhook_handler


logger = logging.getLogger()
logger.setLevel(logging.INFO)

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

ACCESS_TOKEN = ""
SWING = 3
BUCKET = 'datahub-market-data-live'
EQUITY_PATH = 'nse/equity/ind_nifty200list.csv'
# INSTRUMENT_PATH = 'upstox/instrument/NSE.json'
# INSTRUMENT_PATH = "/Users/keerthirajamani/Downloads/sourceCode/parallax/src/NSE.json" # Added for testing.

# trading_symbol_metadata = {'NIFTY', 'FINNIFTY', 'BANKNIFTY'}
trading_symbol_metadata = {'NIFTY'} # Added for testing.

def process_instrument(api, symbol, instrument_key, exchange_token, unit, interval):
    candles = fetch_candles(api, instrument_key, unit, interval)
    df = three_horse_crow_pandas(candles, SWING)
    df = apply_trailing_sl(df)
    df["symbol"] = symbol
    df["exchange_token"] = exchange_token
    return df

def build_signals_from_last_row(df):
    if df.empty:
        return []

    last = df.iloc[-1]
    signals = []

    base_payload = {
        "symbol": last["symbol"],
        "exchange_token": last["exchange_token"],
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

def lambda_handler(event, context):
    MODE = event.get("MODE")
    UNIT = event.get("UNIT")
    INTERVAL = str(event.get("INTERVAL"))

    start_date, end_date = get_date_range(UNIT, INTERVAL)
    print("start_date:", start_date)
    print("end_date:", end_date)

    if MODE == "EQUITY":
        TRADING_SYMBOLS = load_stock_symbols_from_s3(BUCKET, EQUITY_PATH)
    else:
        TRADING_SYMBOLS = trading_symbol_metadata

    # instruments = load_instruments(TRADING_SYMBOLS, BUCKET, INSTRUMENT_PATH)
    instruments = [('NIFTY', 'NSE_INDEX|Nifty 50', '26000'), ('BANKNIFTY', 'NSE_INDEX|Nifty Bank', '26009'), ('FINNIFTY', 'NSE_INDEX|Nifty Fin Service', '26037')]
    print("instruments", instruments)

    if not instruments:
        print("NO_SYMBOLS")
        return

    api = create_upstox_api(ACCESS_TOKEN)

    for symbol, key, exchange_token in instruments:
        try:
            df = process_instrument(api, symbol, key, exchange_token, UNIT, INTERVAL)
            print(df.tail(50))
            signals = build_signals_from_last_row(df)
            # import requests
            # resp = requests.post(
            #     "https://webhook.site/0a6d7f78-bba3-4cdd-9b5c-ece8d5dc3d38"
            # )
            if not signals:
                print("no_signal symbol=%s", symbol)
                continue

            # 2️⃣ Send to webhook engine
            event_payload = {
                "mode": "INDEX",
                "signals": signals,
            }

            result = index_signal_webhook_handler(event_payload, None)

        except Exception:
            logger.exception(f"Failed for {symbol}")

# RUN
if __name__ == "__main__":
    event = {"MODE": "INDEX", "UNIT": "hours", "INTERVAL": 2}
    lambda_handler(event, None)