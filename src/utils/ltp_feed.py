"""
Upstox LTP feed via WebSocket (MarketDataStreamerV3).

Usage:
    feed = LTPFeed(os.environ["UPSTOX_ACCESS_TOKEN"])
    feed.start(["NSE_EQ|INE040A01034"])
    ltp = feed.get_ltp("NSE_EQ|INE040A01034")  # float or None
"""

import logging
import os
import threading
from typing import Dict, List, Optional

import upstox_client

logger = logging.getLogger(__name__)

FEED_MODE_LTPC = "ltpc"
FEED_MODE_FULL = "full"


class LTPFeed:
    def __init__(self, access_token: str, mode: str = FEED_MODE_LTPC):
        self._mode = mode
        self._lock = threading.Lock()
        self._ltps: Dict[str, float] = {}
        self._subscribed: List[str] = []
        self._connected = threading.Event()

        cfg = upstox_client.Configuration()
        cfg.access_token = access_token
        self._streamer = upstox_client.MarketDataStreamerV3(
            upstox_client.ApiClient(cfg),
        )
        self._streamer.on("open", self._on_open)
        self._streamer.on("message", self._on_message)

    def start(self, instruments: List[str], timeout: float = 10) -> bool:
        """Connect and subscribe. Blocks until first connection or timeout."""
        self._subscribed = list(instruments)
        threading.Thread(target=self._streamer.connect, daemon=True).start()
        connected = self._connected.wait(timeout=timeout)
        if not connected:
            logger.error("LTPFeed: failed to connect within %ss", timeout)
        return connected

    def get_ltp(self, instrument_key: str) -> Optional[float]:
        """Return the latest LTP for an instrument, or None if not yet received."""
        with self._lock:
            return self._ltps.get(instrument_key)

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def subscribe(self, instruments: List[str]) -> None:
        """Add new instruments to the live feed after connection."""
        if not self._connected.is_set():
            logger.warning("LTPFeed: not connected yet, queuing instruments")
            self._subscribed.extend(instruments)
            return
        self._subscribed.extend(instruments)
        self._streamer.subscribe(instruments, self._mode)
        logger.info("LTPFeed: subscribed %d new instrument(s)", len(instruments))

    # ---- internal ----

    def _on_open(self):
        logger.info("LTPFeed: connected, subscribing %d instrument(s)", len(self._subscribed))
        self._streamer.subscribe(self._subscribed, self._mode)
        self._connected.set()

    def _on_message(self, message):
        feeds = message.get("feeds") if isinstance(message, dict) else None
        if not feeds:
            return

        updates: Dict[str, float] = {}
        for ikey, payload in feeds.items():
            ltpc = (
                payload.get("ltpc")
                or payload.get("fullFeed", {}).get("marketFF", {}).get("ltpc")
                or payload.get("fullFeed", {}).get("indexFF", {}).get("ltpc")
            )
            if ltpc and "ltp" in ltpc:
                updates[ikey] = ltpc["ltp"]

        if updates:
            with self._lock:
                self._ltps.update(updates)


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    token = os.environ.get("UPSTOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("UPSTOX_ACCESS_TOKEN environment variable is not set")

    feed = LTPFeed(token)
    feed.start(["NSE_EQ|INE040A01034"])

    while True:
        ltp = feed.get_ltp("NSE_EQ|INE040A01034")
        logger.info("LTP: %s", ltp)
        time.sleep(1)
