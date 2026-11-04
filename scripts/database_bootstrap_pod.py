"""Executed inside a temporary EKS pod; credentials arrive through stdin."""

import json
import os
from pathlib import Path
import runpy
import sys

import psycopg
from psycopg import sql


def main():
    payload = json.load(sys.stdin)
    app = payload["application"]
    master = payload["master"]

    ca_path = Path("/tmp/commerce-rds-ca.pem")
    ca_path.write_text(payload["ca"])

    connection = {
        "host": app["DB_HOST"],
        "port": int(app["DB_PORT"]),
        "dbname": app["DB_NAME"],
        "sslmode": "verify-full",
        "sslrootcert": str(ca_path),
        "connect_timeout": 15,
    }

    with psycopg.connect(
        **connection,
        user=master["username"],
        password=master["password"],
    ) as conn:
        role = conn.execute(
            """
            SELECT oid, rolsuper, rolcreatedb, rolcreaterole,
                   rolreplication, rolbypassrls
            FROM pg_roles
            WHERE rolname = %s
            """,
            (app["DB_USER"],),
        ).fetchone()

        if role is None:
            conn.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOREPLICATION NOBYPASSRLS"
                ).format(
                    sql.Identifier(app["DB_USER"]),
                    sql.Literal(app["DB_PASSWORD"]),
                )
            )
        else:
            if not payload["existing_application_secret"]:
                raise RuntimeError(
                    "Role exists but its application secret is missing; "
                    "refusing automatic password replacement"
                )

            if any(role[1:]):
                raise RuntimeError("Existing application role is privileged")

            membership = conn.execute(
                "SELECT 1 FROM pg_auth_members WHERE member = %s LIMIT 1",
                (role[0],),
            ).fetchone()

            if membership:
                raise RuntimeError("Application role has unexpected memberships")

        conn.execute("CREATE SCHEMA IF NOT EXISTS commerce")

        conn.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(app["DB_NAME"]),
                sql.Identifier(app["DB_USER"]),
            )
        )

        conn.execute(
            sql.SQL("GRANT USAGE, CREATE ON SCHEMA commerce TO {}").format(
                sql.Identifier(app["DB_USER"])
            )
        )

        conn.execute(
            sql.SQL(
                "ALTER ROLE {} IN DATABASE {} SET search_path TO commerce"
            ).format(
                sql.Identifier(app["DB_USER"]),
                sql.Identifier(app["DB_NAME"]),
            )
        )

    # Check the restricted login independently of the administrator.
    with psycopg.connect(
        **connection,
        user=app["DB_USER"],
        password=app["DB_PASSWORD"],
    ) as conn:
        user, schema = conn.execute(
            "SELECT current_user, current_schema()"
        ).fetchone()

        if user != "commerce_app" or schema != "commerce":
            raise RuntimeError("Unexpected application login or schema")

        tls = conn.execute(
            "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
        ).fetchone()

        if not tls or not tls[0]:
            raise RuntimeError("Database connection is not encrypted")

    os.environ.update(app)
    os.environ["PGSSLMODE"] = "verify-full"
    os.environ["PGSSLROOTCERT"] = str(ca_path)

    # Execute the application's existing additive schema migration.
    runpy.run_module("app.data", run_name="__main__")

    with psycopg.connect(
        **connection,
        user=app["DB_USER"],
        password=app["DB_PASSWORD"],
    ) as conn:
        for table in (
            "orders",
            "payment_jobs",
            "mock_payments",
            "webhook_events",
        ):
            exists = conn.execute(
                "SELECT to_regclass(%s)",
                (f"commerce.{table}",),
            ).fetchone()[0]

            if exists is None:
                raise RuntimeError("An application table is missing")

    print("PASS: restricted application login")
    print("PASS: verified TLS connection")
    print("PASS: commerce schema and four application tables")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid printing SQL statements or credentials on failure.
        print(
            f"Database bootstrap failed ({type(exc).__name__}); "
            "credentials suppressed.",
            file=sys.stderr,
        )
        sys.exit(1)