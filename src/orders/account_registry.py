import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")
REGISTRY_KEY = "accounts/registry.json"


def load_accounts(broker: str | None = None, bucket: str = S3_BUCKET) -> list[dict]:
    """
    Load enabled accounts from S3 registry.
    Pass broker="dhan" or broker="zerodha" to filter by broker.
    Pass broker=None (default) to load all enabled accounts.

    Expected registry shape:
        [
          {
            "account_id": "alice",
            "broker": "dhan",
            "client_id": "12345678",
            "token_s3_key": "accounts/alice/token.json",
            "max_trade_capital": 10000,
            "enabled": true
          },
          {
            "account_id": "charlie",
            "broker": "zerodha",
            "client_id": "ZX1234",
            "api_key": "zerodha_api_key",
            "token_s3_key": "accounts/charlie/token.json",
            "max_trade_capital": 8000,
            "enabled": true
          }
        ]
    """
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=REGISTRY_KEY)
    accounts = json.loads(response["Body"].read().decode("utf-8"))

    filtered = [
        a for a in accounts
        if a.get("enabled", True) and (broker is None or a.get("broker") == broker)
    ]
    label = broker if broker else "all"
    print(f"account_registry: loaded {len(filtered)} enabled {label} account(s)")
    return filtered
