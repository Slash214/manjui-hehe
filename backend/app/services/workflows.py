import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.workflow_mapping import validate_mapping
from app.models import Workflow


def register_workflows(db: Session) -> None:
    entries: list[dict[str, Any]] = [
        {"name": f"MOCK 测试{'关键画面' if kind == 'keyframe' else '视频'}", "kind": kind,
         "provider": "mock", "version": 1, "comfy_json": {}, "param_map_json": {}, "enabled": True}
        for kind in ("keyframe", "video")]
    for path in sorted(Path(os.getenv("WORKFLOW_DIR", "/workflows")).glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf8"))
        if entry.get("provider") != "comfy" or entry.get("kind") not in ("keyframe", "video"):
            raise ValueError(f"Invalid workflow: {path.name}")
        validate_mapping(entry["comfy_json"], entry["param_map_json"])
        if "prompt" not in entry["param_map_json"]:
            raise ValueError("Workflow requires prompt mapping")
        entries.append(entry)
    for entry in entries:
        old = db.scalar(select(Workflow).where(Workflow.name == entry["name"], Workflow.version == entry["version"]))
        if old:
            if any(getattr(old, k) != entry[k] for k in ("kind", "provider", "comfy_json", "param_map_json")):
                raise ValueError("Workflow changed without version increment")
            continue
        db.add(Workflow(**entry))
    db.flush()


if __name__ == "__main__":
    from app.repos import SessionLocal
    with SessionLocal.begin() as session:
        register_workflows(session)
