import os
import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# Avoid duplicate handlers in Lambda cold/warm starts
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_h)

IST = ZoneInfo("Asia/Kolkata")
Mode = Literal["INDEX"]
Side = Literal["buy", "sell", "sl"]


@dataclass(frozen=True)
class Config:
    # Staleness window in seconds (trading safety)
    stale_seconds: int = int(os.getenv("STALE_SECONDS", "900000000000000000000000"))

    # Concurrency
    max_workers: int = int(os.getenv("MAX_WEBHOOK_WORKERS", "10"))

    # HTTP timeouts
    connect_timeout: float = float(os.getenv("CONNECT_TIMEOUT", "5"))
    read_timeout: float = float(os.getenv("READ_TIMEOUT", "20"))

    # Retry/backoff for transient network / 5xx
    retries: int = int(os.getenv("WEBHOOK_RETRIES", "2"))
    backoff_sec: float = float(os.getenv("WEBHOOK_BACKOFF_SEC", "0.5"))


# Keep your map, but PLEASE move these URLs to env/secrets if you consider them sensitive.
WEBHOOK_MAP: Dict[str, Dict[str, str]] = {
    'NIFTY': {
        'buy':  'https://www.quantman.trade/external_signal/Z2xQOGhFZVRUTjMzQzd3N0c2eFJ1K2RzaTQwR2NTdTdza3hVVmVxaWVQbzJtNEFpM1F2YjJHbGJTckVXdFJsb2tFSHk0M0dyc2k4WmRBZFRzd3BTeGc9PS0tY0FHeTloTlZ4dk9mLzdNRXFOYkVPQT09--262f947366250e523ec19dfc41ca60b28903d7d1',
        'sell': 'https://www.quantman.trade/external_signal/QVpzMHFCcUpxaUNITkVqb3Z2UWFHelRoZWhhaXpsWEx4Qi8vUXpDWEZZTEFaT1ZUeXFEY1VTdHR1dEc1WjRsMUYzQXlhTU55Y3pTYVJJVUM1b05mVHc9PS0tQi9pR1FrMDBkbjRTenVFbktQQzZUZz09--93b26b023744b730268c4f1af4c0e6282486b5d3',
        'sl':'sl_hit_placeholder'
    },
    'FINNIFTY': {
        'buy':  'https://www.quantman.trade/external_signal/d0JIaXlEclIzR1dPdzJMbGVHbVRXakk1dmVlK254TER4R2FtN3lpZ0xpR1c4alRubWVKNkxSUEI5U09pVmFqSDVkQktZN0ZjWVp3R1N6aDdjcG5uYXc9PS0tYzdRQzU0Qy96RGkvdkN5TVhpS05ldz09--ccf06b6e04325507a4a27d347a1fa45c870ded42',
        'sell': 'https://www.quantman.trade/external_signal/cVN6aUFOM21VUDEwd0UzbWtuVCtGbmFPUTlJMUVWMkp1YTk1emtwM29mTWZiZGlXUmcrMWI3cGFTeXpsOWZmZms5cFEzNEpkdWdlZDZwVjQxZWVSTXc9PS0tWUZoRTlQVkJ2SklZNlNSTkEvLzVrUT09--93d4cdb4e189afb20e72aae99a3e3141be94ecb0',
        'sl':'sl_hit_placeholder'
    },
    'BANKNIFTY': {
        'buy':  'https://www.quantman.trade/external_signal/K2xrZ09xQm44SmVMN04rZDl0Q3U5TGI2L0hodXdLNjNwWFB4c0lHWXNLdjZzSEdPbHJMd2pPMWFVKzE2aUtBdWFITUJ0QjZ6WXRoQlRvUitXQnRqR0E9PS0tVjM1R2pIZm5nUzlwb2J1VHBCY1BJQT09--4e806bc2965b57742d7c717e81be6c006dab6613',
        'sell': 'https://www.quantman.trade/external_signal/UDdOTWJTZUlMbjY3Vmx2TjFlSy8wYkVmSWZ1UG9KYnMyYlJ2R1I5WVh5K25mQm9wdE9sUm42K3grd3BVQU9NV3h0SW5hTGNkdUcvOUt5NW11dGswN3c9PS0tdU4vejBKTWJKWFBEZ1UvQ3BheFZNdz09--7c59778f8dd89056bbdf0a8cfb6e22a883c028f3',
        'sl':'sl_hit_placeholder'
    }
}

def build_session(cfg: Config) -> requests.Session:
    """
    Requests Session with connection pooling + urllib3 retry for idempotent-ish failures.
    Note: POST retries are controversial; we keep retries small and only for network/5xx.
    """
    s = requests.Session()

    retry = Retry(
        total=cfg.retries,
        connect=cfg.retries,
        read=cfg.retries,
        backoff_factor=cfg.backoff_sec,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,  # we'll raise manually
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=50)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# Build once per container (Lambda warm reuse)
CFG = Config()
SESSION = build_session(CFG)


def get_webhook_url(symbol: str, side: Side) -> str:
    try:
        print(f"webhook url is :: {WEBHOOK_MAP[symbol][side]}")
        return WEBHOOK_MAP[symbol][side]
    except KeyError as e:
        raise ValueError(f"Webhook URL not found for symbol={symbol} side={side}") from e


def parse_signal_timestamp(ts: str) -> datetime:
    """
    Accepts ISO strings with/without timezone.
    - If tz-aware: keep as is.
    - If tz-naive: assume IST (because you generate in IST upstream).
    """
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt


def is_stale(signal_ts: str, cfg: Config) -> bool:
    dt = parse_signal_timestamp(signal_ts)
    now = datetime.now(IST)
    age = (now - dt.astimezone(IST)).total_seconds()
    return age > cfg.stale_seconds


def trigger_webhook(session: requests.Session, signal: Dict[str, Any], cfg: Config) -> str:
    symbol = signal.get("symbol")
    side = signal.get("signal_type")
    print(f"Triggering a webhook for side {side} on symbol {symbol}")

    if not symbol or side not in ("buy", "sell", "sl"):
        return "INVALID_SIGNAL"

    try:
        webhook_url = get_webhook_url(symbol, side)  # type: ignore[arg-type]

        payload = {
            "symbol": symbol,
            "exchange_token": signal.get("exchange_token"),
            "side": side,
            "close": signal.get("close"),
            "tsl": signal.get("tsl"),
            "timestamp": signal.get("timestamp"),
        }

        resp = session.post(
            webhook_url,
            json=payload,
            timeout=(cfg.connect_timeout, cfg.read_timeout),
        )

        # Treat non-2xx as failure with context
        if not (200 <= resp.status_code < 300):
            logger.error(
                "webhook_non_2xx symbol=%s side=%s status=%s body=%s",
                symbol, side, resp.status_code, resp.text[:300],
            )
            return "WEBHOOK_FAILED"

        return "WEBHOOK_SENT"

    except Exception:
        logger.exception("webhook_exception symbol=%s side=%s", symbol, side)
        return "WEBHOOK_FAILED"


def process_signal(signal: Dict[str, Any], mode: str, cfg: Config) -> Dict[str, Any]:
    symbol = signal.get("symbol")
    side = signal.get("signal_type")
    ts = signal.get("timestamp")

    if mode != "INDEX":
        return {"symbol": symbol, "side": side, "status": "INVALID_MODE"}

    if not ts:
        return {"symbol": symbol, "side": side, "status": "MISSING_TIMESTAMP"}

    # Stale check (trading safety)
    try:
        if is_stale(ts, cfg):
            return {"symbol": symbol, "side": side, "status": "STALE_SKIPPED"}
    except Exception:
        logger.exception("timestamp_parse_failed symbol=%s side=%s ts=%s", symbol, side, ts)
        return {"symbol": symbol, "side": side, "status": "BAD_TIMESTAMP"}

    # status = trigger_webhook(SESSION, signal, cfg)
    # return {"symbol": symbol, "side": side, "status": status}
    return {"symbol": symbol, "side": side, "status": "status"}


def index_signal_webhook_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Safe logging: don't log massive payloads fully
    print(f"event_received {event}")
    mode = event.get("mode")
    signals = event.get("signals") or []

    if not signals:
        return {"status": "NO_SIGNAL", "processed_count": 0, "results": [], "timestamp": datetime.now(IST).isoformat()}

    # Guardrails
    workers = max(1, min(CFG.max_workers, len(signals)))
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(process_signal, s, mode, CFG) for s in signals]

        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                logger.exception("process_signal_unhandled")
                results.append({"symbol": None, "side": None, "status": "PROCESSING_FAILED"})

    processed = len(results)
    sent = sum(1 for r in results if r.get("status") == "WEBHOOK_SENT")
    failed = sum(1 for r in results if r.get("status") in ("WEBHOOK_FAILED", "PROCESSING_FAILED"))
    stale = sum(1 for r in results if r.get("status") == "STALE_SKIPPED")

    logger.info(
        "event_processed processed=%d sent=%d failed=%d stale=%d",
        processed, sent, failed, stale
    )

    return {
        "status": "PROCESSED",
        "mode": mode,
        "processed_count": processed,
        "summary": {"sent": sent, "failed": failed, "stale_skipped": stale},
        "results": results,
        "timestamp": datetime.now(IST).isoformat(),
    }