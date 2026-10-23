# ruff: noqa: F811
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domain.snapshot import build_snapshot
from app.domain.task_state import transition
from app.domain.workflow_mapping import fill_workflow
from app.main import app
from app.models import Candidate, GenerationTask
from app.providers.generation.base import GenerationError, Output
from app.providers.storage import storage
from app.repos import database
from app.workers import generate as worker
from tests.test_api import client, patch, post  # noqa: F401


@pytest.fixture
def setup(client, monkeypatch):
    generator = app.dependency_overrides[database]()
    db = next(generator)
    factory = sessionmaker(db.bind, expire_on_commit=False)
    generator.close()
    monkeypatch.setattr(worker, "SessionLocal", factory)
    store = app.dependency_overrides[storage]()
    monkeypatch.setattr(worker, "storage", lambda: store)

    class Controlled:
        def generate(self, snapshot, pulse, read):
            pulse(None, None)
            if snapshot["params"].get("mock_error"):
                raise GenerationError(snapshot["params"]["mock_error"])
            return Output(b"controlled-test-output", "image/png", 64, 64, None)

    monkeypatch.setattr(worker, "provider", lambda _: Controlled())
    project = post(client, "/projects", name="生成验收")
    episode = post(client, f"/projects/{project['id']}/episodes", title="测试集")
    shot = post(client, f"/episodes/{episode['id']}/shots", action_desc="测试动作")
    workflows = client.get("/api/v1/workflows").json()
    return project, episode, shot, workflows, factory


def submit(client, shot, workflows, kind="keyframe", key=None, **params):
    body = {"kind": kind, "workflow_id": next(w["id"] for w in workflows if w["kind"] == kind),
            "idempotency_key": key or str(uuid4()), "overrides": params}
    return client.post(f"/api/v1/shots/{shot['id']}/generate", json=body)


def test_full_chain_no_auto_adoption_and_snapshot(client, setup):
    _, episode, shot, workflows, factory = setup
    assert submit(client, shot, workflows, "video").status_code == 422
    task = submit(client, shot, workflows, key="double").json()
    assert submit(client, shot, workflows, key="double").json()["id"] == task["id"]
    assert submit(client, shot, workflows, key="double", seed=42).status_code == 409
    original = deepcopy(task["snapshot_json"])
    shot = patch(client, f"/shots/{shot['id']}", base_version=shot["content_version"], action_desc="后改动作")
    worker.generate.run(task["id"])
    worker.generate.run(task["id"])
    result = client.get(f"/api/v1/tasks/{task['id']}").json()
    assert result["status"] == "succeeded" and result["progress"] is None
    assert result["snapshot_json"] == original
    shots = client.get(f"/api/v1/episodes/{episode['id']}/shots").json()["items"]
    assert shots[0]["adopted_keyframe_candidate_id"] is None
    candidate = client.get(f"/api/v1/shots/{shot['id']}/candidates").json()[0]
    shot = post(client, f"/shots/{shot['id']}/adopt", candidate_id=candidate["id"], base_version=shot["content_version"])
    assert shot["adopted_keyframe_candidate_id"] == candidate["id"]
    stale = client.post(f"/api/v1/shots/{shot['id']}/adopt", json={"candidate_id": candidate["id"], "base_version": 1})
    assert stale.status_code == 409
    video = submit(client, shot, workflows, "video").json()
    assert video["snapshot_json"]["first_frame"]["file_id"] == candidate["file_id"]
    worker.generate.run(video["id"])
    candidates = client.get(f"/api/v1/shots/{shot['id']}/candidates").json()
    adopted = post(client, f"/shots/{shot['id']}/adopt", candidate_id=candidates[0]["id"], base_version=shot["content_version"])
    assert adopted["adopted_video_candidate_id"] == candidates[0]["id"]
    with factory() as db:
        assert len(list(db.scalars(select(Candidate)))) == 2


def test_limits_cancel_retry_ownership(client, setup):
    _, episode, shot, workflows, _ = setup
    first = submit(client, shot, workflows).json()
    submit(client, shot, workflows)
    assert submit(client, shot, workflows).status_code == 429
    shot2 = post(client, f"/episodes/{episode['id']}/shots")
    assert submit(client, shot2, workflows).status_code == 202
    assert submit(client, shot2, workflows).status_code == 429
    post(client, f"/tasks/{first['id']}/cancel")
    worker.generate.run(first["id"])
    assert client.get(f"/api/v1/tasks/{first['id']}").json()["status"] == "canceled"
    retry = post(client, f"/tasks/{first['id']}/retry", idempotency_key="retry")
    assert retry["id"] != first["id"] and retry["retry_of_task_id"] == first["id"]
    assert retry["snapshot_json"] == first["snapshot_json"]
    token = client.post("/api/v1/auth/register", json={"email":"other@example.com", "password":"password123"}).json()["access_token"]
    assert client.get(f"/api/v1/tasks/{first['id']}", headers={"Authorization":f"Bearer {token}"}).status_code == 404


def test_failure_not_retried_and_snapshot_guard(client, setup):
    _, _, shot, workflows, factory = setup
    task = submit(client, shot, workflows, mock_error="TIMEOUT").json()
    worker.generate.run(task["id"])
    result = client.get(f"/api/v1/tasks/{task['id']}").json()
    assert result["status"] == "failed" and result["error_code"] == "TIMEOUT"
    assert "额外算力" in result["error_message"]
    with factory() as db:
        assert len(list(db.scalars(select(GenerationTask)))) == 1
        stored = db.get(GenerationTask, task["id"])
        stored.snapshot_json = {}
        with pytest.raises(ValueError, match="immutable"):
            db.commit()


def test_pure_rules():
    assert transition("queued", "running") == "running"
    with pytest.raises(ValueError):
        transition("succeeded", "running")
    graph = {"42":{"inputs":{"text":"old"}}}
    assert fill_workflow(graph, {"prompt":{"node_id":"42","input":"text"}}, {"prompt":"new"})["42"]["inputs"]["text"] == "new"
    assert graph["42"]["inputs"]["text"] == "old"
    with pytest.raises(ValueError):
        fill_workflow(graph, {}, {"seed":1})
    params = {"seed":2}
    result = build_snapshot(content_version=1,prompt="p",references=[],asset_version_ids=[],workflow={"id":"w","version":1,"name":"m"},params=params)
    params["seed"] = 3
    assert result["seed"] == 2 and result["params"]["seed"] == 2
