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
    # Below Commented code is check the buy signal in bearish candle at 9:15 candle.
    # is_0915 = df["ts"].dt.time == pd.Timestamp("09:15").time()

    # df["buy"] = df["buy"] & ~(is_0915 & (df["candleType"] == "Bear"))
    # df["sell"] = df["sell"] & ~(is_0915 & (df["candleType"] == "Bull"))
    df = df.drop(columns=["oi"])
    return df