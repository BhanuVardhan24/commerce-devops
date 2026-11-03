import hashlib
import hmac
import json
import os
import urllib.request

from flask import Flask, jsonify, request

from app.data import db


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.post("/payments")
    def pay():
        body = request.get_json()
        key, amount, mode = body["order_id"], body["amount"], body["mode"]
        outcome = "PAYMENT_FAILED" if mode == "decline" else "CONFIRMED"
        with db() as conn:
            row = conn.execute("""INSERT INTO mock_payments(payment_key,amount,outcome,mode)
                VALUES (%s,%s,%s,%s) ON CONFLICT(payment_key)
                DO UPDATE SET attempts=mock_payments.attempts+1 RETURNING *""",
                (key, amount, outcome, mode)).fetchone()
            if row["amount"] != amount or row["mode"] != mode:
                return jsonify(error="Payment key conflict"), 409
        # The provider commits its result before sending the callback.
        event = {"event_id": f"payment:{key}", "order_id": key,
                 "amount": amount, "currency": "INR", "status": row["outcome"]}
        payload = json.dumps(event).encode()
        signature = hmac.new(os.environ["WEBHOOK_SECRET"].encode(), payload, hashlib.sha256).hexdigest()
        req = urllib.request.Request(
            os.getenv("CALLBACK_URL", "http://web:8000/api/payment-webhook"), data=payload,
            headers={"Content-Type": "application/json", "X-Signature": signature})
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
        if mode == "timeout_once" and row["attempts"] == 1:
            # Simulate a lost provider response AFTER the payment took effect.
            return jsonify(error="Simulated lost response; retry the same key"), 503
        return jsonify(status=row["outcome"])

    return app
