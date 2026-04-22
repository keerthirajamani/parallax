import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.common_utils import write_to_s3

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def log_executed_orders(orders: list[dict], bucket: str, key_prefix: str = "orders") -> str:
    """
    Write executed order records to S3 as a JSON file.

    Each record shape:
        symbol, security_id, exchange, indicator,
        qty, entry_price, stop_loss, target,
        order_id, forever_placed, timestamp
    """
    if not orders:
        return ""

    now_ist  = datetime.now(IST)
    date_str = now_ist.strftime("%Y-%m-%d")
    ts_str   = now_ist.strftime("%Y%m%dT%H%M%S")
    s3_key   = f"{key_prefix}/{date_str}/executed_{ts_str}.json"

    write_to_s3(bucket, s3_key, json.dumps(orders, indent=2).encode("utf-8"), "application/json")

    print(f"order_logger: wrote {len(orders)} order(s) to s3://{bucket}/{s3_key}")
    return s3_key
