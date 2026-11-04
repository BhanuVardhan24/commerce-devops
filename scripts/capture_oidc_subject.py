"""Record the non-secret subject claim, never the OIDC token itself."""
import base64
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

if os.environ["GITHUB_REPOSITORY"] != "BhanuVardhan24/commerce-devops" or os.environ["GITHUB_REF"] != "refs/heads/main":
    raise RuntimeError("AWS publishing is restricted to the project's main branch")
url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=" + urllib.parse.quote("sts.amazonaws.com")
req = urllib.request.Request(url, headers={
    "Authorization": "bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]})
with urllib.request.urlopen(req, timeout=20) as response:
    token = json.load(response)["value"]
payload = token.split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
if claims["aud"] != "sts.amazonaws.com" or claims["repository"] != "BhanuVardhan24/commerce-devops" or claims["ref"] != "refs/heads/main":
    raise RuntimeError("Unexpected token context")
Path("reports").mkdir(exist_ok=True)
Path("reports/oidc-subject.txt").write_text(claims["sub"] + "\n")
print("Recorded OIDC subject:", claims["sub"])
print("AWS STS validates the token; this script only records metadata.")
