import unittest
from app.main import create_app


class CheckoutValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_invalid_cart_is_rejected(self):
        response = self.client.put("/api/carts/00000000-0000-0000-0000-000000000001",
                                  json={"items": [{"product_id": 1, "quantity": -1}]})
        self.assertEqual(response.status_code, 400)

    def test_checkout_requires_valid_cart_id(self):
        self.assertEqual(self.client.post("/api/orders", json={}).status_code, 400)

    def test_checkout_requires_idempotency_key(self):
        response = self.client.post("/api/orders", json={
            "cart_id": "00000000-0000-0000-0000-000000000001"})
        self.assertEqual(response.status_code, 400)
