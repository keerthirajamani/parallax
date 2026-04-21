import subprocess
import json
import boto3
import os

DHAN_CLIENT_ID = os.environ.get("DHAN_CLIENT_ID")
S3_BUCKET = os.environ.get("BUCKET", "nse-artifacts")
S3_KEY = "dhan/token.json"

def get_token_from_s3():
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data["token"]

def is_error_response(response):
    if 'errorType' in response or 'errorCode' in response:
        print(f"Error: {response.get('errorCode')} - {response.get('errorMessage')}")
        return True
    return False

def lambda_handler(event, context):
    print("DHAN_CLIENT_ID",DHAN_CLIENT_ID)
    print("S3_BUCKET",S3_BUCKET)
    ACCESS_TOKEN = get_token_from_s3()

    result = subprocess.run([
        "curl",
        "--location",
        "https://api.dhan.co/v2/RenewToken",
        "--header", f"access-token: {ACCESS_TOKEN}",
        "--header", f"dhanClientId: {DHAN_CLIENT_ID}"
    ], capture_output=True, text=True)

    response = json.loads(result.stdout)
    try:
        if 'errorCode' in response:
            raise Exception(f"{response['errorCode']} - {response['errorMessage']}")
        new_token = response["token"]
    except Exception as e:
        print(f"Error: {e}")

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