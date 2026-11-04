"""Run private RDS setup from EKS without writing credentials to local files."""

import base64
import json
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.request


REGION = "ap-south-1"
NAMESPACE = "commerce"
POD = "commerce-db-bootstrap"

IMAGE = (
    "036706657723.dkr.ecr.ap-south-1.amazonaws.com/commerce/catalog"
    "@sha256:2c7a1c5ea23857a9e69c4be235fd21242466826fb92e92df645d4506c6df33e3"
)


def command(args, stdin=None):
    result = subprocess.run(
        args,
        input=stdin,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        # Intentionally do not echo captured command output.
        raise RuntimeError(f"{args[0]} operation failed")
    return result.stdout


def output(name):
    return command([
        "terraform",
        "-chdir=infra/environments/dev",
        "output",
        "-raw",
        name,
    ]).strip()


def aws(*args):
    return [
        "aws", *args,
        "--region", REGION,
        "--output", "json",
        "--no-cli-pager",
    ]


def read_secret(arn):
    response = json.loads(command(aws(
        "secretsmanager", "get-secret-value",
        "--secret-id", arn,
    )))
    return json.loads(response["SecretString"])


def main():
    identity = json.loads(command(aws("sts", "get-caller-identity")))
    if ":assumed-role/CommerceDevMachineRole/" not in identity["Arn"]:
        raise RuntimeError("Use the EC2 CommerceDevMachineRole identity")

    host = output("database_address")
    master_arn = output("database_master_secret_arn")
    app_arn = output("application_database_secret_arn")

    metadata = json.loads(command(aws(
        "secretsmanager", "describe-secret",
        "--secret-id", app_arn,
    )))
    existing = bool(metadata.get("VersionIdsToStages"))

    if existing:
        app = read_secret(app_arn)
        if (
            app.get("DB_USER") != "commerce_app"
            or app.get("DB_HOST") != host
            or app.get("DB_NAME") != "commerce"
        ):
            raise RuntimeError("Existing application secret does not match")
        print("Existing application password will be preserved.")
    else:
        app = {
            "DB_HOST": host,
            "DB_PORT": "5432",
            "DB_NAME": "commerce",
            "DB_USER": "commerce_app",
            "DB_PASSWORD": secrets.token_urlsafe(36),
        }

    master = read_secret(master_arn)

    with urllib.request.urlopen(
        "https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem",
        timeout=30,
    ) as response:
        ca = response.read().decode()

    if "BEGIN CERTIFICATE" not in ca:
        raise RuntimeError("Invalid RDS certificate bundle")

    # The certificate is public information, safe to keep in Git.
    ca_file = Path("gitops/platform/external-secrets/rds-ca.pem")
    ca_file.write_text(ca)

    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": POD,
            "namespace": NAMESPACE,
        },
        "spec": {
            "restartPolicy": "Never",
            "automountServiceAccountToken": False,
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 10001,
                "runAsGroup": 10001,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "containers": [{
                "name": "bootstrap",
                "image": IMAGE,
                "command": [
                    "python", "-c",
                    "import time; time.sleep(1800)",
                ],
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "capabilities": {"drop": ["ALL"]},
                },
                "resources": {
                    "requests": {"cpu": "50m", "memory": "64Mi"},
                    "limits": {"memory": "256Mi"},
                },
            }],
        },
    }

    command([
        "kubectl", "-n", NAMESPACE, "delete", "pod", POD,
        "--ignore-not-found", "--wait=true", "--timeout=60s",
    ])

    try:
        command(["kubectl", "create", "-f", "-"], json.dumps(pod))

        command([
            "kubectl", "-n", NAMESPACE, "wait",
            "--for=condition=Ready", f"pod/{POD}", "--timeout=180s",
        ])

        payload = {
            "master": master,
            "application": app,
            "existing_application_secret": existing,
            "ca": ca,
        }

        code = Path("scripts/database_bootstrap_pod.py").read_text()

        result = command([
            "kubectl", "-n", NAMESPACE, "exec", "-i", POD,
            "--", "python", "-c", code,
        ], json.dumps(payload))

        print(result.strip())

        if not existing:
            command(aws(
                "secretsmanager", "put-secret-value",
                "--secret-id", app_arn,
                "--secret-string", "file:///dev/stdin",
            ), json.dumps(app))

        print("PASS: application credentials stored in Secrets Manager")

    finally:
        command([
            "kubectl", "-n", NAMESPACE, "delete", "pod", POD,
            "--ignore-not-found", "--wait=false",
        ])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        sys.exit(1)