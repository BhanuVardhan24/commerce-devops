"""HTTP end-to-end test. Standard library only; run against a started Compose stack."""
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
import uuid

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def call(path, method="GET", body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


for mode, expected in [("success", "CONFIRMED"), ("decline", "PAYMENT_FAILED"),
                       ("timeout_once", "CONFIRMED")]:
    cart, key = str(uuid.uuid4()), str(uuid.uuid4())
    call(f"/api/carts/{cart}", "PUT", {"items": [{"product_id": 1, "quantity": 2}]})
    body = {"cart_id": cart, "mode": mode}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(call, "/api/orders", "POST", body, key) for _ in range(2)]
        orders = [future.result() for future in futures]
    if orders[0]["order_id"] != orders[1]["order_id"]:
        raise RuntimeError("Duplicate checkout created two orders")
    order_id = orders[0]["order_id"]
    deadline = time.monotonic() + 60
    while True:
        state = call(f"/api/orders/{order_id}")
        if state["job_state"] in ("DONE", "DEAD"):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Order did not complete: {state}")
        time.sleep(1)
    if state["status"] != expected or state["job_state"] != "DONE" or state["amount"] != 39800:
        raise RuntimeError(f"Unexpected order outcome: {state}")
    if mode == "timeout_once" and state["attempts"] < 2:
        raise RuntimeError("Lost-response scenario did not retry")
    changed = {"cart_id": cart, "mode": "decline" if mode == "success" else "success"}
    try:
        call("/api/orders", "POST", changed, key)
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise
    else:
        raise RuntimeError("Reusing a key for different input should fail")
    print(f"PASS: {mode}; duplicate checkout safe; amount=39800; attempts={state['attempts']}")

try:
    call("/api/payment-webhook", "POST", {"order_id": "forged"})
except urllib.error.HTTPError as error:
    if error.code != 401:
        raise
else:
    raise RuntimeError("Unsigned webhook was accepted")

print("PASS: unsigned webhook rejected")
