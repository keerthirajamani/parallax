import pandas as pd
import numpy as np


def three_horse_crow_pandas(candles, swing=3):

    if not candles or len(candles) < swing + 2:
        return None

    df = pd.DataFrame(
        candles,
        columns=["ts", "open", "high", "low", "close", "volume", "oi"]
    )

    # ----------------------------
    # Force correct dtypes early
    # ----------------------------
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df["candleType"] = df.apply(lambda r: "Bull" if r["close"] > r["open"] else "Bear",axis=1)

    numeric_cols = ["open", "high", "low", "close", "volume", "oi"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("ts").reset_index(drop=True)

    # ----------------------------
    # Rolling calculations
    # ----------------------------
    df["res"] = df["high"].rolling(window=swing, min_periods=swing).max()
    df["sup"] = df["low"].rolling(window=swing, min_periods=swing).min()

    df["res_prev"] = df["res"].shift(1)
    df["sup_prev"] = df["sup"].shift(1)

    df["avd"] = 0
    df.loc[df["close"] > df["res_prev"], "avd"] = 1
    df.loc[df["close"] < df["sup_prev"], "avd"] = -1
    df["avn"] = (df["avd"].astype("float64").replace(0, np.nan).ffill().fillna(0).astype("int8"))
    df["tsl"] = np.where(df["avn"] == 1, df["sup"], df["res"])
    df["prev_close"] = df["close"].shift(1)
    df["prev_tsl"] = df["tsl"].shift(1)

    df["buy"] = (df["close"] > df["tsl"]) & (
        df["prev_close"] <= df["prev_tsl"]
    )

    df["sell"] = (df["close"] < df["tsl"]) & (
        df["prev_close"] >= df["prev_tsl"]
    )
    df["pos"] = np.where(df["buy"], 1, np.where(df["sell"], -1, 0))
    df["pos"] = (df["pos"].astype("float64")
                          .replace(0, np.nan)
                          .ffill()
                          .fillna(0)
                          .astype("int8"))
    # Below Commented code is check the buy signal in bearish candle at 9:15 candle.
    # is_0915 = df["ts"].dt.time == pd.Timestamp("09:15").time()

    # df["buy"] = df["buy"] & ~(is_0915 & (df["candleType"] == "Bear"))
    # df["sell"] = df["sell"] & ~(is_0915 & (df["candleType"] == "Bull"))
    # df = df.drop(columns=["oi"])
    df = df.drop(columns=["oi", "res", "sup", "res_prev","sup_prev", "avd","avn","prev_close", "prev_tsl"])
    return df

def ut_bot_pandas(candles, key_value=3, atr_period=10):
    """
    UT Bot ATR Trailing Stop Strategy
    Converted from Pine Script v4 by HPotter

    Args:
        candles : list of [ts, open, high, low, close, volume, oi]
        key_value  : sensitivity multiplier (default 3)
        atr_period : ATR period (default 10)

    Returns:
        DataFrame with trailing stop, position, buy/sell signals
    """

    if not candles or len(candles) < atr_period + 2:
        return None

    df = pd.DataFrame(
        candles,
        columns=["ts", "open", "high", "low", "close", "volume", "oi"]
    )

    # ----------------------------
    # Force correct dtypes early
    # ----------------------------
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    numeric_cols = ["open", "high", "low", "close", "volume", "oi"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("ts").reset_index(drop=True)

    # ----------------------------
    # ATR Calculation
    # ----------------------------
    high_low   = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close  = (df["low"]  - df["close"].shift(1)).abs()

    tr     = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr    = tr.ewm(alpha=1 / atr_period, adjust=False).mean()
    n_loss = key_value * atr

    src = df["close"]

    # ----------------------------
    # ATR Trailing Stop (iterative — matches Pine's self-referencing logic)
    # ----------------------------
    tsl = np.zeros(len(df))

    for i in range(len(df)):
        prev_tsl = tsl[i - 1] if i > 0 else 0.0
        c        = src.iloc[i]
        c_prev   = src.iloc[i - 1] if i > 0 else 0.0
        loss     = n_loss.iloc[i]

        if c > prev_tsl and c_prev > prev_tsl:
            tsl[i] = max(prev_tsl, c - loss)
        elif c < prev_tsl and c_prev < prev_tsl:
            tsl[i] = min(prev_tsl, c + loss)
        elif c > prev_tsl:
            tsl[i] = c - loss
        else:
            tsl[i] = c + loss

    df["tsl"] = tsl

    # ----------------------------
    # Buy / Sell Signals (crossover/crossunder)
    # ----------------------------
    df["buy"]  = (src > df["tsl"]) & (src.shift(1) <= df["tsl"].shift(1))
    df["sell"] = (src < df["tsl"]) & (src.shift(1) >= df["tsl"].shift(1))

    # ----------------------------
    # Suppress conflicting signals at 09:15 candle only
    # ----------------------------
    # df["candleType"] = np.where(df["close"] > df["open"], "Bull", "Bear")
    # is_0915 = df["ts"].dt.time == pd.Timestamp("09:15").time()

    # df["buy"]  = df["buy"]  & ~(is_0915 & (df["candleType"] == "Bear"))
    # df["sell"] = df["sell"] & ~(is_0915 & (df["candleType"] == "Bull"))

    # ----------------------------
    # Position — derived from buy/sell only (no silent flip on gap)
    # ----------------------------
    df["pos"] = np.where(df["buy"], 1, np.where(df["sell"], -1, np.nan))
    df["pos"] = df["pos"].ffill().fillna(0).astype("int8")

    df = df.drop(columns=["oi"])
    return df