import logging
import time

from src.utils.ltp_feed import LTPFeed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

token = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzUkNLNTYiLCJqdGkiOiI2OWM3N2JlMmVmZmU0ODJmNzA5NmM0YzIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc3NDY4MTA1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODA2MjcxMjAwfQ.tOVcAfz7htW1OPhPQdxvmu-Uc5HviBvDu3lFYTyUjdg"

INDEX_INSTRUMENTS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Fin Service",
    "BSE_INDEX|SENSEX",
]

EQUITY_INSTRUMENTS = [
    "NSE_EQ|INE040A01034",  # HDFCBANK
]

if __name__ == "__main__":
    feed = LTPFeed(token, mode="full")
    connected = feed.start(INDEX_INSTRUMENTS)

    if not connected:
        raise RuntimeError("Feed failed to connect")

    feed.subscribe(EQUITY_INSTRUMENTS)

    while True:
        print(feed.get_all_feeds())
        time.sleep(1)
