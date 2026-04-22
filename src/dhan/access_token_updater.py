import json
import os
import requests

from src.utils.common_utils import get_token_from_s3, write_to_s3

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
S3_BUCKET = os.environ.get("BUCKET", "nse-artifacts")
S3_KEY = "dhan/token.json"


def lambda_handler(event, context):
    print("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    print("S3_BUCKET", S3_BUCKET)
    ACCESS_TOKEN = get_token_from_s3(S3_BUCKET, S3_KEY)

    response = requests.get(
        "https://api.dhan.co/v2/RenewToken",
        headers={
            "access-token": ACCESS_TOKEN,
            "dhanClientId": DHAN_CLIENT_ID,
            "Content-Type": "application/json",
        }
    )
    response.raise_for_status()
    data = response.json()

    if "errorCode" in data:
        raise Exception(f"{data['errorCode']} - {data['errorMessage']}")

    new_token = data["token"]

    write_to_s3(S3_BUCKET, S3_KEY, json.dumps({"token": new_token}).encode("utf-8"), "application/json")

    print(f"Token refreshed and saved to s3://{S3_BUCKET}/{S3_KEY}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Token refreshed successfully"})
    }
