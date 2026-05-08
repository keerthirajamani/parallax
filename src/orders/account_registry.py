import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")
REGISTRY_KEY = "accounts/registry.json"

# Brokers supported per market. "both" brokers appear in both sets.
MARKET_BROKERS = {
    "india": {"dhan", "zerodha", "indmoney"},
    "us":    {"indmoney", "alpaca"},
}


def load_accounts(market: str | None = None, broker: str | None = None, bucket: str = S3_BUCKET) -> list[dict]:
    """
    Load enabled accounts from S3 registry.

    market: "india" or "us" to filter by market. None loads all (used by token refresh).
    broker: filter by specific broker, None for all.
    Expected registry shape:
    [
      {
        "account_id": "alice",
        "broker": "indmoney",
        "market": ["india", "us"],
        "client_id":  "12345678",
        "token_s3_key": "accounts/alice/token.json",
        "market_config": {
          "india": { "max_trade_capital": 10000 },
          "us":    { "max_trade_capital": 500 }
        },
        "enabled": false
      },
      ...
  ]
    """
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=REGISTRY_KEY)
    accounts = json.loads(response["Body"].read().decode("utf-8"))

    filtered = []
    for a in accounts:
        account_id = a.get("account_id")

        if not a.get("enabled", True):
            continue

        if market is not None and market not in a.get("market", []):
            continue

        if broker is not None and a.get("broker") != broker:
            continue

        if market is not None:
            allowed = MARKET_BROKERS.get(market, set())
            if a.get("broker") not in allowed:
                print(f"account_registry: skipping account={account_id} — broker={a.get('broker')} not supported for market={market}")
                continue

        filtered.append(a)

    label = f"{market or 'all'} / {broker or 'all brokers'}"
    print(f"account_registry: loaded {len(filtered)} enabled account(s) [{label}]")
    return filtered