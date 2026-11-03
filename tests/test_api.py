import unittest

from app.main import create_app


class CatalogApiTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_product_catalog(self):
        response = self.client.get("/api/products")

        self.assertEqual(response.status_code, 200)

        products = response.get_json()["products"]
        self.assertGreater(len(products), 0)

        for product in products:
            self.assertIsInstance(product["price_minor"], int)
            self.assertGreater(product["price_minor"], 0)
            self.assertEqual(product["currency"], "INR")

    def test_existing_product(self):
        response = self.client.get("/api/products/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["id"], 1)
        self.assertEqual(response.get_json()["price_minor"], 19900)

    def test_missing_product(self):
        response = self.client.get("/api/products/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.get_json(),
            {"error": "Product not found"},
        )

    def test_catalog_rejects_post(self):
        response = self.client.post("/api/products", json={})

        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()