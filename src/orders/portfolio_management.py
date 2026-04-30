from src.orders.brokers import dhan as dhan_broker
from src.orders.order_placement import load_accounts, _prefetch_clients
from src.utils.position_sizer import calculate_percentage

accounts = load_accounts(market="india")
clients  = _prefetch_clients(accounts)

results = {}
for account in accounts:
    account_id = account["account_id"]
    client = clients[account_id]
    holdings = dhan_broker.get_current_holding(client)
    print("\ncurrent holdings",holdings)
    current_fo_orders = dhan_broker.get_forever_order(client)
    print("\ncurrent fo orders",current_fo_orders)
    existing_fo_map = {order['tradingSymbol']: order for order in current_fo_orders}
    print("\nexisting fo orders",existing_fo_map)
    for holding in holdings:
        print("\nExecuting for ",holding)
        tgt_price = round(holding.get('avgCostPrice') + calculate_percentage(holding.get('avgCostPrice')),2)
        print(f"{holding.get('dpQty')}|{holding.get('tradingSymbol')}@{holding.get('avgCostPrice')}|tgt@{tgt_price}|ltp@{holding['lastTradedPrice']}")
        if holding.get('tradingSymbol') in existing_fo_map:
            existing_fo_order = existing_fo_map.get(holding.get('tradingSymbol'))
            order_info = {
                'orderId': existing_fo_order.get('orderId'),
                'orderFlag': existing_fo_order.get('orderType'),
                'legName': existing_fo_order.get('legName'),
                }
            print(f"order_info {order_info}")
            print(f"\nFo order is already Exists {holding.get('tradingSymbol')}")
            dhan_broker.modify_forever_order(client, order_info.get('orderId'), holding.get('dpQty'), tgt_price, tgt_price, order_info.get('orderFlag'), order_info.get('legName'))
        else:
            print(f"\nfo not exists for {holding.get('tradingSymbol')}")
            dhan_broker.place_forever_order(client, holding.get('securityId'), holding.get('dpQty'), tgt_price, tgt_price)