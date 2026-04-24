import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")
REGISTRY_KEY = "accounts/registry.json"


def load_accounts(bucket: str = S3_BUCKET) -> list[dict]:
    """
    Load and return all enabled accounts from S3 registry.

    Expected registry shape:
        [
          {
            "account_id": "alice",
            "client_id":  "1107245176",
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

    enabled = [a for a in accounts if a.get("enabled", True)]
    logger.info("account_registry: loaded %d enabled account(s)", len(enabled))
    return enabled
