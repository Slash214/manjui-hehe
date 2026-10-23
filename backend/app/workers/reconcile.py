import logging
import os
import threading
from datetime import timedelta

from celery.signals import worker_ready, worker_shutdown
from sqlalchemy import select

from app.models import GenerationTask, utcnow
from app.providers.generation.base import GenerationError
from app.providers.storage import storage
from app.repos import SessionLocal
from app.workers.generate import fail, finish, generate, provider

stop = threading.Event()


def maintain() -> None:
    stale = utcnow() - timedelta(seconds=int(os.getenv("GENERATION_HEARTBEAT_TIMEOUT", "90")))
    with SessionLocal() as db:
        queued = list(db.scalars(select(GenerationTask.id).where(GenerationTask.status == "queued").limit(100)))
        lost = list(db.scalars(select(GenerationTask.id).where(GenerationTask.status == "running", GenerationTask.heartbeat_at < stale).limit(100)))
    for id in queued:
        generate.apply_async(args=[id], queue=os.getenv("GENERATION_QUEUE", "generation"))
    for id in lost:
        # Claim the stale lease before network reconciliation so multiple workers do not reconcile together.
        with SessionLocal.begin() as db:
            task = db.scalar(select(GenerationTask).where(GenerationTask.id == id).with_for_update())
            if task is None or task.status != "running" or task.heartbeat_at is None:
                continue
            heartbeat = task.heartbeat_at
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=stale.tzinfo)
            if heartbeat >= stale:
                continue
            task.heartbeat_at = utcnow()
            snapshot, prompt_id = task.snapshot_json, task.comfy_prompt_id
        try:
            store = storage()
            output = provider(snapshot).recover(snapshot, prompt_id, store.get)
            if output:
                finish(id, output, store)
            else:
                fail(id, GenerationError("WORKER_LOST"))
        except Exception:
            logging.getLogger(__name__).exception("generation_recovery_failed", extra={"task_id": id})
            fail(id, GenerationError("WORKER_LOST"))


def loop() -> None:
    while not stop.is_set():
        try:
            maintain()
        except Exception:
            logging.getLogger(__name__).exception("generation_maintenance_failed")
        stop.wait(3)


@worker_ready.connect
def start_maintenance(**kwargs: object) -> None:
    stop.clear()
    threading.Thread(target=loop, name="generation-maintenance", daemon=True).start()


@worker_shutdown.connect
def stop_maintenance(**kwargs: object) -> None:
    stop.set()
