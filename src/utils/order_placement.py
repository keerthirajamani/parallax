import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

IST = ZoneInfo("Asia/Kolkata")

session = requests.Session()




def process_equity_signal(signal):
    try:
        print(f"Processing EQUITY: {signal['symbol']}")
        # place_equity_order(signal)
        return "EQUITY_PROCESSED"

    except Exception as e:
        logger.error(f"Equity processing failed: {str(e)}")
        return "EQUITY_FAILED"


def process_signal(signal, mode):

    if mode == "EQUITY":
        result = process_equity_signal(signal)
    else:
        return {"symbol": signal["symbol"], "side": signal["side"], "status": "INVALID_MODE"}

    return {
        "symbol": signal["symbol"],
        "side": signal["side"],
        "status": result
    }


def order_execution(event, context):
    

    logger.info(f"Event received: {json.dumps(event)}")

    mode = event.get("mode")
    signals = event.get("signals", [])
    
    if mode not in "EQUITY":
        return {"status": "ERROR", "message": f"Invalid MODE: {mode}"}
    
    if not signals:
        return {"status": "NO_SIGNAL", "processed": 0}

    results = []

    max_workers = min(25, len(signals))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_signal, signal, mode)
            for signal in signals
        ]

        for future in as_completed(futures):
            results.append(future.result())

    return {
        "status": "PROCESSED",
        "mode": mode,
        "processed_count": len(results),
        # "results": results,
        "timestamp": datetime.now(IST).isoformat()
    }