import boto3

def send_email_ses(
    subject: str,
    body: str,
    sender: str,
    recipients: list,
    region: str = "us-east-1"
):
    """
    subject: str,
    body: str,
    sender: str,
    recipients: list
    """
    ses = boto3.client("ses", region_name=region)

    response = ses.send_email(
        Source=sender,
        Destination={
            "ToAddresses": recipients
        },
        Message={
            "Subject": {
                "Data": subject,
                "Charset": "UTF-8"
            },
            "Body": {
                "Text": {
                    "Data": body,
                    "Charset": "UTF-8"
                }
            }
        }
    )

    return response["MessageId"]
