"""
End-of-Day (EOD) Candle Data Fetcher
Uses: yfinance (no API key required)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.utils.indicators import three_horse_crow, ut_bot_alerts

def fetch_eod_candles(
    symbols: list[str],
    period: str = "1y",       # e.g. 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    start: str = None,         # e.g. "2024-01-01" (overrides period if set)
    end: str = None,           # e.g. "2024-12-31" (defaults to today)
) -> dict[str, pd.DataFrame]:
    """
    Fetch end-of-day OHLCV candle data for one or more US stock symbols.

    Args:
        symbols : List of ticker symbols, e.g. ["AAPL", "MSFT"]
        period  : Lookback period (used only if start is None)
        start   : Start date string "YYYY-MM-DD"
        end     : End date string "YYYY-MM-DD" (defaults to today)

    Returns:
        dict of {symbol: DataFrame with OHLCV columns}
    """
    results = {}

    for symbol in symbols:
        print(f"\nFetching EOD candles for: {symbol}")
        ticker = yf.Ticker(symbol)

        if start:
            df = ticker.history(start=start, end=end, interval="1d")
        else:
            df = ticker.history(period=period, interval="1d")

        if df.empty:
            print(f"  ⚠️  No data returned for {symbol}. Check the symbol or date range.")
            continue

        # Keep only standard OHLCV columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.rename(columns={'Open': 'open', 'High': 'high','Close': 'close', 'Low': 'low', 'Volume': 'volume'}, inplace=True)
        df.index = df.index.tz_localize(None)   # strip timezone for clean display
        df.index.name = "Date"
        df = df.round(4)
        df['symbol']= symbol
        results[symbol] = df
        df = three_horse_crow(df)
        print(df.tail(50).to_string())
        signals = build_signals_from_last_row(df)

    return results

def build_signals_from_last_row(df, prefixes=("3hc", "2ut")):

    if df.empty:
        return []

    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")
    else:
        df.index = pd.to_datetime(df.index)

    last = df.iloc[-1]
    signals = []

    for prefix in prefixes:
        tsl_col  = f"{prefix}_tsl"
        buy_col  = f"{prefix}_buy"
        sell_col = f"{prefix}_sell"
        sl_col   = f"{prefix}_sl_hit"

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

def get_latest_candle(symbols: list[str]) -> pd.DataFrame:
    """
    Fetch only the most recent completed daily candle for each symbol.
    Useful to run after US market close (4 PM ET).
    """
    rows = []
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1d")

        if df.empty:
            print(f"⚠️  No data for {symbol}")
            continue

        last = df.iloc[-1]
        rows.append({
            "Symbol": symbol,
            "Date":   df.index[-1].date(),
            "Open":   round(last["Open"],   4),
            "High":   round(last["High"],   4),
            "Low":    round(last["Low"],    4),
            "Close":  round(last["Close"],  4),
            "Volume": int(last["Volume"]),
        })

    summary = pd.DataFrame(rows).set_index("Symbol")
    return summary


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    SP500_TOP30 = [
        "AAPL", "MSFT", "NVDA", "AMZN", "META",
        "GOOGL", "GOOG", "TSLA", "BRK-B", "JPM",
        "UNH", "V", "XOM", "MA", "LLY",
        "AVGO", "HD", "PG", "JNJ", "MRK",
        "COST", "ABBV", "CVX", "CRM", "BAC",
        "NFLX", "AMD", "PEP", "KO", "TMO",
    ]
 
    # Top 30 Nasdaq-100 by weight (deduped against S&P 500)
    NASDAQ_TOP30 = [
        "QCOM", "INTC", "ADBE", "CSCO", "TXN",
        "AMAT", "MU", "PANW", "SNPS", "KLAC",
        "LRCX", "MRVL", "CDNS", "REGN", "VRTX",
        "FTNT", "MDLZ", "GILD", "ADI", "ASML",
        "ABNB", "PYPL", "MELI", "IDXX", "DXCM",
        "AZN", "HON", "SBUX", "ISRG", "INTU",
    ]
 
    # Top 30 Dow Jones Industrial Average components
    DJIA_TOP30 = [
        "GS", "UNH", "CAT", "AMGN", "MCD",
        "AXP", "TRV", "IBM", "MMM", "NKE",
        "DIS", "WMT", "RTX", "BA", "DOW",
        "SHW", "CRM", "VZ", "IBKR", "CVX",
        "MRK", "JNJ", "PG", "KO", "MSFT",
        "JPM", "HD", "AAPL", "CSCO", "HON",
    ]
    seen = set()
    SYMBOLS = []
    for sym in SP500_TOP30 + NASDAQ_TOP30 + DJIA_TOP30:
        if sym not in seen:
            seen.add(sym)
            SYMBOLS.append(sym)
 
    print(f"Total unique symbols: {len(SYMBOLS)}")
    print("Symbols:", SYMBOLS)

    print("=" * 60)
    print("  EOD Candle Fetcher  |  Source: yfinance  |  Interval: 1d")
    print("=" * 60)

    all_data = fetch_eod_candles(
        symbols=SYMBOLS,
        period="1mo",       # change to start="2025-01-01" for custom range
    )

    # ── 2. Print the latest single candle for each symbol ──
    print("\n" + "=" * 60)
    print("  Latest Completed Daily Candle")
    print("=" * 60)