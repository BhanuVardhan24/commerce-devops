"""Send, receive and delete only a uniquely identified lab probe message."""
import json
import subprocess
import time
import uuid


def aws(*args):
    return json.loads(subprocess.check_output([
        "aws", "sqs", *args, "--region", "ap-south-1", "--output", "json", "--no-cli-pager"
    ], text=True) or "{}")


queue = subprocess.check_output([
    "terraform", "-chdir=infra/environments/dev", "output", "-raw", "payments_queue_url"
], text=True).strip()
probe = json.dumps({"type": "infrastructure-probe", "id": str(uuid.uuid4())})
message_id = aws("send-message", "--queue-url", queue, "--message-body", probe)["MessageId"]
deadline = time.monotonic() + 30
done = False
while not done and time.monotonic() < deadline:
    messages = aws("receive-message", "--queue-url", queue, "--max-number-of-messages", "10",
                   "--wait-time-seconds", "2", "--visibility-timeout", "15").get("Messages", [])
    for message in messages:
        if message["MessageId"] == message_id:
            aws("delete-message", "--queue-url", queue, "--receipt-handle", message["ReceiptHandle"])
            done = True
        else:
            aws("change-message-visibility", "--queue-url", queue,
                "--receipt-handle", message["ReceiptHandle"], "--visibility-timeout", "0")
if not done:
    raise RuntimeError("Probe was not received. Check for another active consumer; the probe may remain queued.")
attributes = aws("get-queue-attributes", "--queue-url", queue, "--attribute-names",
                 "RedrivePolicy", "SqsManagedSseEnabled")["Attributes"]
if json.loads(attributes["RedrivePolicy"])["maxReceiveCount"] != 5:
    raise RuntimeError("Unexpected retry limit")
if attributes["SqsManagedSseEnabled"] != "true":
    raise RuntimeError("SQS managed encryption is not enabled")
print("PASS: encrypted SQS send/receive/delete and configured five-receive DLQ policy.")
print("This checks configuration; the full poison-message/redrive drill comes later.")
