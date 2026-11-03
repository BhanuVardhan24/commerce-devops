import json
import logging
import os
import signal
import time
import urllib.request

from app.data import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
running = True


def stop(*_):
    global running
    running = False


def tick():
    with db() as conn:
        job = conn.execute("""SELECT j.order_id, j.attempts, o.amount, o.mode
            FROM payment_jobs j JOIN orders o ON o.id=j.order_id
            WHERE j.state='PENDING' AND j.available_at<=now()
            ORDER BY j.available_at FOR UPDATE OF j SKIP LOCKED LIMIT 1""").fetchone()
        if not job:
            return False
        attempt = job["attempts"] + 1
        try:
            payload = json.dumps({"order_id": job["order_id"], "amount": job["amount"],
                                  "mode": job["mode"]}).encode()
            req = urllib.request.Request(os.getenv("PROVIDER_URL", "http://provider:8000/payments"),
                data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                response.read()
            state = "DONE"
        except (OSError, TimeoutError) as error:
            state = "DEAD" if attempt >= 5 else "PENDING"
            logging.warning("payment_retry order_id=%s attempt=%s error=%s",
                            job["order_id"], attempt, type(error).__name__)
        conn.execute("""UPDATE payment_jobs SET state=%s, attempts=%s,
            available_at=now()+interval '2 seconds' WHERE order_id=%s""",
            (state, attempt, job["order_id"]))
        logging.info("payment_job order_id=%s attempt=%s state=%s", job["order_id"], attempt, state)
    return True


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            if not tick():
                time.sleep(1)
        except Exception:
            logging.exception("worker_iteration_failed")
            time.sleep(2)
