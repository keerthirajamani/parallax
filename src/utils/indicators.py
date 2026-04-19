import pandas as pd
import numpy as np

def three_horse_crow(df, prefix='3hc', swing=3):

    df = df.copy()

    tsl_col  = f"{prefix}_tsl"
    buy_col  = f"{prefix}_buy"
    sell_col = f"{prefix}_sell"

    df["res"] = df["high"].rolling(window=swing, min_periods=swing).max()
    df["sup"] = df["low"].rolling(window=swing, min_periods=swing).min()

    df["res_prev"] = df["res"].shift(1)
    df["sup_prev"] = df["sup"].shift(1)

    df["avd"] = np.where(df["close"] > df["res_prev"], 1,np.where(df["close"] < df["sup_prev"], -1, 0))

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

    df[buy_col] = (
        (df["close"] > df[tsl_col]) 
        & (df["prev_close"] <= df["prev_tsl"]) 
        # & (df["candleType"] == "Bull") 
        # & df["is_strong"]
    )

    df[sell_col] = (
        (df["close"] < df[tsl_col]) 
        & (df["prev_close"] >= df["prev_tsl"]) 
        # & (df["candleType"] == "Bear") 
        # & df["is_strong"]
    )
    
    df = df.drop(columns=[
        "oi","res","sup","res_prev","sup_prev",
        "avd","avn","prev_close","prev_tsl","volume"
    ], errors="ignore")

    return df

def ut_bot_alerts(df, prefix="2ut", key_value=1, atr_period=10, use_heikin_ashi=False):
    """
    UT Bot with crossover + candle-type + is_strong signal logic.
    Same ATR trailing stop as ut_bot_alerts, but buy/sell signals require:
        Buy  : close crosses above tsl AND candleType == Bull AND is_strong
        Sell : close crosses below tsl AND candleType == Bear AND is_strong
    """
    data = df.copy()
    tsl_col  = f"{prefix}_tsl"
    buy_col  = f"{prefix}_buy"
    sell_col = f"{prefix}_sell"

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
    high  = data['high']
    low   = data['low']
    close = data['close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr    = tr.rolling(atr_period).mean()
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

    # --- Signals ---
    result = data.copy()
    result[tsl_col] = trailing_stop

    result["prev_close"] = result["close"].shift(1)
    result["prev_tsl"]   = trailing_stop.shift(1)

    result[buy_col] = (
        (result["close"] > result[tsl_col]) 
        & (result["prev_close"] <= result["prev_tsl"]) 
        # & (result["candleType"] == "Bull") 
        # & result["is_strong"]
    )

    result[sell_col] = (
        (result["close"] < result[tsl_col]) 
        & (result["prev_close"] >= result["prev_tsl"]) 
        # & (result["candleType"] == "Bear") 
        # & result["is_strong"]
    )

    result = result.drop(columns=["prev_close", "prev_tsl"], errors="ignore")

    if "oi" in df.columns:
        result = result.drop(columns=["oi"])
    return result