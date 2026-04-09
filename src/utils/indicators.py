import pandas as pd
import numpy as np

def three_horse_crow(df, prefix='3hc', swing=3):
    df = df.copy()

    # ----------------------------
    # Column names (dynamic)
    # ----------------------------
    tsl_col  = f"{prefix}_tsl"
    buy_col  = f"{prefix}_buy"
    sell_col = f"{prefix}_sell"
    pos_col  = f"{prefix}_pos"

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

    df["avn"] = (
        df["avd"]
        .astype("float64")
        .replace(0, np.nan)
        .ffill()
        .fillna(0)
        .astype("int8")
    )

    df[tsl_col] = np.where(df["avn"] == 1, df["sup"], df["res"])

    df["prev_close"] = df["close"].shift(1)
    df["prev_tsl"] = df[tsl_col].shift(1)

    # ----------------------------
    # Signals
    # ----------------------------
    df[buy_col] = (
        (df["close"] > df[tsl_col]) &
        (df["prev_close"] <= df["prev_tsl"]) &
        (df["candleType"] == "Bull") &
        df["is_strong"]
    )

    df[sell_col] = (
        (df["close"] < df[tsl_col]) &
        (df["prev_close"] >= df["prev_tsl"]) &
        (df["candleType"] == "Bear") &
        df["is_strong"]
    )

    # ----------------------------
    # POSITION LOGIC (unchanged)
    # ----------------------------
    pos = np.zeros(len(df))

    for i in range(1, len(df)):
        if df["close"].iloc[i-1] <= df[tsl_col].iloc[i-1] and df["close"].iloc[i] > df[tsl_col].iloc[i]:
            pos[i] = 1
        elif df["close"].iloc[i-1] >= df[tsl_col].iloc[i-1] and df["close"].iloc[i] < df[tsl_col].iloc[i]:
            pos[i] = -1
        else:
            pos[i] = pos[i-1]

    df[pos_col] = pos

    # ----------------------------
    # Cleanup
    # ----------------------------
    df = df.drop(columns=[
        "oi","res","sup","res_prev","sup_prev",
        "avd","avn","prev_close","prev_tsl"
    ], errors="ignore")

    return df


def ut_bot_alerts(df, prefix="2ut", key_value=1, atr_period=10, use_heikin_ashi=False):

    data = df.copy()
    tsl_col  = f"{prefix}_tsl"
    buy_col  = f"{prefix}_buy"
    sell_col = f"{prefix}_sell"
    pos_col  = f"{prefix}_pos"
    
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
    result[tsl_col] = trailing_stop
    result[buy_col] = buy
    result[sell_col] = sell
    result[pos_col] = pos
    
    if "oi" in df.columns:
        result = result.drop(columns=["oi"])
    return result