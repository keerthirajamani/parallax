# from kiteconnect import KiteConnect
#
# def place_order(client, sig: dict, side: str, qty: int) -> str:
#     transaction_type = "BUY" if side == "buy" else "SELL"
#     order_id = client.place_order(
#         variety=KiteConnect.VARIETY_REGULAR,
#         exchange="NSE",
#         tradingsymbol=sig["symbol"],
#         transaction_type=transaction_type,
#         quantity=qty,
#         product=KiteConnect.PRODUCT_CNC,
#         order_type=KiteConnect.ORDER_TYPE_MARKET,
#     )
#     return str(order_id)
