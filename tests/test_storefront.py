import unittest
from unittest.mock import patch

from app.main import create_app


class StorefrontTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_storefront_displays_products_and_prices(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")

        html = response.get_data(as_text=True)

        self.assertIn("DevOps Notebook", html)
        self.assertIn("Linux Mug", html)
        self.assertIn("199.00", html)
        self.assertIn("299.00", html)

    def test_storefront_displays_release_version(self):
        with patch.dict("os.environ", {"APP_VERSION": "test-release"}):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "test-release",
            response.get_data(as_text=True),
        )