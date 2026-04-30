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
    print("\nPlacing Order ...")
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
    print("\nGetting Holding ...")
    holdings = client.get_holdings()
    extracted_data = []
    if holdings['status'] == 'success':
        for stock in holdings['data']:
            if stock['dpQty']>0: #filters only settled stock
                extracted_data.append({
                    'tradingSymbol': stock['tradingSymbol'],
                    'securityId': stock['securityId'],
                    'dpQty': stock['dpQty'],
                    'avgCostPrice': stock['avgCostPrice'],
                    'lastTradedPrice': stock['lastTradedPrice']
                })
    return extracted_data

def place_forever_order(client, 
                        security_id:int, 
                        quantity:int, 
                        price:float, 
                        trigger_Price:float,
                        is_oco=False,
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

def get_forever_order(client):
    print("\nGetting Forever order ...")
    forever_orders = client.get_forever()
    extracted_data = []
    if forever_orders['status'] == 'success':
        for stock in forever_orders['data']:
            extracted_data.append({
                'dhanClientId': stock['dhanClientId'],
                'orderId': stock['orderId'],
                'orderStatus': stock['orderStatus'],
                'transactionType': stock['transactionType'],
                'productType': stock['productType'],
                'orderType': stock['orderType'],
                'tradingSymbol': stock['tradingSymbol'],
                'securityId': stock['securityId'],
                'quantity': stock['quantity'],
                'price': stock['price'],
                'triggerPrice': stock['triggerPrice'],
                'legName': stock['legName']                
            })
    return extracted_data

def modify_forever_order(client, order_id, quantity, price, trigger_price, order_flag, leg_name, order_type="LIMIT", disclosed_quantity=0, validity="DAY"):
    print("\nModifying Forever Order ...")
    modify_forever_orders = client.modify_forever(order_id, order_flag, order_type, leg_name,
                       quantity, price, trigger_price, disclosed_quantity, validity)
    
    return modify_forever_orders
