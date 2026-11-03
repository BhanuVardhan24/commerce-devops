import os

from flask import Flask, jsonify


PRODUCTS = [
    {
        "id": 1,
        "name": "DevOps Notebook",
        "price_minor": 19900,
        "currency": "INR",
    },
    {
        "id": 2,
        "name": "Linux Mug",
        "price_minor": 29900,
        "currency": "INR",
    },
]


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def health():
        return jsonify(
            status="ok",
            service="catalog",
            version=os.getenv("APP_VERSION", "local"),
        )

    @app.get("/api/products")
    def list_products():
        return jsonify(products=PRODUCTS)

    @app.get("/api/products/<int:product_id>")
    def get_product(product_id):
        product = next(
            (item for item in PRODUCTS if item["id"] == product_id),
            None,
        )

        if product is None:
            return jsonify(error="Product not found"), 404

        return jsonify(product)

    return app