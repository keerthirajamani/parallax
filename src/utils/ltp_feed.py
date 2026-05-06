import logging
import threading
from typing import Dict, List, Optional

import upstox_client

logger = logging.getLogger(__name__)

FEED_MODE_LTPC = "ltpc"
FEED_MODE_FULL = "full"


class LTPFeed:
    def __init__(self, access_token: str, mode: str = FEED_MODE_FULL):
        self._mode = mode
        self._lock = threading.Lock()
        self._ltps: Dict[str, float] = {}
        self._feeds: Dict[str, dict] = {}
        self._subscribed: List[str] = []
        self._connected = threading.Event()

        cfg = upstox_client.Configuration()
        cfg.access_token = access_token
        self._streamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(cfg))
        self._streamer.on("open", self._on_open)
        self._streamer.on("message", self._on_message)

    def start(self, instruments: List[str], timeout: float = 10) -> bool:
        self._subscribed = list(instruments)
        threading.Thread(target=self._streamer.connect, daemon=True).start()
        connected = self._connected.wait(timeout=timeout)
        if not connected:
            logger.error("LTPFeed: failed to connect within %ss", timeout)
        return connected

    def subscribe(self, instruments: List[str]) -> None:
        if not self._connected.is_set():
            self._subscribed.extend(instruments)
            return
        self._subscribed.extend(instruments)
        self._streamer.subscribe(instruments, self._mode)

    def get_ltp(self, instrument_key: str) -> Optional[float]:
        with self._lock:
            return self._ltps.get(instrument_key)

    def get_all_feeds(self) -> Dict[str, dict]:
        with self._lock:
            return dict(self._feeds)

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def _on_open(self):
        self._streamer.subscribe(self._subscribed, self._mode)
        self._connected.set()
        logger.info("LTPFeed: connected, subscribed %d instruments", len(self._subscribed))

    def _on_message(self, message):
        feeds = message.get("feeds") if isinstance(message, dict) else None
        if not feeds:
            return

        ltp_updates: Dict[str, float] = {}
        feed_updates: Dict[str, dict] = {}

        for ikey, payload in feeds.items():
            feed_updates[ikey] = payload
            ltpc = (
                payload.get("ltpc")
                or payload.get("fullFeed", {}).get("marketFF", {}).get("ltpc")
                or payload.get("fullFeed", {}).get("indexFF", {}).get("ltpc")
            )
            if ltpc and "ltp" in ltpc:
                ltp_updates[ikey] = ltpc["ltp"]

        with self._lock:
            self._feeds.update(feed_updates)
            self._ltps.update(ltp_updates)
