import json
import boto3
import os
import requests

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
S3_BUCKET = os.environ.get("BUCKET", "nse-artifacts")
S3_KEY = "dhan/token.json"


def get_token_from_s3():
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data["token"]


def lambda_handler(event, context):
    print("DHAN_CLIENT_ID", DHAN_CLIENT_ID)
    print("S3_BUCKET", S3_BUCKET)
    ACCESS_TOKEN = get_token_from_s3()

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

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=json.dumps({"token": new_token}),
        ContentType="application/json"
    )

    print(f"Token refreshed and saved to s3://{S3_BUCKET}/{S3_KEY}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Token refreshed successfully"})
    }
