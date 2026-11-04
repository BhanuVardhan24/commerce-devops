"""Check private RDS reachability from an EKS pod without reading any password."""
import json
import subprocess

host = subprocess.check_output([
    "terraform", "-chdir=infra/environments/dev", "output", "-raw", "database_address"
], text=True).strip()
name = "commerce-rds-check"
job = {
    "apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": name, "namespace": "default"},
    "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 90, "template": {"spec": {
        "restartPolicy": "Never", "automountServiceAccountToken": False,
        "containers": [{"name": "check", "image": "postgres:17.11-alpine",
            "command": ["pg_isready", "-h", host, "-p", "5432", "-U", "commerce_admin", "-d", "commerce", "-t", "30"],
            "resources": {"requests": {"cpu": "50m", "memory": "32Mi"},
                          "limits": {"cpu": "100m", "memory": "64Mi"}},
            "securityContext": {"runAsUser": 10001, "runAsNonRoot": True,
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]}}}]
    }}}
}
subprocess.run(["kubectl", "delete", "job", name, "-n", "default", "--ignore-not-found=true"], check=True)
try:
    subprocess.run(["kubectl", "apply", "-f", "-"], input=json.dumps(job), text=True, check=True)
    result = subprocess.run(["kubectl", "wait", "--for=condition=complete", f"job/{name}",
                             "-n", "default", "--timeout=100s"])
    subprocess.run(["kubectl", "logs", f"job/{name}", "-n", "default"])
    result.check_returncode()
    print("PASS: PostgreSQL accepts connections from EKS; credentials were not tested.")
finally:
    subprocess.run(["kubectl", "delete", "job", name, "-n", "default", "--ignore-not-found=true"])
