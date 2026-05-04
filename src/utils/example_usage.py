token = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIzUkNLNTYiLCJqdGkiOiI2OWM3N2JlMmVmZmU0ODJmNzA5NmM0YzIiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc3NDY4MTA1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODA2MjcxMjAwfQ.tOVcAfz7htW1OPhPQdxvmu-Uc5HviBvDu3lFYTyUjdg"

"""
Minimal Upstox LTP feed.

Just gives you `feed.get_ltp("NSE_EQ|INE040A01034")` and that's it.
"""

import os
import threading
import upstox_client
# from src.utils.ltp_feed import LTPFeed

class LTPFeed:
    def __init__(self, access_token):
        self._ltps = {}                    # instrument_key -> ltp
        self._subscribed = []
        self._connected = threading.Event()

        cfg = upstox_client.Configuration()
        cfg.access_token = access_token
        self._streamer = upstox_client.MarketDataStreamerV3(
            upstox_client.ApiClient(cfg),
        )
        self._streamer.on("open", self._on_open)
        self._streamer.on("message", self._on_message)

    def start(self, instruments):
        """Connect and subscribe. Blocks until first connection."""
        self._subscribed = instruments
        threading.Thread(target=self._streamer.connect, daemon=True).start()
        self._connected.wait(timeout=10)

    def get_ltp(self, instrument_key):
        """Return latest LTP, or None if not received yet."""
        return self._ltps.get(instrument_key)

    # ---- internal ----

    def _on_open(self):
        self._streamer.subscribe(self._subscribed, "ltpc")
        self._connected.set()

    def _on_message(self, message):
        print("message", message)
        feeds = message.get("feeds") if isinstance(message, dict) else None
        if not feeds:
            return
        for ikey, payload in feeds.items():
            # Handles both "ltpc" mode and "full" mode payloads
            ltpc = payload.get("ltpc") or \
                   payload.get("fullFeed", {}).get("marketFF", {}).get("ltpc") or \
                   payload.get("fullFeed", {}).get("indexFF", {}).get("ltpc")
            if ltpc and "ltp" in ltpc:
                self._ltps[ikey] = ltpc["ltp"]


# ---- usage ----

if __name__ == "__main__":
    import time

    feed = LTPFeed(token)
    feed.start(["NSE_EQ|INE040A01034"])

    while True:
        ltp = feed.get_ltp("NSE_EQ|INE040A01034")
        print(f"LTP: {ltp}")
        time.sleep(1)