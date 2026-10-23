from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.auth import DB, CurrentUser
from app.models import AssetVersion, Candidate, GenerationTask, Shot, Workflow
from app.services.content import Problem, dump
from app.services.generation import GenerationService
from app.services.workflows import register_workflows

router = APIRouter()


class Submit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["keyframe", "video"]
    workflow_id: str
    idempotency_key: str = Field(min_length=1, max_length=128)
    overrides: dict[str, Any] = Field(default_factory=dict)


class Retry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=1, max_length=128)
    overrides: dict[str, Any] = Field(default_factory=dict)


class Adopt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    base_version: int = Field(ge=1)


@router.get("/workflows")
def workflows(db: DB, user: CurrentUser) -> list[dict[str, Any]]:
    register_workflows(db)
    return [dump(row) for row in db.scalars(select(Workflow).where(Workflow.enabled.is_(True)).order_by(Workflow.name, Workflow.version))]


@router.post("/shots/{id}/generate", status_code=202)
def submit_shot(id: str, body: Submit, db: DB, user: CurrentUser) -> dict[str, Any]:
    return dump(GenerationService(db, user.id).submit(id, body.model_dump()))


@router.post("/asset-versions/{id}/generate", status_code=202)
def submit_asset(id: str, body: Submit, db: DB, user: CurrentUser) -> dict[str, Any]:
    return dump(GenerationService(db, user.id).submit(id, body.model_dump(), asset=True))


@router.get("/tasks/{id}")
def task(id: str, db: DB, user: CurrentUser) -> dict[str, Any]:
    return dump(GenerationService(db, user.id).task(id))


@router.post("/tasks/{id}/cancel")
def cancel(id: str, db: DB, user: CurrentUser) -> dict[str, Any]:
    return dump(GenerationService(db, user.id).cancel(id))


@router.post("/tasks/{id}/retry", status_code=202)
def retry(id: str, body: Retry, db: DB, user: CurrentUser) -> dict[str, Any]:
    service = GenerationService(db, user.id)
    original = service.task(id)
    if original.status not in ("failed", "canceled"):
        raise Problem(409, "TASK_NOT_RETRYABLE", "仅失败或已取消的任务可重试。")
    return dump(service.submit(original.shot_id or str(original.asset_version_id),
                               {**body.model_dump(), "kind": original.kind, "workflow_id": original.workflow_id},
                               asset=original.shot_id is None, retry=original))


def listing(id: str, db: DB, user: CurrentUser, asset: bool, candidates: bool, offset: int, limit: int) -> list[dict[str, Any]]:
    GenerationService(db, user.id).content.get(AssetVersion if asset else Shot, id)
    model = Candidate if candidates else GenerationTask
    field = model.asset_version_id if asset else model.shot_id
    return [dump(row) for row in db.scalars(select(model).where(field == id).order_by(model.created_at.desc(), model.id).offset(offset).limit(limit))]


@router.get("/shots/{id}/tasks")
def shot_tasks(id: str, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    return listing(id, db, user, False, False, offset, limit)


@router.get("/asset-versions/{id}/tasks")
def asset_tasks(id: str, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    return listing(id, db, user, True, False, offset, limit)


@router.get("/shots/{id}/candidates")
def shot_candidates(id: str, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    return listing(id, db, user, False, True, offset, limit)


@router.get("/asset-versions/{id}/candidates")
def asset_candidates(id: str, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)) -> list[dict[str, Any]]:
    return listing(id, db, user, True, True, offset, limit)


@router.post("/shots/{id}/adopt")
def adopt_shot(id: str, body: Adopt, db: DB, user: CurrentUser) -> dict[str, Any]:
    return GenerationService(db, user.id).adopt(body.candidate_id, id, body.base_version)


@router.post("/asset-versions/{id}/adopt")
def adopt_asset(id: str, body: Adopt, db: DB, user: CurrentUser) -> dict[str, Any]:
    return GenerationService(db, user.id).adopt(body.candidate_id, id, body.base_version, asset=True)
