import json
import os

import requests

_raw = os.environ.get("IN_INDEX_WEBHOOK_URLS", "{}")
_WEBHOOK_URLS: dict = json.loads(_raw)
 

def send_to_webhook(payload: dict) -> None:
    print("triggerting webhook")
    for signal in payload.get("signals", []):
        print("signal", signal)
        symbol      = signal.get("symbol", "").lower()
        signal_type = signal.get("signal_type")

        if signal_type not in ("buy", "sell"):
            continue

        url = _WEBHOOK_URLS.get(symbol, {}).get(signal_type, "")
        print("url", url)
        if not url:
            print(f"webhook_trigger: no URL configured for {symbol} {signal_type}")
            continue

        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"webhook_trigger: {symbol} {signal_type} → {resp.status_code}")
