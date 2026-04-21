import sys
import json
import os
import io
import boto3
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

LOG_BUCKET = os.environ.get("SIGNALS_BUCKET", "nse-artifacts")
LOG_DIR = "/var/log/parallax"


def run_with_logging(label: str, fn):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    s3_key = f"logs/{label}/{timestamp}.log"

    buffer = io.StringIO()

    class Tee:
        def write(self, msg):
            buffer.write(msg)
            sys.__stdout__.write(msg)
        def flush(self):
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
    from src.signals.signal_generation_engine import lambda_handler
    # TODO: from src.dhan.order_placement import place_orders
    event = json.loads(sys.argv[2])
    place_orders = "--place-orders" in sys.argv
    entity = event.get("entity", "unknown").lower()
    unit = event.get("unit", "unknown").lower()

    def run_signals():
        result = lambda_handler(event, None)
        print(f"signals result: {json.dumps(result, default=str, indent=2)}")
        if place_orders:
            print("placing orders...")
            # TODO: place_orders(result)

    run_with_logging(f"{entity}_{unit}", run_signals)

elif mode == "token_refresh":
    from src.dhan.access_token_updater import lambda_handler

    def run_token():
        result = lambda_handler({}, None)
        print(f"token_refresh result: {json.dumps(result, default=str)}")

    run_with_logging("token_refresh", run_token)
