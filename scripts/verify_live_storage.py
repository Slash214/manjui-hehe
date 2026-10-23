"""Verify actual API image upload against the running PostgreSQL/MinIO stack."""
import hashlib
import json
import os
import secrets
from io import BytesIO
from urllib.parse import parse_qs, urlsplit, urlunsplit

import httpx
from PIL import Image

client = httpx.Client(base_url=os.getenv("API_URL", "http://127.0.0.1:18000") + "/api/v1", timeout=30)
response = client.post("/auth/register", json={"email": f"storage-{secrets.token_hex(8)}@example.com",
                                             "password": secrets.token_urlsafe(24)})
response.raise_for_status()
client.headers["Authorization"] = "Bearer " + response.json()["access_token"]


def post(path: str, data: dict):
    response = client.post(path, json=data)
    response.raise_for_status()
    return response.json()


project = post("/projects", {"name": "阶段1存储验收"})
asset = post(f"/projects/{project['id']}/assets", {"name": "测试参考图", "asset_type": "location"})
version = post(f"/assets/{asset['id']}/versions", {"base_version": 1, "description": "存储测试，非生成画面"})
buffer = BytesIO()
Image.new("RGB", (16, 16), (30, 30, 30)).save(buffer, format="PNG")
response = client.post(f"/asset-versions/{version['id']}/reference-image", data={"base_version": "2"},
                       files={"file": ("storage-test.png", buffer.getvalue(), "image/png")})
response.raise_for_status()
new_version = response.json()
assert new_version["version_no"] == 2 and new_version["id"] != version["id"]
response = client.get(f"/files/{new_version['reference_file_id']}/url")
response.raise_for_status()
link = response.json()
parts = urlsplit(link["url"])
assert link["expires_in"] == 3600 and parse_qs(parts.query)["X-Amz-Expires"] == ["3600"]
download = httpx.get(link["url"], timeout=10)
download.raise_for_status()
assert hashlib.sha256(download.content).digest() == hashlib.sha256(buffer.getvalue()).digest()
assert httpx.get(urlunsplit(parts._replace(query="")), timeout=10).status_code == 403
old = client.get(f"/asset-versions/{version['id']}").json()
assert old["reference_file_id"] is None
assert client.get(f"/assets/{asset['id']}").json()["current_version_id"] == version["id"]
print(json.dumps({"upload": response.status_code, "asset_version_append": True,
                  "old_version_unchanged": True, "download_hash_matches": True,
                  "signature_expires_seconds": 3600, "anonymous_read_status": 403}))
