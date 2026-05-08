import json
import os

import boto3

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _client


def publish_signal(payload: dict) -> None:
    queue_url = os.environ.get("SIGNALS_QUEUE_URL")
    _get_client().send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
