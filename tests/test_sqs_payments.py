import json
import unittest
from unittest.mock import Mock, patch

from app.sqs_payments import handle_message


class SqsAcknowledgmentTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.message = {
            "Body": json.dumps({"order_id": "order-123"}),
            "ReceiptHandle": "receipt-123",
        }

    @patch("app.sqs_payments.process_order", return_value=True)
    def test_committed_work_is_acknowledged(self, process):
        handle_message(self.client, "queue-url", self.message)

        process.assert_called_once_with("order-123")
        self.client.delete_message.assert_called_once_with(
            QueueUrl="queue-url",
            ReceiptHandle="receipt-123",
        )
        self.client.change_message_visibility.assert_not_called()

    @patch("app.sqs_payments.process_order", return_value=False)
    def test_incomplete_work_is_not_acknowledged(self, process):
        handle_message(self.client, "queue-url", self.message)

        self.client.delete_message.assert_not_called()
        self.client.change_message_visibility.assert_called_once_with(
            QueueUrl="queue-url",
            ReceiptHandle="receipt-123",
            VisibilityTimeout=2,
        )

    @patch(
        "app.sqs_payments.process_order",
        side_effect=RuntimeError("commit failed"),
    )
    def test_database_failure_does_not_acknowledge(self, process):
        with self.assertRaises(RuntimeError):
            handle_message(self.client, "queue-url", self.message)

        self.client.delete_message.assert_not_called()

    def test_invalid_message_is_not_acknowledged(self):
        self.message["Body"] = "{}"

        with self.assertRaises(ValueError):
            handle_message(self.client, "queue-url", self.message)

        self.client.delete_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()