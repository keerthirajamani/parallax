import sys
import json
import os
import io
import boto3
from datetime import datetime
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")

load_dotenv()

LOG_BUCKET = os.environ.get("SIGNALS_BUCKET", "us-east-1-parallax-bucket")
LOG_DIR = "/var/log/parallax"


def run_with_logging(label: str, fn):
    timestamp = datetime.now(IST).strftime("%Y-%m-%d_%H-%M-%S")
    s3_key = f"logs/{label}/{timestamp}.log"

    buffer = io.StringIO()

    class Tee:
        def __init__(self):
            self._pending = ""

        def write(self, msg):
            self._pending += msg
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", 1)
                ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
                out = f"[{ts}] {line}\n"
                buffer.write(out)
                sys.__stdout__.write(out)

        def flush(self):
            if self._pending:
                ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
                out = f"[{ts}] {self._pending}"
                buffer.write(out)
                sys.__stdout__.write(out)
                self._pending = ""
            sys.__stdout__.flush()

    sys.stdout = Tee()
    sys.stderr = Tee()

    try:
        fn()
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        log_content = buffer.getvalue()

        os.makedirs(LOG_DIR, exist_ok=True)
        with open(f"{LOG_DIR}/{label}_{timestamp}.log", "w") as f:
            f.write(log_content)

        try:
            boto3.client("s3").put_object(
                Bucket=LOG_BUCKET,
                Key=s3_key,
                Body=log_content.encode("utf-8"),
                ContentType="text/plain",
            )
        except Exception as e:
            sys.__stdout__.write(f"Failed to upload log to S3: {e}\n")


mode = sys.argv[1]

if mode == "signals":
    from src.signals.signal_generation_engine import signal_lambda_handler
    from src.orders.order_placement import place_orders
    event = json.loads(sys.argv[2])
    should_place_orders = "--place-orders" in sys.argv
    entity = event.get("entity", "unknown").lower()
    unit = event.get("unit", "unknown").lower()

    if unit == "weeks":
        from src.utils.nse_utils import is_last_trading_day_of_week
        from datetime import date
        if not is_last_trading_day_of_week(date.today()):
            print(f"Skipping weekly EQUITY signals — {date.today()} is not the last trading day of the week")
            sys.exit(0)

    def run_signals():
        print(f"Signal Genaration Starting at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')} ")
        result = signal_lambda_handler(event, None, should_place_orders=should_place_orders)
        print(f"Signal Genaration Completed at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')} ")
        print(f"signals result: {json.dumps(result, default=str, indent=2)}")
        # if should_place_orders:
        #     print("placing orders...")
        #     order_results = place_orders(result, entity=entity)
        #     print(f"order results: {json.dumps(order_results, default=str, indent=2)}")
        #     print(f"Orders Completed at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')} ")
    run_with_logging(f"{entity}_{unit}", run_signals)

elif mode == "consumer":
    from src.queue.consumer import consume
    consume()

elif mode == "token_refresh":
    from src.orders.access_token_updater import token_lambda_handler

    def run_token():
        result = token_lambda_handler({}, None)
        print(f"token_refresh result: {json.dumps(result, default=str)}")

    run_with_logging("token_refresh", run_token)

elif mode == "forever_order_update":
    from src.portfolio.portfolio_management import forever_order_lambda_handler
    event = json.loads(sys.argv[2])
    def run_forever_update():
        result = forever_order_lambda_handler(event, None)
        print(f"portfolio_update result: {json.dumps(result, default=str)}")

    run_with_logging("portfolio_update", run_forever_update)