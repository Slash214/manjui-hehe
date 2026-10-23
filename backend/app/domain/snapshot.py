import hashlib
import json
from copy import deepcopy
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_snapshot(*, content_version: int, prompt: str, references: list[dict[str, Any]],
                   asset_version_ids: list[str], workflow: dict[str, Any], params: dict[str, Any],
                   first_frame: dict[str, Any] | None = None) -> dict[str, Any]:
    return deepcopy({"content_version": content_version, "prompt": prompt,
                     "references": references, "asset_version_ids": asset_version_ids,
                     "workflow_id": workflow["id"], "workflow_version": workflow["version"],
                     "workflow": workflow, "model": params.get("model", workflow["name"]),
                     "params": params, "seed": params.get("seed"), "first_frame": first_frame})
