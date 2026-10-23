"""Real PostgreSQL/Redis/Celery/FFmpeg/MinIO verification in a newly isolated database and queue.

Run via docker compose run --rm --no-deps api python -m tests.verify_generation.
Only the worker process created by this script is killed. Application data and workers are untouched.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


def main() -> None:
    if os.getenv("MANJU_GENERATION_VERIFY_CHILD") != "true":
        url = make_url(os.environ["DATABASE_URL"])
        name = "manju_phase2_verify_" + uuid4().hex[:12]
        admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        env = {**os.environ, "DATABASE_URL": url.set(database=name).render_as_string(hide_password=False),
               "GENERATION_QUEUE": name, "GENERATION_HEARTBEAT_TIMEOUT": "4",
               "MANJU_GENERATION_VERIFY_CHILD": "true", "COMFYUI_ENABLED": "false"}
        for command in ("upgrade head", "downgrade base", "upgrade head", "check"):
            subprocess.run([sys.executable, "-m", "alembic", *command.split()], env=env, check=True)
        subprocess.run([sys.executable, "-m", "tests.verify_generation"], env=env, check=True)
        print(json.dumps({"isolated_database": name, "migrations": "upgrade/downgrade/upgrade/check passed", "application_database_untouched": True}))
        return
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import Candidate, GenerationTask
    from app.providers.storage import storage
    from app.repos import SessionLocal

    client = TestClient(app)
    token = client.post("/api/v1/auth/register", json={"email": "isolated-generation@example.com", "password": uuid4().hex}).json()["access_token"]
    client.headers["Authorization"] = "Bearer " + token

    def post(path, data=None, expected=200):
        response = client.post("/api/v1" + path, json=data or {})
        assert response.status_code == expected, response.text
        return response.json()

    project = post("/projects", {"name": "阶段2隔离验证"})
    episode = post(f"/projects/{project['id']}/episodes", {"title": "真实队列 mock 测试"})
    shot = post(f"/episodes/{episode['id']}/shots", {"action_desc": "测试动作"})
    workflows = client.get("/api/v1/workflows").json()
    workflow_ids = {w["kind"]: w["id"] for w in workflows if w["provider"] == "mock"}

    def submit(kind="keyframe", params=None, key=None, target=None):
        return post(f"/shots/{target or shot['id']}/generate", {"kind": kind,"workflow_id":workflow_ids[kind],
                    "idempotency_key":key or uuid4().hex,"overrides":params or {}}, 202)

    def wait(id, wanted="succeeded", seconds=45):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            task = client.get(f"/api/v1/tasks/{id}").json()
            if task["status"] == wanted:
                return task
            if task["status"] in ("succeeded", "failed", "canceled"):
                raise AssertionError(task)
            time.sleep(0.25)
        raise AssertionError(f"Task did not reach {wanted}")

    def start_worker():
        return subprocess.Popen([sys.executable, "-m", "celery", "-A", "app.workers.celery_app", "worker", "-P", "solo",
                                 "-Q", os.environ["GENERATION_QUEUE"], "--hostname", os.environ["GENERATION_QUEUE"] + "@%h",
                                 "--loglevel", "WARNING", "--without-gossip", "--without-mingle", "--without-heartbeat"],
                                stdout=log, stderr=subprocess.STDOUT)

    log = open("/tmp/phase2-isolated-worker.log", "a", encoding="utf8")  # noqa: SIM115 - closed after worker termination
    worker = start_worker()
    try:
        key = uuid4().hex
        with ThreadPoolExecutor(max_workers=2) as pool:
            repeated = list(pool.map(lambda _: submit(params={"mock_delay_sec": 2}, key=key), range(2)))
        assert repeated[0]["id"] == repeated[1]["id"]
        task = repeated[0]
        wait(task["id"], "running")
        response = client.patch(f"/api/v1/shots/{shot['id']}", json={"base_version":1,"action_desc":"提交后修改"})
        assert response.is_success
        shot = response.json()
        completed = wait(task["id"])
        assert completed["snapshot_json"] == task["snapshot_json"] and completed["progress"] is None
        candidate = client.get(f"/api/v1/shots/{shot['id']}/candidates").json()[0]
        assert shot["adopted_keyframe_candidate_id"] is None
        shot = post(f"/shots/{shot['id']}/adopt", {"candidate_id":candidate["id"],"base_version":shot["content_version"]})
        video = submit("video")
        wait(video["id"])
        candidates = client.get(f"/api/v1/shots/{shot['id']}/candidates").json()
        shot = post(f"/shots/{shot['id']}/adopt", {"candidate_id":candidates[0]["id"],"base_version":shot["content_version"]})
        with SessionLocal() as db:
            from app.models import File
            file = db.get(File, candidates[0]["file_id"])
            path = Path("/tmp/phase2-test-output.mp4")
            path.write_bytes(storage().get(file.storage_key))
        probe = subprocess.run(["ffprobe","-v","error","-show_streams","-of","json",str(path)],capture_output=True,check=True)
        assert json.loads(probe.stdout)["streams"][0]["codec_name"] == "h264"
        failure = submit(params={"mock_error":"COMFY_VALIDATION"})
        failed = wait(failure["id"],"failed")
        assert failed["error_code"] == "COMFY_VALIDATION" and "额外算力" in failed["error_message"]
        retried = post(f"/tasks/{failure['id']}/retry", {"idempotency_key":uuid4().hex}, 202)
        assert retried["snapshot_json"] == failed["snapshot_json"] and retried["retry_of_task_id"] == failed["id"]
        wait(retried["id"],"failed")
        after = client.get(f"/api/v1/episodes/{episode['id']}/shots").json()["items"][0]
        assert after["adopted_video_candidate_id"] == shot["adopted_video_candidate_id"]
        canceled = submit(params={"mock_delay_sec":10})
        wait(canceled["id"],"running")
        post(f"/tasks/{canceled['id']}/cancel")
        time.sleep(1)
        assert wait(canceled["id"],"canceled")["progress"] is None
        lost = submit(params={"mock_delay_sec":30})
        wait(lost["id"],"running")
        worker.kill(); worker.wait(timeout=10)
        worker = start_worker()
        recovered = wait(lost["id"],"failed",seconds=20)
        assert recovered["error_code"] == "WORKER_LOST"
        with SessionLocal() as db:
            task = db.get(GenerationTask, task["id"])
            assert task.snapshot_json == completed["snapshot_json"]
            assert db.query(Candidate).count() == 2
        with SessionLocal() as db:
            try:
                db.execute(text("UPDATE generation_tasks SET snapshot_json='{}' WHERE id=:id"),{"id":task.id})
                db.commit()
                raise AssertionError("DB snapshot guard missing")
            except DBAPIError as error:
                db.rollback()
                assert "immutable" in str(error)
        print(json.dumps({"real_redis_celery_mock_chain":"passed", "ffmpeg_h264":"passed", "minio_read":"passed",
                          "parallel_idempotency":"passed", "immutable_snapshot":"passed", "no_auto_adoption":"passed",
                          "manual_retry_new_task":"passed", "running_cancel":"passed", "isolated_worker_kill_recovery":"WORKER_LOST",
                          "real_comfyui":"not tested; no GPU/external call"}))
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill();worker.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
