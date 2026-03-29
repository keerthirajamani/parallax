INDEX_SYMBOLS = {
        "nifty50":   "NSE_INDEX|Nifty 50",
        "banknifty": "NSE_INDEX|Nifty Bank",
        "finnifty":  "NSE_INDEX|Nifty Fin Service"
    }
EQUITY_SYMBOLS = {
        "ONGC": "NSE_EQ|INE213A01029",
        "WIPRO": "NSE_EQ|INE075A01022",
        "BHARTIARTL": "NSE_EQ|INE397D01024",
        "TCS": "NSE_EQ|INE467B01029",
        "COALINDIA": "NSE_EQ|INE522F01014",
        "POWERGRID": "NSE_EQ|INE752E01010",
        "SUNPHARMA": "NSE_EQ|INE044A01036",
        "CIPLA": "NSE_EQ|INE059A01026",
        "GRASIM": "NSE_EQ|INE047A01021",
        "HDFCLIFE": "NSE_EQ|INE795G01014",
        "ITC": "NSE_EQ|INE154A01025",
        "HINDALCO": "NSE_EQ|INE038A01020",
        "APOLLOHOSP": "NSE_EQ|INE437A01024",
        "NTPC": "NSE_EQ|INE733E01010",
        "NESTLEIND": "NSE_EQ|INE239A01024",
        "INFY": "NSE_EQ|INE009A01021",
        "ULTRACEMCO": "NSE_EQ|INE481G01011",
        "KOTAKBANK": "NSE_EQ|INE237A01036",
        "MAXHEALTH": "NSE_EQ|INE027H01010",
        "TATACONSUM": "NSE_EQ|INE192A01025",
        "SBILIFE": "NSE_EQ|INE123W01016",
        "TITAN": "NSE_EQ|INE280A01028",
        "AXISBANK": "NSE_EQ|INE238A01034",
        "DRREDDY": "NSE_EQ|INE089A01031",
        "HCLTECH": "NSE_EQ|INE860A01027",
        "TECHM": "NSE_EQ|INE669C01036",
        "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
        "ICICIBANK": "NSE_EQ|INE090A01021",
        "TATASTEEL": "NSE_EQ|INE081A01020",
        "BEL": "NSE_EQ|INE263A01024",
        "TRENT": "NSE_EQ|INE849A01020",
        "LT": "NSE_EQ|INE018A01030",
        "JSWSTEEL": "NSE_EQ|INE019A01038",
        "JIOFIN": "NSE_EQ|INE758E01017",
        "MARUTI": "NSE_EQ|INE585B01010",
        "ADANIPORTS": "NSE_EQ|INE742F01042",
        "M&M": "NSE_EQ|INE101A01026",
        "ASIANPAINT": "NSE_EQ|INE021A01026",
        "EICHERMOT": "NSE_EQ|INE066A01021",
        "HINDUNILVR": "NSE_EQ|INE030A01027",
        "BAJAJFINSV": "NSE_EQ|INE918I01026",
        "HDFCBANK": "NSE_EQ|INE040A01034",
        "ADANIENT": "NSE_EQ|INE423A01024",
        "SBIN": "NSE_EQ|INE062A01020",
        "ETERNAL": "NSE_EQ|INE758T01015",
        "BAJFINANCE": "NSE_EQ|INE296A01032",
        "INDIGO": "NSE_EQ|INE646L01027",
        "RELIANCE": "NSE_EQ|INE002A01018",
        "TMPV": "NSE_EQ|INE155A01022",
        "SHRIRAMFIN": "NSE_EQ|INE721A01047",
    }
SYMBOL_REGISTRY = {
    "INDEX":  INDEX_SYMBOLS,
    "EQUITY": EQUITY_SYMBOLS,
}
def resolve_symbol_map(mode: str) -> dict:
    """
    Returns the correct symbol map based on the trading mode.
    Raises ValueError for unsupported modes.
    """
    symbol_map = SYMBOL_REGISTRY.get(mode.upper())
    if symbol_map is None:
        raise ValueError(f"Unsupported mode '{mode}'. Expected one of: {list(SYMBOL_REGISTRY.keys())}")
    return symbol_map