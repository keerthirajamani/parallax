from dhanhq import dhanhq

dhan = dhanhq("i am id")


# Place an order for Equity Cash
# print(dhan.place_order(security_id='11184',            # HDFC Bank
#     exchange_segment=dhan.NSE,
#     transaction_type=dhan.BUY,
#     quantity=1,
#     order_type=dhan.MARKET,
#     product_type=dhan.CNC,
#     price=0))
    

  
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