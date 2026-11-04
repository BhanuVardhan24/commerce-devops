"""Generate a callback key and send it to Secrets Manager without printing the value."""
import json
import secrets
import subprocess

secret_arn = subprocess.check_output([
    "terraform", "-chdir=infra/environments/dev", "output", "-raw", "webhook_secret_arn"
], text=True).strip()
metadata = json.loads(subprocess.check_output([
    "aws", "secretsmanager", "describe-secret", "--secret-id", secret_arn,
    "--region", "ap-south-1", "--output", "json", "--no-cli-pager"
], text=True))
if metadata.get("VersionIdsToStages"):
    print("Webhook secret already initialized; existing value preserved.")
else:
    payload = json.dumps({"WEBHOOK_SECRET": secrets.token_urlsafe(48)})
    subprocess.run([
        "aws", "secretsmanager", "put-secret-value", "--secret-id", secret_arn,
        "--secret-string", "file:///dev/stdin", "--region", "ap-south-1",
        "--query", "ARN", "--output", "text", "--no-cli-pager"
    ], input=payload, text=True, check=True)
    print("Webhook secret initialized; its value was not printed or written to a local file.")
