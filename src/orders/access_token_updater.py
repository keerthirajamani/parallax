import json
import logging
import os

import requests

from src.orders.account_registry import load_accounts
from src.utils.common_utils import get_token_from_s3, write_to_s3

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("BUCKET", "us-east-1-parallax-bucket")


def lambda_handler(event, context):
    accounts = load_accounts()
    results = {}

    for account in accounts:
        account_id = account["account_id"]
        try:
            _refresh_token(account)
            results[account_id] = "ok"
        except Exception as exc:
            print(f"token_refresh: account={account_id} failed: {exc}")
            results[account_id] = f"error: {exc}"

    print(f"token_refresh results: {results}")
    return {"statusCode": 200, "body": json.dumps(results)}


def _refresh_token(account: dict) -> None:
    broker = account.get("broker")

    if broker == "dhan":
        _refresh_dhan_token(account)
    elif broker == "zerodha":
        _refresh_zerodha_token(account)
    else:
        raise ValueError(f"Unsupported broker: {broker!r} for account={account['account_id']}")


def _refresh_dhan_token(account: dict) -> None:
    account_id = account["account_id"]
    token_key  = account["token_s3_key"]

    current_token = get_token_from_s3(S3_BUCKET, token_key)

    response = requests.get(
        "https://api.dhan.co/v2/RenewToken",
        headers={
            "access-token": current_token,
            "dhanClientId": account["client_id"],
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    data = response.json()

    if "errorCode" in data:
        raise Exception(f"{data['errorCode']} - {data['errorMessage']}")

    _save_token(S3_BUCKET, token_key, data["token"])
    print(f"token_refresh: account={account_id} dhan token saved to s3://{S3_BUCKET}/{token_key}")


def _refresh_zerodha_token(account: dict) -> None:
    """
    Zerodha tokens cannot be auto-renewed via API — they require a login redirect.
    This is a placeholder; wire in your token generation flow here.
    """
    account_id = account["account_id"]
    raise NotImplementedError(
        f"token_refresh: account={account_id} zerodha tokens must be refreshed manually via login flow"
    )


def _save_token(bucket: str, key: str, token: str) -> None:
    write_to_s3(bucket, key, json.dumps({"token": token}).encode("utf-8"), "application/json")
