import pandas as pd
import numpy as np
from collections import deque

def three_horse_crow(candles, swing=3):
    if len(candles) < swing + 2:
        return None

    maxdq, mindq = deque(), deque()
    avn = 0
    prev_tsl = None
    prev_close = None

    for i, cndl in enumerate(candles):
        high, low, close = cndl[2], cndl[3], cndl[4]

        while maxdq and maxdq[-1][1] <= high:
            maxdq.pop()
        maxdq.append((i, high))
        while maxdq and maxdq[0][0] <= i - swing:
            maxdq.popleft()

        while mindq and mindq[-1][1] >= low:
            mindq.pop()
        mindq.append((i, low))
        while mindq and mindq[0][0] <= i - swing:
            mindq.popleft()

        if i < swing:
            prev_close = close
            continue

        res = maxdq[0][1]
        sup = mindq[0][1]

        if i == swing:
            last_res, last_sup = res, sup
        else:
            avd = 1 if close > last_res else (-1 if close < last_sup else 0)
            if avd != 0:
                avn = avd

        tsl = sup if avn == 1 else res

        buy = sell = False
        if prev_tsl is not None:
            if close > tsl and prev_close <= prev_tsl:
                buy = True
            elif close < tsl and prev_close >= prev_tsl:
                sell = True

        last_res, last_sup = res, sup
        prev_tsl, prev_close = tsl, close

    last = candles[-1]
    return {
        "ts": last[0],
        "close": last[4],
        "tsl": prev_tsl,
        "avn": avn,
        "buy": buy,
        "sell": sell
    }


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
    df = df.drop(columns=["oi"])
    return df