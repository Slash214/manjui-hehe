import os
from io import BytesIO

os.environ.setdefault("JWT_SECRET", "test-secret-is-long-enough-for-local-tests-only")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base
from app.providers.storage import MockStorage, storage
from app.repos import database


@pytest.fixture
def client():
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        from sqlalchemy.engine import make_url
        if not (make_url(test_url).database or "").startswith("manju_phase1_verify_"):
            raise RuntimeError("External tests require an isolated manju_phase1_verify_ database")
        engine = create_engine(test_url)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def db():
        with Session(engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[database] = db
    mock = MockStorage()
    app.dependency_overrides[storage] = lambda: mock
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register", json={"email": "creator@example.com", "password": "password123"}
        )
        assert response.status_code == 201, response.text
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        yield client
    app.dependency_overrides.clear()
    if test_url:
        Base.metadata.drop_all(engine)
    engine.dispose()


def post(client, path, **data):
    response = client.post("/api/v1" + path, json=data)
    assert response.is_success, response.text
    return response.json()


def patch(client, path, **data):
    response = client.patch("/api/v1" + path, json=data)
    assert response.is_success, response.text
    return response.json()


def fixture_content(client):
    project = post(client, "/projects", name="大唐小饭馆")
    episode = post(client, f"/projects/{project['id']}/episodes", title="第一集")
    scene = post(client, f"/episodes/{episode['id']}/scenes", title="饭馆大堂")
    line = post(client, f"/scenes/{scene['id']}/lines", text="三个月房租，今天必须结清！")
    return project, episode, scene, line


def test_full_stage_one_flow(client):
    project, episode, scene, line = fixture_content(client)
    confirmed = post(client, f"/episodes/{episode['id']}/script/confirm", base_version=1)
    assert confirmed["snapshot_json"]["scenes"][0]["lines"][0]["text"] == line["text"]
    changed = patch(client, f"/lines/{line['id']}", text="再来一碗。", base_version=1)
    assert changed["version"] == 2
    restored = post(
        client, f"/episodes/{episode['id']}/script/versions/{confirmed['id']}/restore", base_version=2
    )
    assert restored["scenes"][0]["lines"][0]["text"] == line["text"]
    assert client.get(f"/api/v1/episodes/{episode['id']}/script/versions").json()["total"] == 1
    asset = post(client, f"/projects/{project['id']}/assets", name="沈知味", asset_type="character")
    version = post(client, f"/assets/{asset['id']}/versions", description="青衣少年", base_version=1)
    location = post(client, f"/projects/{project['id']}/assets", name="饭馆大堂", asset_type="location")
    location_version = post(
        client, f"/assets/{location['id']}/versions", description="木桌与窗", base_version=1
    )
    shot = post(client, f"/episodes/{episode['id']}/shots", scene_id=scene["id"], action_desc="掌柜拍桌")
    refs = client.put(
        f"/api/v1/shots/{shot['id']}/refs",
        json={"base_version": 1, "asset_version_ids": [version["id"], location_version["id"]]},
    )
    assert refs.status_code == 200, refs.text
    assert refs.json()["content_version"] == 2
    bound = client.put(
        f"/api/v1/shots/{shot['id']}/lines", json={"base_version": 2, "line_ids": [line["id"]]}
    )
    assert bound.status_code == 200
    assert bound.json()["content_version"] == 3
    first = patch(client, f"/shots/{shot['id']}", base_version=3, action_desc="放下饭碗")
    assert first["content_version"] == 4
    conflict = client.patch(
        f"/api/v1/shots/{shot['id']}", json={"base_version": 3, "action_desc": "不能覆盖"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "VERSION_CONFLICT"
    assert client.get(f"/api/v1/shots/{shot['id']}").json()["action_desc"] == "放下饭碗"


def test_ownership_and_cross_project_references(client):
    project, episode, _scene, line = fixture_content(client)
    other = post(client, "/projects", name="其他项目")
    asset = post(client, f"/projects/{other['id']}/assets", name="外部角色", asset_type="character")
    version = post(client, f"/assets/{asset['id']}/versions", base_version=1)
    shot = post(client, f"/episodes/{episode['id']}/shots")
    response = client.put(
        f"/api/v1/shots/{shot['id']}/refs", json={"base_version": 1, "asset_version_ids": [version["id"]]}
    )
    assert response.status_code == 422
    user2 = post(client, "/auth/register", email="other@example.com", password="password123")
    client.headers["Authorization"] = "Bearer " + user2["access_token"]
    for path in [
        f"/projects/{project['id']}",
        f"/shots/{shot['id']}",
        f"/lines/{line['id']}",
        f"/episodes/{episode['id']}/script",
        f"/assets/{asset['id']}/versions",
    ]:
        assert client.get("/api/v1" + path).status_code == 404


def test_upload_appends_and_current_not_silently_changed(client):
    project, *_ = fixture_content(client)
    asset = post(client, f"/projects/{project['id']}/assets", name="沈知味", asset_type="character")
    version = post(client, f"/assets/{asset['id']}/versions", base_version=1, description="原描述")
    image = BytesIO()
    Image.new("RGB", (2, 2)).save(image, format="PNG")
    response = client.post(
        f"/api/v1/asset-versions/{version['id']}/reference-image",
        data={"base_version": 2},
        files={"file": ("image.png", image.getvalue(), "image/png")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["version_no"] == 2
    versions = client.get(f"/api/v1/assets/{asset['id']}/versions").json()["items"]
    assert versions[0]["reference_file_id"] is None
    assert client.get(f"/api/v1/assets/{asset['id']}").json()["current_version_id"] == version["id"]
    assert (
        client.get(f"/api/v1/files/{response.json()['reference_file_id']}/url").json()["expires_in"] == 3600
    )
    invalid = client.post(
        f"/api/v1/asset-versions/{version['id']}/reference-image",
        data={"base_version": 3},
        files={"file": ("image.png", b"not an image", "image/png")},
    )
    assert invalid.status_code == 422


def test_reorder_conflicts_atomic_and_soft_delete(client):
    project, episode, *_ = fixture_content(client)
    one = post(client, f"/episodes/{episode['id']}/shots", action_desc="一")
    two = post(client, f"/episodes/{episode['id']}/shots", action_desc="二", order_no=1)
    post(client, f"/episodes/{episode['id']}/shots/reorder", items={two["id"]: 1, one["id"]: 1})
    response = client.post(
        f"/api/v1/episodes/{episode['id']}/shots/reorder", json={"items": {one["id"]: 2, two["id"]: 1}}
    )
    assert response.status_code == 409
    saved = client.get(f"/api/v1/episodes/{episode['id']}/shots").json()["items"]
    assert [x["id"] for x in saved] == [two["id"], one["id"]]
    assert all(x["content_version"] == 2 for x in saved)
    assert client.delete(f"/api/v1/projects/{project['id']}?base_version=1").status_code == 200
    assert client.get(f"/api/v1/episodes/{episode['id']}").status_code == 404


def test_validation_and_password_storage(client):
    response = client.post("/api/v1/projects", json={"name": "", "owner_id": "hacker"})
    assert response.status_code == 422
    project = post(client, "/projects", name="test")
    assert client.patch(f"/api/v1/projects/{project['id']}", json={"name": "new"}).status_code == 422
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "creator@example.com", "password": "wrongpass"}
        ).status_code
        == 401
    )
