import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def get_json(path):
    with urllib.request.urlopen(
        f"{BASE_URL}{path}",
        timeout=2,
    ) as response:
        return json.load(response)


deadline = time.monotonic() + 60

while True:
    try:
        health = get_json("/healthz")

        if health.get("status") != "ok":
            raise RuntimeError(f"Unexpected health response: {health}")

        break
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        RuntimeError,
    ):
        if time.monotonic() >= deadline:
            raise RuntimeError("Application did not become healthy in time")

        time.sleep(1)


catalog = get_json("/api/products")

if not catalog.get("products"):
    raise RuntimeError("Catalog contains no products")

product = get_json("/api/products/1")

if product.get("id") != 1 or product.get("price_minor") != 19900:
    raise RuntimeError(f"Unexpected product response: {product}")

print("PASS: container health and catalog smoke tests")