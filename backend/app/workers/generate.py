import hashlib
import logging
from typing import Any

from sqlalchemy import select

from app.domain.task_state import transition
from app.models import Candidate, File, GenerationTask, utcnow
from app.providers.generation.base import Canceled, GenerationError, GenerationProvider, Output
from app.providers.generation.comfy import ComfyGenerationProvider
from app.providers.generation.mock import MockGenerationProvider
from app.providers.storage import StorageProvider, storage
from app.repos import SessionLocal
from app.workers.celery_app import app


def provider(snapshot: dict[str, Any]) -> GenerationProvider:
    if snapshot["workflow"]["provider"] == "mock":
        return MockGenerationProvider()
    return ComfyGenerationProvider()


def pulse(task_id: str, prompt_id: str | None, progress: float | None) -> None:
    with SessionLocal.begin() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id).with_for_update())
        if task is None or task.status != "running":
            raise Canceled()
        task.heartbeat_at = utcnow()
        if prompt_id:
            task.comfy_prompt_id = prompt_id
        task.progress = progress


def fail(task_id: str, error: GenerationError) -> None:
    with SessionLocal.begin() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id).with_for_update())
        if task and task.status == "running":
            task.status = transition(task.status, "failed")
            task.error_code, task.error_message = error.code, str(error)
            task.finished_at, task.progress = utcnow(), None


def finish(task_id: str, output: Output, store: StorageProvider) -> None:
    # Deterministic storage key makes interrupted finalization safely repeatable.
    key = f"generation/{task_id}/output.{'mp4' if output.mime == 'video/mp4' else 'png'}"
    try:
        store.put(key, output.data, output.mime)
    except Exception as exc:
        raise GenerationError("STORAGE_ERROR") from exc
    with SessionLocal.begin() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id).with_for_update())
        if task is None or task.status != "running":
            return
        file = File(project_id=task.project_id, storage_key=key, mime=output.mime, size_bytes=len(output.data),
                    sha256=hashlib.sha256(output.data).hexdigest(), width=output.width, height=output.height,
                    duration_ms=output.duration_ms)
        db.add(file)
        db.flush()
        db.add(Candidate(task_id=task.id, shot_id=task.shot_id, asset_version_id=task.asset_version_id,
                         kind=task.kind, file_id=file.id, duration_ms=output.duration_ms,
                         meta_json={"provider": task.snapshot_json["workflow"]["provider"]}))
        task.status = transition(task.status, "succeeded")
        task.finished_at, task.progress = utcnow(), None


@app.task(name="manju.generate", autoretry_for=(), max_retries=0)
def generate(task_id: str) -> None:
    with SessionLocal.begin() as db:
        task = db.scalar(select(GenerationTask).where(GenerationTask.id == task_id).with_for_update())
        if task is None or task.status != "queued":
            return
        task.status = transition(task.status, "running")
        task.started_at = task.heartbeat_at = utcnow()
        snapshot = task.snapshot_json
    try:
        store = storage()
        output = provider(snapshot).generate(snapshot, lambda prompt, progress: pulse(task_id, prompt, progress), store.get)
        finish(task_id, output, store)
    except Canceled:
        return
    except GenerationError as error:
        fail(task_id, error)
    except Exception:
        logging.getLogger(__name__).exception("generation_failed", extra={"task_id": task_id})
        fail(task_id, GenerationError("COMFY_EXECUTION"))
