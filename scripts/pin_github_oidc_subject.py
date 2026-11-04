"""Pass the downloaded oidc-subject.txt artifact to pin the exact subject in Terraform."""
import json
from pathlib import Path
import re
import subprocess
import sys

subject = Path(sys.argv[1]).read_text().strip()
pattern = r"repo:BhanuVardhan24(?:@\d+)?/commerce-devops(?:@\d+)?:ref:refs/heads/main"
if not re.fullmatch(pattern, subject):
    raise SystemExit("Unexpected subject; refusing to broaden AWS trust")
p = Path("infra/environments/dev/github-oidc-subjects.tf")
p.write_text("# Exact subject verified from a successful main-branch OIDC run.\n"
             "locals {\n  github_main_subjects = [" + json.dumps(subject) + "]\n}\n")
subprocess.run(["terraform", "fmt", str(p)], check=True)
print("Pinned the exact main-branch OIDC subject. Review and apply the Terraform change.")
