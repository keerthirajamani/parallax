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

    df["candleType"] = np.where(df["close"] > df["open"], "Bull", "Bear")
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["body_threshold"] = df["close"] * 0.0025
    df["is_strong"] = df["body_size"] >= df["body_threshold"]

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

    # df["buy_0"] = (df["close"] > df["tsl"]) & (
    #     df["prev_close"] <= df["prev_tsl"]
    # )

    # df["sell_0"] = (df["close"] < df["tsl"]) & (
    #     df["prev_close"] >= df["prev_tsl"]
    # )
    
    df["buy"] = (
        (df["close"] > df["tsl"]) &
        (df["prev_close"] <= df["prev_tsl"]) &
        (df["candleType"] == "Bull") &
        df["is_strong"]
        )
    df["sell"] = (
        (df["close"] < df["tsl"]) &
        (df["prev_close"] >= df["prev_tsl"]) &
        (df["candleType"] == "Bear") &
        df["is_strong"]
        )

    df = df.drop(columns=["oi","res","sup","res_prev","sup_prev","avd","avn","prev_close","prev_tsl"])
    return df

def ut_bot_alerts(candles, key_value=1, atr_period=10, use_heikin_ashi=False):
    if not candles:
        return None

    df = pd.DataFrame(
        candles,
        columns=["ts", "open", "high", "low", "close", "volume", "oi"]
    )
    # ----------------------------
    # Force correct dtypes early
    # ----------------------------
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df["candleType"] = np.where(df["close"] > df["open"], "Bull", "Bear")
    df["body_size"] = (df["close"] - df["open"]).abs()
    df["body_threshold"] = df["close"] * 0.0025
    df["is_strong"] = df["body_size"] >= df["body_threshold"]

    numeric_cols = ["open", "high", "low", "close", "volume", "oi"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    df = df.sort_values("ts").reset_index(drop=True)

    data = df.copy()
    

    # --- Heikin Ashi (optional) ---
    if use_heikin_ashi:
        ha = pd.DataFrame(index=data.index)
        ha['close'] = (data['open'] + data['high'] + data['low'] + data['close']) / 4
        ha['open'] = (data['open'].shift(1) + data['close'].shift(1)) / 2
        ha['high'] = ha[['open', 'close']].join(data['high']).max(axis=1)
        ha['low'] = ha[['open', 'close']].join(data['low']).min(axis=1)
        src = ha['close']
    else:
        src = data['close']

    # --- ATR calculation ---
    high = data['high']
    low = data['low']
    close = data['close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(atr_period).mean()

    n_loss = key_value * atr

    # --- ATR Trailing Stop ---
    trailing_stop = np.zeros(len(data))
    
    for i in range(1, len(data)):
        prev_stop = trailing_stop[i-1]

        if src.iloc[i] > prev_stop and src.iloc[i-1] > prev_stop:
            trailing_stop[i] = max(prev_stop, src.iloc[i] - n_loss.iloc[i])
        elif src.iloc[i] < prev_stop and src.iloc[i-1] < prev_stop:
            trailing_stop[i] = min(prev_stop, src.iloc[i] + n_loss.iloc[i])
        elif src.iloc[i] > prev_stop:
            trailing_stop[i] = src.iloc[i] - n_loss.iloc[i]
        else:
            trailing_stop[i] = src.iloc[i] + n_loss.iloc[i]

    trailing_stop = pd.Series(trailing_stop, index=data.index)

    # --- Position Logic ---
    pos = np.zeros(len(data))

    for i in range(1, len(data)):
        if src.iloc[i-1] < trailing_stop.iloc[i-1] and src.iloc[i] > trailing_stop.iloc[i]:
            pos[i] = 1
        elif src.iloc[i-1] > trailing_stop.iloc[i-1] and src.iloc[i] < trailing_stop.iloc[i]:
            pos[i] = -1
        else:
            pos[i] = pos[i-1]

    pos = pd.Series(pos, index=data.index)

    # --- EMA(1) ---
    ema = src.ewm(span=1, adjust=False).mean()

    # --- Signals ---
    above = (ema > trailing_stop) & (ema.shift(1) <= trailing_stop.shift(1))
    below = (trailing_stop > ema) & (trailing_stop.shift(1) <= ema.shift(1))

    buy = (src > trailing_stop) & above
    sell = (src < trailing_stop) & below

    # --- Output ---
    result = data.copy()
    result['atr'] = atr
    result['tsl'] = trailing_stop
    result['pos'] = pos
    result['buy'] = buy
    result['sell'] = sell
    result = result.drop(columns=["oi"])
    return result