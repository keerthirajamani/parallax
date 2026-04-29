PRODUCT_TYPE_MAP = {
    "CNC":    "CNC",       # delivery
    "INTRA":  "INTRADAY",     # intraday (INTRADAY)
    "MARGIN": "MARGIN",    # overnight margin
    "CO":     "CO",        # cover order
    "BO":     "BO",        # bracket order
    "MTF":    "MTF",       # margin trade funding
    }

ORDER_TYPE_MAP = {
    "MARKET": "MARKET",
    "LIMIT":  "LIMIT",
    "SL":     "STOP_LOSS",        # STOP_LOSS (limit-triggered)
    "SLM":    "STOP_LOSS_MARKET",       # STOP_LOSS_MARKET (market-triggered)
}

TRANSACTION_TYPE_MAP = {
    "BUY":  "BUY",
    "SELL": "SELL",
}
EXCHANGE_TYPE_MAP = {
    "NSE" : "NSE_EQ",
    # "BSE" : "BSE_EQ",
    # "CUR" : "NSE_CURRENCY",
    # "MCX" : "MCX_COMM",
    # "FNO" : "NSE_FNO",
    # "NSE_FNO" : "NSE_FNO",
    # "BSE_FNO" : "BSE_FNO",
    # "INDEX" : "IDX_I"
}


def place_order(client, sig: dict, side: str, qty: int, order_type="MARKET", product_type="CNC") -> str:
    resp = client.place_order(
        security_id=sig["security_id"],
        exchange_segment=sig["exchange"],
        transaction_type=TRANSACTION_TYPE_MAP[side.upper()],
        quantity=qty,
        order_type=ORDER_TYPE_MAP[order_type.upper()],
        product_type=PRODUCT_TYPE_MAP[product_type.upper()],
        price=0,
    )
    if resp.get("status") == "failure":
        print("resp", resp)
        raise RuntimeError(resp.get("remarks", "unknown error"))
    return resp.get("data", {}).get("orderId", "")

def get_current_holding(client):
    response = client.get_holdings()
    return response

def place_forever_order(client, 
                        security_id:int, 
                        quantity:int, 
                        price:float, 
                        trigger_Price:float,
                        is_oco=0,
                        order_flag="OCO",
                        price1=0,
                        trigger_Price1=0,
                        exchange="NSE", 
                        side="SELL", 
                        order_type="LIMIT", 
                        product_type="CNC") -> str:
    
    print("\nPlacing Forever Order (Single)...")
    if not is_oco:
        try:
            response = client.place_forever(
                security_id=security_id,
                exchange_segment=EXCHANGE_TYPE_MAP[exchange.upper()],
                transaction_type=TRANSACTION_TYPE_MAP[side.upper()],
                order_type=ORDER_TYPE_MAP[order_type.upper()],
                product_type=PRODUCT_TYPE_MAP[product_type.upper()],
                quantity=quantity,
                price=price,
                trigger_Price=trigger_Price
            )
            print(response)
        except Exception as e:
            print(f"Error placing forever order: {e}")
    elif is_oco:
        print("\nPlacing Forever Order (OCO)...")
        try:
            response = client.place_forever(
                security_id=security_id,
                exchange_segment=EXCHANGE_TYPE_MAP[exchange.upper()],
                transaction_type=TRANSACTION_TYPE_MAP[side.upper()],
                order_type=ORDER_TYPE_MAP[order_type.upper()],
                product_type=PRODUCT_TYPE_MAP[product_type.upper()],
                quantity=quantity,
                price=price,
                trigger_Price=trigger_Price,
                order_flag="OCO",
                price1=price1,          # Stop Loss Price
                trigger_Price1=trigger_Price1   # Stop Loss Trigger Price
            )
            print(response)
        except Exception as e:
            print(f"Error placing OCO forever order: {e}")
        print("\nPlacing Forever Order (OCO)...")