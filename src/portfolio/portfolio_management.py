import traceback

from src.brokers import dhan as dhan_broker
from src.orders.order_placement import load_accounts, _prefetch_clients
from src.utils.position_sizer import calculate_percentage

US_ENTITIES = {"us_equity", "us_index"}

# market = "us" if entity.lower() in US_ENTITIES else "india"


def portfolio_lambda_handler(event, _context):
    market   = event.get("market")
    accounts = load_accounts(market=market)
    clients  = _prefetch_clients(accounts)

    for account in accounts:
        account_id = account["account_id"]
        client = clients[account_id]

        try:
            holdings = dhan_broker.get_current_holding(client)
            print("\ncurrent holdings", holdings)
            current_fo_orders = dhan_broker.get_forever_order(client)
            print("\ncurrent fo orders", current_fo_orders)
            existing_fo_map = {order['tradingSymbol']: order for order in current_fo_orders}
            print("\nexisting fo orders", existing_fo_map)
        except Exception:
            print(f"\n[ERROR] Failed to fetch data for account {account_id}")
            traceback.print_exc()
            continue

        for holding in holdings:
            try:
                print("\nExecuting for ", holding)
                tgt_price = round(holding.get('avgCostPrice') + calculate_percentage(holding.get('avgCostPrice')), 2)
                print(f"{holding.get('dpQty')}|{holding.get('tradingSymbol')}@{holding.get('avgCostPrice')}|tgt@{tgt_price}|ltp@{holding['lastTradedPrice']}")

                if holding.get('tradingSymbol') in existing_fo_map:
                    existing_fo_order = existing_fo_map.get(holding.get('tradingSymbol'))
                    order_info = {
                        'orderId': existing_fo_order.get('orderId'),
                        'orderFlag': existing_fo_order.get('orderType'),
                        'legName': existing_fo_order.get('legName'),
                    }
                    print(f"order_info {order_info}")
                    print(f"\nForever Order already exists for {holding.get('tradingSymbol')}")
                    dhan_broker.modify_forever_order(client, order_info.get('orderId'), holding.get('dpQty'), tgt_price, tgt_price, order_info.get('orderFlag'), order_info.get('legName'))
                else:
                    print(f"\nForever Order doesn't exists for {holding.get('tradingSymbol')}")
                    dhan_broker.place_forever_order(client, holding.get('securityId'), holding.get('dpQty'), tgt_price, tgt_price)

            except Exception:
                print(f"\n[ERROR] Failed to process {holding.get('tradingSymbol')} in account {account_id}")
                traceback.print_exc()


if __name__ == "__main__":
    portfolio_lambda_handler()
