"""Download the npm CLI to this project only; verify the registry's SHA-512 before extraction."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

root = Path(__file__).resolve().parents[1]
metadata = json.load(urllib.request.urlopen("https://registry.npmjs.org/npm/10.9.2", timeout=30))
content = urllib.request.urlopen(metadata["dist"]["tarball"], timeout=30).read()
expected = metadata["dist"]["integrity"]
actual = "sha512-" + base64.b64encode(hashlib.sha512(content).digest()).decode()
if actual != expected:
    raise RuntimeError("npm integrity mismatch")
target = root / ".tools" / "npm"
target.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
    archive.extractall(target, filter="data")
print(target / "package" / "bin" / "npm-cli.js")
