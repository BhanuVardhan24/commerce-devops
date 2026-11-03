import hashlib
import hmac
import json
import os
import uuid

import psycopg
from flask import Flask, jsonify, render_template, request
from psycopg.types.json import Jsonb
from redis.exceptions import RedisError

from app.data import PRODUCTS, cache, db


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16384

    @app.get("/")
    def storefront():
        return render_template("index.html", products=PRODUCTS,
                               version=os.getenv("APP_VERSION", "local"))

    @app.get("/healthz")
    def health():
        return jsonify(status="ok", service="catalog",
                       version=os.getenv("APP_VERSION", "local"))

    @app.get("/readyz")
    def ready():
        with db() as conn:
            conn.execute("SELECT 1 FROM orders LIMIT 1")
        cache().ping()
        return jsonify(status="ready")

    @app.get("/api/products")
    def products():
        return jsonify(products=PRODUCTS)

    @app.get("/api/products/<int:product_id>")
    def product(product_id):
        item = next((p for p in PRODUCTS if p["id"] == product_id), None)
        return jsonify(item) if item else (jsonify(error="Product not found"), 404)

    @app.route("/api/carts/<uuid:cart_id>", methods=["GET", "PUT"])
    def cart(cart_id):
        key = f"cart:{cart_id}"
        if request.method == "PUT":
            body = request.get_json(silent=True)
            items = body.get("items") if isinstance(body, dict) else None
            valid = (isinstance(items, list) and 0 < len(items) <= 10
                     and all(isinstance(i, dict)
                             and type(i.get("product_id")) is int
                             and i["product_id"] in (1, 2)
                             and type(i.get("quantity")) is int
                             and 1 <= i["quantity"] <= 10 for i in items))
            if not valid:
                return jsonify(error="Supply 1-10 items with valid product_id and quantity 1-10"), 400
            cache().set(key, json.dumps(items), ex=3600)
        return jsonify(items=json.loads(cache().get(key) or "[]"))

    @app.post("/api/orders")
    def checkout():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="JSON object required"), 400
        try:
            cart_id = str(uuid.UUID(str(body.get("cart_id", ""))))
        except ValueError:
            return jsonify(error="Valid cart_id required"), 400
        key = request.headers.get("Idempotency-Key", "")
        mode = body.get("mode", "success")
        if not 1 <= len(key) <= 100 or mode not in ("success", "decline", "timeout_once"):
            return jsonify(error="Valid Idempotency-Key and payment mode required"), 400
        fingerprint = hashlib.sha256(json.dumps(
            {"cart_id": cart_id, "mode": mode}, sort_keys=True).encode()).hexdigest()
        with db() as conn:
            # Serialize requests with this key, including simultaneous double clicks.
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
            old = conn.execute("SELECT * FROM orders WHERE request_key=%s", (key,)).fetchone()
            if old:
                if old["request_hash"] != fingerprint:
                    return jsonify(error="Key already used for a different request"), 409
                return jsonify(order_id=old["id"], status=old["status"]), 200
            items = json.loads(cache().get(f"cart:{cart_id}") or "[]")
            if not items:
                return jsonify(error="Cart is empty or expired"), 400
            prices = {p["id"]: p["price_minor"] for p in PRODUCTS}
            snapshot = [{**i, "price_minor": prices[i["product_id"]]} for i in items]
            amount = sum(i["quantity"] * i["price_minor"] for i in snapshot)
            order_id = str(uuid.uuid4())
            conn.execute("""INSERT INTO orders
                (id, request_key, request_hash, cart_id, items, amount, mode)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (order_id, key, fingerprint, cart_id, Jsonb(snapshot), amount, mode))
            conn.execute("INSERT INTO payment_jobs(order_id) VALUES (%s)", (order_id,))
        return jsonify(order_id=order_id, status="PENDING_PAYMENT"), 202

    @app.get("/api/orders/<uuid:order_id>")
    def order(order_id):
        with db() as conn:
            row = conn.execute("""SELECT o.id, o.status, o.items, o.amount, o.currency,
                j.state AS job_state, j.attempts FROM orders o
                JOIN payment_jobs j ON j.order_id=o.id WHERE o.id=%s""",
                (str(order_id),)).fetchone()
        return jsonify(row) if row else (jsonify(error="Order not found"), 404)

    @app.post("/api/payment-webhook")
    def webhook():
        signature = hmac.new(os.environ["WEBHOOK_SECRET"].encode(),
                             request.get_data(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, request.headers.get("X-Signature", "")):
            return jsonify(error="Invalid signature"), 401
        event = request.get_json(silent=True)
        if not isinstance(event, dict) or not all(k in event for k in ("order_id", "event_id", "amount", "currency", "status")):
            return jsonify(error="Invalid event"), 400
        if event["status"] not in ("CONFIRMED", "PAYMENT_FAILED"):
            return jsonify(error="Invalid payment status"), 400
        with db() as conn:
            row = conn.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE",
                               (event["order_id"],)).fetchone()
            if not row or row["amount"] != event["amount"] or row["currency"] != event["currency"]:
                return jsonify(error="Payment does not match order"), 409
            if row["status"] not in ("PENDING_PAYMENT", event["status"]):
                return jsonify(error="Conflicting terminal status"), 409
            existing = conn.execute("SELECT order_id FROM webhook_events WHERE event_id=%s",
                                    (event["event_id"],)).fetchone()
            if existing and existing["order_id"] != row["id"]:
                return jsonify(error="Event ID belongs to another order"), 409
            conn.execute("INSERT INTO webhook_events VALUES (%s,%s) ON CONFLICT DO NOTHING",
                         (event["event_id"], row["id"]))
            conn.execute("UPDATE orders SET status=%s WHERE id=%s", (event["status"], row["id"]))
        return jsonify(status="accepted")

    @app.errorhandler(psycopg.Error)
    @app.errorhandler(RedisError)
    def dependency_error(error):
        app.logger.error("dependency_unavailable type=%s", type(error).__name__)
        return jsonify(error="Dependency unavailable"), 503

    return app
