import os

import psycopg
from psycopg.rows import dict_row
from redis import Redis

PRODUCTS = [
    {"id": 1, "name": "DevOps Notebook", "price_minor": 19900, "currency": "INR"},
    {"id": 2, "name": "Linux Mug", "price_minor": 29900, "currency": "INR"},
]


def db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "postgres"),
        dbname=os.getenv("DB_NAME", "commerce"),
        user=os.getenv("DB_USER", "commerce"),
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
        row_factory=dict_row,
    )


def cache():
    return Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True,
                 socket_connect_timeout=2, socket_timeout=2)


if __name__ == "__main__":
    # Run explicitly as a migration job, not once per web worker.
    statements = [
        """CREATE TABLE IF NOT EXISTS orders (
          id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
          request_hash TEXT NOT NULL, cart_id TEXT NOT NULL,
          items JSONB NOT NULL, amount INTEGER NOT NULL CHECK (amount > 0),
          currency TEXT NOT NULL DEFAULT 'INR', mode TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDING_PAYMENT',
          created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS payment_jobs (
          order_id TEXT PRIMARY KEY REFERENCES orders(id),
          state TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
          available_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
        """CREATE TABLE IF NOT EXISTS mock_payments (
          payment_key TEXT PRIMARY KEY, amount INTEGER NOT NULL,
          outcome TEXT NOT NULL, mode TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS webhook_events (
          event_id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES orders(id))""",
    ]
    with db() as conn:
        for statement in statements:
            conn.execute(statement)
    print("Database schema ready", flush=True)
