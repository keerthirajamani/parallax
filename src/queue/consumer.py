import os
import json
import signal
import logging
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sqs-consumer")

# QUEUE_URL          = os.environ["SQS_QUEUE_URL"]
QUEUE_URL          = "https://sqs.us-east-1.amazonaws.com/719211780716/parallax-signals"
REGION             = os.environ.get("AWS_REGION", "us-east-1")
MAX_MESSAGES       = int(os.environ.get("SQS_MAX_MESSAGES", "10"))   # 1-10
WAIT_SECONDS       = int(os.environ.get("SQS_WAIT_SECONDS", "20"))   # long poll, max 20
VISIBILITY_TIMEOUT = int(os.environ.get("SQS_VISIBILITY", "60"))     # give yourself time to process

sqs = boto3.client("sqs", region_name=REGION)

_shutdown = False
def _handle_signal(signum, _frame):
    global _shutdown
    log.info("Received signal %s, shutting down after current batch...", signum)
    _shutdown = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def process(message: dict) -> None:
    """Your business logic. Raise to leave the message on the queue (it'll retry)."""
    body = message["Body"]
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = body
    log.info("Processing message %s: %r", message["MessageId"], payload)
    # ... do real work here ...


def receive_batch():
    return sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=MAX_MESSAGES,
        WaitTimeSeconds=WAIT_SECONDS,
        VisibilityTimeout=VISIBILITY_TIMEOUT,
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
    ).get("Messages", [])


def delete_batch(entries):
    if not entries:
        return
    resp = sqs.delete_message_batch(QueueUrl=QUEUE_URL, Entries=entries)
    for failure in resp.get("Failed", []):
        log.error("Failed to delete %s: %s", failure["Id"], failure.get("Message"))


def main():
    log.info("Polling %s (region=%s)", QUEUE_URL, REGION)
    while not _shutdown:
        try:
            messages = receive_batch()
        except ClientError as e:
            log.exception("receive_message failed: %s", e)
            continue

        if not messages:
            continue  # long poll just timed out

        to_delete = []
        for msg in messages:
            try:
                process(msg)
                to_delete.append({"Id": msg["MessageId"], "ReceiptHandle": msg["ReceiptHandle"]})
            except Exception:
                log.exception("Handler failed for %s; leaving on queue for retry", msg["MessageId"])

        try:
            delete_batch(to_delete)
        except ClientError as e:
            log.exception("delete_message_batch failed: %s", e)

    log.info("Stopped.")


if __name__ == "__main__":
    main()