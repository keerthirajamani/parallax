import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")
REGISTRY_KEY = "accounts/registry.json"


def load_accounts(broker: str = "dhan", bucket: str = S3_BUCKET) -> list[dict]:
    """
    Load and return all enabled accounts for a given broker from S3 registry.

    Expected registry shape:
        [
          {
            "account_id": "alice",
            "broker": "dhan",
            "client_id":  "12345678",
            "token_s3_key": "accounts/alice/token.json",
            "max_trade_capital": 10000,
            "enabled": true
          },
          ...
        ]
    """
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=REGISTRY_KEY)
    accounts = json.loads(response["Body"].read().decode("utf-8"))

    filtered = [
        a for a in accounts
        if a.get("enabled", True) and a.get("broker") == broker
    ]
    logger.info("account_registry: loaded %d enabled %s account(s)", len(filtered), broker)
    return filtered
