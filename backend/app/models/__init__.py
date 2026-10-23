from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Row(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Content(Row):
    __abstract__ = True
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(default=1)


class User(Row):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class ModelConfig(Row):
    __tablename__ = "model_configs"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(40))
    base_url: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    secret_env: Mapped[str] = mapped_column(String(100), default="")
    allow_local: Mapped[bool] = mapped_column(Boolean, default=False)


class CreativeCandidate(Row):
    __tablename__ = "creative_candidates"
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    model_config_id: Mapped[str] = mapped_column(ForeignKey("model_configs.id"), index=True)
    operation: Mapped[str] = mapped_column(String(30))
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    approval_state: Mapped[str] = mapped_column(String(20), default="pending")
    version: Mapped[int] = mapped_column(default=1)


@event.listens_for(CreativeCandidate, "before_update")
def immutable_creative_snapshot(mapper: Any, connection: Any, target: CreativeCandidate) -> None:
    state = inspect(target)
    for field in ("episode_id", "model_config_id", "operation", "input_json", "output_json", "provenance_json"):
        if state.attrs[field].history.has_changes():
            raise ValueError("immutable creative snapshot")


class Project(Content):
    __tablename__ = "projects"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    style_prompt: Mapped[str] = mapped_column(Text, default="")
    aspect_ratio: Mapped[str] = mapped_column(default="9:16")
    resolution: Mapped[str] = mapped_column(default="1080x1920")
    fps: Mapped[int] = mapped_column(default=24)
    production_type: Mapped[str] = mapped_column(default="dialogue_drama")


class Episode(Content):
    __tablename__ = "episodes"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    episode_no: Mapped[int] = mapped_column(default=1)
    title: Mapped[str] = mapped_column(String(200))
    target_duration_sec: Mapped[int] = mapped_column(default=60)
    confirmed_script_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("script_versions.id", use_alter=True, name="fk_episode_confirmed"), index=True
    )


class Scene(Content):
    __tablename__ = "scenes"
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    order_no: Mapped[int] = mapped_column(default=0)
    time_of_day: Mapped[str] = mapped_column(default="白天")
    location_asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), index=True)
    title: Mapped[str] = mapped_column(default="新场次")
    summary: Mapped[str] = mapped_column(Text, default="")


class Line(Content):
    __tablename__ = "scene_lines"
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    order_no: Mapped[int] = mapped_column(default=0)
    line_type: Mapped[str] = mapped_column(default="dialogue")
    character_asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScriptVersion(Row):
    __tablename__ = "script_versions"
    __table_args__ = (UniqueConstraint("episode_id", "version_no"),)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    version_no: Mapped[int] = mapped_column()
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    note: Mapped[str] = mapped_column(Text, default="")
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Asset(Content):
    __tablename__ = "assets"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    asset_type: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column(String(200))
    parent_asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), index=True)
    current_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("asset_versions.id", use_alter=True, name="fk_asset_current"), index=True
    )


class File(Row):
    __tablename__ = "files"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    storage_key: Mapped[str] = mapped_column(unique=True)
    mime: Mapped[str] = mapped_column()
    size_bytes: Mapped[int] = mapped_column()
    sha256: Mapped[str] = mapped_column()
    width: Mapped[int | None] = mapped_column()
    height: Mapped[int | None] = mapped_column()
    duration_ms: Mapped[int | None] = mapped_column()


class AssetVersion(Row):
    __tablename__ = "asset_versions"
    __table_args__ = (UniqueConstraint("asset_id", "version_no"),)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    version_no: Mapped[int] = mapped_column()
    description: Mapped[str] = mapped_column(Text, default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reference_file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), index=True)
    voice_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Shot(Content):
    __tablename__ = "shots"
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id"), index=True)
    order_no: Mapped[int] = mapped_column(default=0)
    action_desc: Mapped[str] = mapped_column(Text, default="")
    shot_size: Mapped[str] = mapped_column(default="中景")
    camera_angle: Mapped[str] = mapped_column(default="平视")
    camera_movement: Mapped[str] = mapped_column(default="固定")
    blocking_desc: Mapped[str] = mapped_column(Text, default="")
    est_duration_ms: Mapped[int] = mapped_column(default=5000)
    use_keyframe: Mapped[bool] = mapped_column(Boolean, default=True)
    dialogue_source: Mapped[str] = mapped_column(default="dubbed")
    sfx_note: Mapped[str] = mapped_column(Text, default="")
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    prompt_overridden: Mapped[bool] = mapped_column(default=False)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_version: Mapped[int] = mapped_column(default=1)
    review_status: Mapped[str] = mapped_column(default="confirmed")
    review_reasons_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    adopted_keyframe_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id", use_alter=True, name="fk_shot_keyframe"), index=True
    )
    adopted_video_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id", use_alter=True, name="fk_shot_video"), index=True
    )


class Workflow(Row):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("name", "version"),)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(20))
    comfy_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    param_map_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column()
    enabled: Mapped[bool] = mapped_column(default=True)


class GenerationTask(Row):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        UniqueConstraint("owner_id", "idempotency_key"),
        CheckConstraint("(shot_id IS NULL) <> (asset_version_id IS NULL)", name="ck_task_target"),
        CheckConstraint("kind IN ('keyframe','video')", name="ck_task_kind"),
        CheckConstraint("status IN ('queued','running','succeeded','failed','canceled')", name="ck_task_status"),
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    shot_id: Mapped[str | None] = mapped_column(ForeignKey("shots.id"), index=True)
    asset_version_id: Mapped[str | None] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    retry_of_task_id: Mapped[str | None] = mapped_column(ForeignKey("generation_tasks.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    request_hash: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    comfy_prompt_id: Mapped[str | None] = mapped_column(String(100))
    seed: Mapped[int | None] = mapped_column()
    progress: Mapped[float | None] = mapped_column()
    error_code: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class Candidate(Row):
    __tablename__ = "candidates"
    task_id: Mapped[str] = mapped_column(ForeignKey("generation_tasks.id"), unique=True, index=True)
    shot_id: Mapped[str | None] = mapped_column(ForeignKey("shots.id"), index=True)
    asset_version_id: Mapped[str | None] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), index=True)
    duration_ms: Mapped[int | None] = mapped_column()
    meta_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


@event.listens_for(GenerationTask, "before_update")
def immutable_generation_snapshot(mapper: Any, connection: Any, target: GenerationTask) -> None:
    state = inspect(target)
    for field in ("owner_id", "project_id", "shot_id", "asset_version_id", "workflow_id",
                  "kind", "snapshot_json", "request_hash", "idempotency_key", "retry_of_task_id", "seed"):
        if state.attrs[field].history.has_changes():
            raise ValueError("immutable generation snapshot")


class ShotLine(Row):
    __tablename__ = "shot_lines"
    __table_args__ = (UniqueConstraint("shot_id", "line_id"),)
    shot_id: Mapped[str] = mapped_column(ForeignKey("shots.id"), index=True)
    line_id: Mapped[str] = mapped_column(ForeignKey("scene_lines.id"), index=True)
    order_no: Mapped[int] = mapped_column()


class ShotCreativeImage(Row):
    __tablename__ = "shot_creative_images"
    shot_id: Mapped[str] = mapped_column(ForeignKey("shots.id"), unique=True, index=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("creative_candidates.id"), index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), index=True)


class ShotRef(Row):
    __tablename__ = "shot_asset_refs"
    shot_id: Mapped[str] = mapped_column(ForeignKey("shots.id"), index=True)
    asset_version_id: Mapped[str] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    role: Mapped[str] = mapped_column(default="reference")
    order_no: Mapped[int] = mapped_column()


def immutable(*args: Any) -> None:
    raise ValueError("版本只允许追加")


for model in (ScriptVersion, AssetVersion):
    event.listen(model, "before_update", immutable)
    event.listen(model, "before_delete", immutable)

event.listen(Candidate, "before_update", immutable)
event.listen(Candidate, "before_delete", immutable)
event.listen(GenerationTask, "before_delete", immutable)
