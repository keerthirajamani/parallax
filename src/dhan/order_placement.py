from dhanhq import dhanhq
import os,sys
import numpy as np
from src.utils.common_utils import (
    get_token_from_s3,
)

S3_BUCKET = os.environ.get("BUCKET", "nse-artifacts")
S3_KEY="dhan/token.json"

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID","1107245176")
access_token = get_token_from_s3(S3_BUCKET, S3_KEY)

dhan = dhanhq(DHAN_CLIENT_ID,access_token)

signals = [{'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE795G01014', 'security_id': '467'}, 'interval': 1, 'signals': [{'symbol': 'HDFCLIFE', 'indicator': '2ut', 'close': 616.45, 'tsl': np.float64(637.255), 'timestamp': '2026-04-17T00:00:00+05:30', 'signal_type': 'sell'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE154A01025', 'security_id': '1660'}, 'interval': 1, 'signals': [{'symbol': 'ITC', 'indicator': '3hc', 'close': 306.8, 'tsl': np.float64(300.55), 'timestamp': '2026-04-17T00:00:00+05:30', 'signal_type': 'buy'}, {'symbol': 'ITC', 'indicator': '2ut', 'close': 306.8, 'tsl': np.float64(301.77500000000003), 'timestamp': '2026-04-17T00:00:00+05:30', 'signal_type': 'buy'}]}, {'mode': 'EQUITY', 'unit': 'days', 'instrument': {'exchange': 'NSE_EQ', 'isin': 'INE002A01018', 'security_id': '2885'}, 'interval': 1, 'signals': [{'symbol': 'RELIANCE', 'indicator': '3hc', 'close': 1365.0, 'tsl': np.float64(1330.0), 'timestamp': '2026-04-17T00:00:00+05:30', 'signal_type': 'buy'}]}]


buy_signals = [
    {**s, 'signals': [sig for sig in s['signals'] if sig['signal_type'] == 'buy']}
    for s in signals
    if any(sig['signal_type'] == 'buy' for sig in s['signals'])
]

sell_signals = [
    {**s, 'signals': [sig for sig in s['signals'] if sig['signal_type'] == 'sell']}
    for s in signals
    if any(sig['signal_type'] == 'sell' for sig in s['signals'])
]
print("buy_signals", buy_signals)

for buy in buy_signals:
    print("buy is ", buy)
    print("security_id is",buy['instrument']['security_id'])
    sys.exit("Planned Exit")
    print(dhan.place_order(security_id='11184',            # HDFC Bank
    exchange_segment=dhan.NSE,
    transaction_type=dhan.BUY,
    quantity=1,
    order_type=dhan.MARKET,
    product_type=dhan.CNC,
    price=0))
    sys.exit("Planned Exit")
# Place an order for Equity Cash

    

  
# Fetch all orders
print(dhan.get_order_list())

# # Get order by id
# dhan.get_order_by_id(order_id)

# # Modify order
# dhan.modify_order(order_id, order_type, leg_name, quantity, price, trigger_price, disclosed_quantity, validity)

# # Cancel order
# dhan.cancel_order(order_id)

# # Get order by correlation id
# dhan.get_order_by_corelationID(corelationID)

# # Get Instrument List
# dhan.fetch_security_list("compact")

# # Get positions
# dhan.get_positions()

# # Get holdings
# dhan.get_holdings()

# # Intraday Minute Data 
# dhan.intraday_minute_data(security_id, exchange_segment, instrument_type, from_date, to_date)

# # Historical Daily Data
# dhan.historical_daily_data(security_id, exchange_segment, instrument_type, from_date, to_date)

# # Expired Options Data
# dhan.expired_options_data(
#     security_id=13,
#     exchange_segment="NSE_FNO",
#     instrument_type="INDEX",
#     expiry_flag="MONTH",
#     expiry_code=1,
#     strike="ATM",
#     drv_option_type="CALL",
#     required_data=["open", "high", "low", "close", "volume"],
#     from_date="2023-01-01",
#     to_date="2023-01-31"
# )

# # Time Converter
# dhan.convert_to_date_time(EPOCH Date)

# # Get trade book
# dhan.get_trade_book(order_id)

# # Get trade history
# dhan.get_trade_history(from_date,to_date,page_number=0)

# # Get fund limits
dhan.get_fund_limits()

# # Generate TPIN
# dhan.generate_tpin()

# # Enter TPIN in Form
# dhan.open_browser_for_tpin(isin='INE00IN01015',
#     qty=1,
#     exchange='NSE')

# # EDIS Status and Inquiry
# dhan.edis_inquiry()

# # Expiry List of Underlying
# dhan.expiry_list(
#     under_security_id=13,                       # Nifty
#     under_exchange_segment="IDX_I"
# )

# # Option Chain
# dhan.option_chain(
#     under_security_id=13,                       # Nifty
#     under_exchange_segment="IDX_I",
#     expiry="2024-10-31"
# )

# # Market Quote Data                     # LTP - ticker_data, OHLC - ohlc_data, Full Packet - quote_data
# dhan.ohlc_data(
#     securities = {"NSE_EQ":[1333]}
# )

# # Place Forever Order (SINGLE)
# dhan.place_forever(
#     security_id="1333",
#     exchange_segment= dhan.NSE,
#     transaction_type= dhan.BUY,
#     order_type=dhan.LIMIT,
#     product_type=dhan.CNC,
#     quantity= 10,
#     price= 1900,
#     trigger_Price= 1950
# )