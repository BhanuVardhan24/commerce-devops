import json
import logging
import os
import signal
import sys
import time
import urllib.request

import boto3
from botocore.config import Config

from app.data import db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

running = True


def stop(*_):
    global running
    running = False


def dispatch_one(client, queue_url):
    """Publish an outbox entry, then mark it queued."""
    with db() as conn:
        job = conn.execute(
            """
            SELECT order_id
            FROM payment_jobs
            WHERE state = 'PENDING' AND available_at <= now()
            ORDER BY available_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        ).fetchone()

        if not job:
            return False

        client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"order_id": job["order_id"]}),
        )

        conn.execute(
            "UPDATE payment_jobs SET state = 'QUEUED' WHERE order_id = %s",
            (job["order_id"],),
        )

    logging.info("payment_published order_id=%s", job["order_id"])
    return True


def process_order(order_id):
    """Return True only when it is safe to acknowledge the SQS message."""
    with db() as conn:
        job = conn.execute(
            """
            SELECT j.order_id, j.state, j.attempts, o.amount, o.mode
            FROM payment_jobs j
            JOIN orders o ON o.id = j.order_id
            WHERE j.order_id = %s
            FOR UPDATE OF j SKIP LOCKED
            """,
            (order_id,),
        ).fetchone()

        # Missing row or another worker currently owns the lock.
        if not job:
            return False

        # Duplicate delivery after a completed database transaction.
        if job["state"] == "DONE":
            return True

        if job["state"] not in ("PENDING", "QUEUED"):
            return False

        attempt = job["attempts"] + 1
        success = False

        try:
            payload = json.dumps({
                "order_id": order_id,
                "amount": job["amount"],
                "mode": job["mode"],
            }).encode()

            request = urllib.request.Request(
                os.environ.get(
                    "PROVIDER_URL",
                    "http://commerce-provider:8000/payments",
                ),
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()

            success = True

        except (OSError, TimeoutError) as error:
            logging.warning(
                "payment_retry order_id=%s attempt=%s error=%s",
                order_id,
                attempt,
                type(error).__name__,
            )

        conn.execute(
            """
            UPDATE payment_jobs
            SET state = %s, attempts = %s
            WHERE order_id = %s
            """,
            ("DONE" if success else "QUEUED", attempt, order_id),
        )

    # The connection context has committed before returning success.
    logging.info(
        "payment_processed order_id=%s attempt=%s success=%s",
        order_id,
        attempt,
        success,
    )
    return success


def handle_message(client, queue_url, message):
    body = json.loads(message["Body"])
    order_id = body.get("order_id")

    if not isinstance(order_id, str) or not 1 <= len(order_id) <= 128:
        raise ValueError("Invalid payment message")

    if process_order(order_id):
        client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message["ReceiptHandle"],
        )
    else:
        client.change_message_visibility(
            QueueUrl=queue_url,
            ReceiptHandle=message["ReceiptHandle"],
            VisibilityTimeout=2,
        )


def main():
    mode = sys.argv[1]
    if mode not in ("dispatch", "consume"):
        raise ValueError("Expected dispatch or consume")

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    queue_url = os.environ["PAYMENTS_QUEUE_URL"]

    client = boto3.client(
        "sqs",
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        config=Config(
            connect_timeout=5,
            read_timeout=25,
            retries={"mode": "standard", "total_max_attempts": 3},
        ),
    )

    logging.info("sqs_process_started mode=%s", mode)

    while running:
        try:
            if mode == "dispatch":
                if not dispatch_one(client, queue_url):
                    time.sleep(1)
                continue

            response = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10,
                VisibilityTimeout=60,
            )

            for message in response.get("Messages", []):
                try:
                    handle_message(client, queue_url, message)
                except Exception as error:
                    # Keep the message for retry; repeated failures reach the DLQ.
                    logging.error(
                        "payment_message_failed error=%s",
                        type(error).__name__,
                    )

        except Exception as error:
            logging.error(
                "sqs_iteration_failed mode=%s error=%s",
                mode,
                type(error).__name__,
            )
            time.sleep(2)


if __name__ == "__main__":
    main()