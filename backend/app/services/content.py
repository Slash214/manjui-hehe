from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.domain.prompt import build_prompt
from app.models import (
    Asset,
    AssetVersion,
    Content,
    Episode,
    File,
    Line,
    Project,
    Row,
    Scene,
    ScriptVersion,
    Shot,
    ShotCreativeImage,
    ShotLine,
    ShotRef,
    utcnow,
)
from app.repos import rows
from app.schemas import AssetInput, EpisodeInput, LineInput, ProjectInput, SceneInput, ShotInput

SCHEMAS: dict[type[Content], type[BaseModel]] = {
    Project: ProjectInput,
    Episode: EpisodeInput,
    Scene: SceneInput,
    Line: LineInput,
    Asset: AssetInput,
    Shot: ShotInput,
}
PARENTS: dict[type[Row], tuple[str, type[Row]]] = {
    Episode: ("project_id", Project),
    Scene: ("episode_id", Episode),
    Line: ("scene_id", Scene),
    Asset: ("project_id", Project),
    AssetVersion: ("asset_id", Asset),
    Shot: ("episode_id", Episode),
    ScriptVersion: ("episode_id", Episode),
    File: ("project_id", Project),
}


class Problem(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        self.status, self.code, self.message, self.details = status, code, message, details


def dump(row: Row) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for col in row.__table__.columns:
        value = getattr(row, col.name)
        result[col.name] = (
            value.isoformat() + ("Z" if value.tzinfo is None else "")
            if isinstance(value, datetime)
            else value
        )
    return result


class ContentService:
    def __init__(self, db: Session, user_id: str):
        self.db, self.user_id = db, user_id

    def get(self, model: type[Row], id: str) -> Any:
        row = self.db.get(model, id)
        if row is None or getattr(row, "deleted_at", None) is not None:
            raise Problem(404, "NOT_FOUND", "内容不存在或已删除，请刷新列表。")
        if isinstance(row, Project):
            if row.owner_id != self.user_id:
                raise Problem(404, "NOT_FOUND", "内容不存在。")
        else:
            field, parent = PARENTS[model]
            self.get(parent, getattr(row, field))
        return row

    def project(self, row: Row) -> Project:
        while not isinstance(row, Project):
            field, parent = PARENTS[type(row)]
            row = self.get(parent, getattr(row, field))
        return row

    def lock(self, row: Row) -> None:
        project = self.project(row)
        locked = self.db.scalar(
            select(Project)
            .where(Project.id == project.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked is None or locked.deleted_at is not None or locked.owner_id != self.user_id:
            raise Problem(404, "NOT_FOUND", "项目不存在或已删除。")

    def bump(self, row: Content, base: int) -> None:
        self.lock(row)
        field = "content_version" if isinstance(row, Shot) else "version"
        col = getattr(type(row), field)
        result = self.db.execute(
            update(type(row))
            .where(type(row).id == row.id, col == base)
            .values(**{field: col + 1, "updated_at": utcnow()})
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            self.db.refresh(row)
            raise Problem(
                409,
                "VERSION_CONFLICT",
                "其他页签已修改此内容，请保留本地草稿并载入最新版本。",
                {"current": dump(row)},
            )
        self.db.refresh(row)

    def validate(self, model: type[Content], data: dict[str, Any], old: Any = None) -> dict[str, Any]:
        schema = SCHEMAS[model]
        if old is not None:
            allowed = schema.model_fields
            if data.keys() - allowed.keys():
                raise Problem(422, "INVALID_INPUT", "包含不允许修改的字段。")
            data = {**{k: getattr(old, k) for k in allowed}, **data}
        try:
            return schema.model_validate(data).model_dump()
        except ValidationError as error:
            raise Problem(422, "INVALID_INPUT", "输入格式不正确，请检查内容。", str(error)) from error

    def validate_links(self, row: Content) -> None:
        project_id = self.project(row).id
        for field, kind in (
            ("location_asset_id", "location"),
            ("character_asset_id", "character"),
            ("parent_asset_id", "character"),
        ):
            if id := getattr(row, field, None):
                asset = self.get(Asset, id)
                if asset.project_id != project_id or asset.asset_type != kind:
                    raise Problem(422, "INVALID_REFERENCE", "引用资产必须属于本项目，且类型正确。")
        if isinstance(row, Asset) and (row.asset_type == "costume") != bool(row.parent_asset_id):
            raise Problem(422, "INVALID_REFERENCE", "造型必须关联角色，其他资产不设置父角色。")
        if (
            isinstance(row, Shot)
            and row.scene_id
            and self.get(Scene, row.scene_id).episode_id != row.episode_id
        ):
            raise Problem(422, "INVALID_REFERENCE", "镜头场次必须属于本集。")

    def prompt(self, shot: Shot) -> None:
        if shot.prompt_overridden:
            return
        descriptions = [
            self.get(AssetVersion, ref.asset_version_id).description
            for ref in rows(self.db, ShotRef, shot_id=shot.id)
        ]
        shot.prompt_text = build_prompt(
            self.project(shot).style_prompt,
            descriptions,
            shot.action_desc,
            shot.shot_size,
            shot.camera_angle,
            shot.blocking_desc,
        )

    def create(self, model: type[Content], data: dict[str, Any], parent_id: str | None) -> Content:
        values = self.validate(model, data)
        if model is Project:
            values["owner_id"] = self.user_id
        else:
            field, parent = PARENTS[model]
            parent_row = self.get(parent, str(parent_id))
            self.lock(parent_row)
            values[field] = parent_id
        row = model(**values)
        self.db.add(row)
        self.db.flush()
        self.validate_links(row)
        if isinstance(row, Shot):
            self.prompt(row)
        self.db.flush()
        return row

    def patch(self, model: type[Content], id: str, data: dict[str, Any]) -> Content:
        data = dict(data)
        base = data.pop("base_version", None)
        if not isinstance(base, int) or isinstance(base, bool) or base < 1:
            raise Problem(422, "BASE_VERSION_REQUIRED", "请提供编辑时的版本号。")
        row = self.get(model, id)
        values = self.validate(model, data, row)
        if isinstance(row, Asset) and values["asset_type"] != row.asset_type:
            raise Problem(422, "INVALID_INPUT", "资产创建后不可更改类型。")
        self.bump(row, base)
        for field, value in values.items():
            setattr(row, field, value)
        self.validate_links(row)
        if isinstance(row, Line):
            row.edited_at = utcnow()
        if isinstance(row, Shot):
            self.prompt(row)
        self.db.flush()
        return row

    def remove(self, model: type[Content], id: str, base: int) -> None:
        row = self.get(model, id)
        self.bump(row, base)
        # Keep references valid; removing a referenced scene/line requires explicit unbinding first.
        if isinstance(row, Scene):
            line_ids = [x.id for x in rows(self.db, Line, scene_id=id)]
            used = self.db.scalar(
                select(ShotLine.id)
                .join(Shot)
                .where(ShotLine.line_id.in_(line_ids), Shot.deleted_at.is_(None))
            )
            if used or rows(self.db, Shot, scene_id=id):
                raise Problem(409, "IN_USE", "请先解除镜头对场次或台词的引用，再删除。")
        if isinstance(row, Line) and self.db.scalar(
            select(ShotLine.id).join(Shot).where(ShotLine.line_id == id, Shot.deleted_at.is_(None))
        ):
            raise Problem(409, "IN_USE", "该台词仍被镜头引用，请先解除绑定。")
        row.deleted_at = utcnow()
        self.db.flush()

    def reorder(self, model: type[Content], parent_id: str, versions: dict[str, int]) -> list[Any]:
        field, parent = PARENTS[model]
        owner = self.get(parent, parent_id)
        self.lock(owner)
        items = rows(self.db, model, **{field: parent_id})
        if set(versions) != {item.id for item in items}:
            raise Problem(409, "LIST_CHANGED", "列表已变化，请刷新后重新排序。")
        by_id = {row.id: row for row in items}
        for index, (id, base) in enumerate(versions.items()):
            self.bump(by_id[id], base)
            by_id[id].order_no = index
        self.db.flush()
        return [by_id[id] for id in versions]

    def script(self, episode_id: str) -> dict[str, Any]:
        episode = self.get(Episode, episode_id)
        return {
            "episode": dump(episode),
            "scenes": [
                {**dump(scene), "lines": [dump(line) for line in rows(self.db, Line, scene_id=scene.id)]}
                for scene in rows(self.db, Scene, episode_id=episode_id)
            ],
        }

    def confirm(self, episode_id: str, base: int, note: str) -> ScriptVersion:
        episode = self.get(Episode, episode_id)
        self.bump(episode, base)
        version = ScriptVersion(
            episode_id=episode_id,
            version_no=self.next_version(ScriptVersion, episode_id),
            snapshot_json=self.script(episode_id),
            note=note,
            confirmed_by=self.user_id,
        )
        self.db.add(version)
        self.db.flush()
        episode.confirmed_script_version_id = version.id
        self.db.flush()
        return version

    def next_version(self, model: type[AssetVersion | ScriptVersion], parent_id: str) -> int:
        field, _ = PARENTS[model]
        maximum = self.db.scalar(select(func.max(model.version_no)).where(getattr(model, field) == parent_id))
        return int(maximum or 0) + 1

    def restore(self, episode_id: str, version_id: str, base: int) -> dict[str, Any]:
        episode = self.get(Episode, episode_id)
        version = self.get(ScriptVersion, version_id)
        if version.episode_id != episode_id:
            raise Problem(404, "NOT_FOUND", "此版本不属于本集。")
        self.bump(episode, base)
        snapshot = version.snapshot_json["scenes"]
        keep_scenes = {s["id"] for s in snapshot}
        keep_lines = {line["id"] for s in snapshot for line in s["lines"]}
        # Keep stable IDs for surviving lines so existing shot bindings remain meaningful.
        for scene in rows(self.db, Scene, episode_id=episode_id):
            if scene.id not in keep_scenes:
                scene.deleted_at = utcnow()
            for line in rows(self.db, Line, scene_id=scene.id):
                if line.id not in keep_lines:
                    line.deleted_at = utcnow()
        for saved in snapshot:
            scene = self.db.get(Scene, saved["id"])
            assert scene is not None  # Soft deletion retains every historical object.
            scene.deleted_at = None
            scene.version += 1
            for key in SceneInput.model_fields:
                setattr(scene, key, saved[key])
            for saved_line in saved["lines"]:
                line = self.db.get(Line, saved_line["id"])
                assert line is not None
                line.deleted_at = None
                line.version += 1
                line.edited_at = utcnow()
                for key in LineInput.model_fields:
                    setattr(line, key, saved_line[key])
        for shot in rows(self.db, Shot, episode_id=episode_id):
            bindings = rows(self.db, ShotLine, shot_id=shot.id)
            if shot.scene_id not in keep_scenes or any(x.line_id not in keep_lines for x in bindings):
                shot.content_version += 1
                if shot.scene_id not in keep_scenes:
                    shot.scene_id = None
                for binding in bindings:
                    if binding.line_id not in keep_lines:
                        self.db.delete(binding)
        self.db.flush()
        return self.script(episode_id)

    def asset_version(self, asset_id: str, base: int, values: dict[str, Any]) -> AssetVersion:
        asset = self.get(Asset, asset_id)
        self.bump(asset, base)
        version = AssetVersion(
            asset_id=asset_id, version_no=self.next_version(AssetVersion, asset_id), **values
        )
        self.db.add(version)
        self.db.flush()
        if asset.current_version_id is None:
            asset.current_version_id = version.id
        self.db.flush()
        return version

    def bindings(self, shot_id: str, base: int, ids: list[str], refs: bool) -> dict[str, Any]:
        shot = self.get(Shot, shot_id)
        self.bump(shot, base)
        if len(set(ids)) != len(ids):
            raise Problem(422, "INVALID_REFERENCE", "引用列表不能重复。")
        model = ShotRef if refs else ShotLine
        for id in ids:
            target = self.get(AssetVersion if refs else Line, id)
            if self.project(target).id != self.project(shot).id:
                raise Problem(422, "INVALID_REFERENCE", "不能引用其他项目的内容。")
            if not refs and self.get(Scene, target.scene_id).episode_id != shot.episode_id:
                raise Problem(422, "INVALID_REFERENCE", "台词必须属于本集。")
        self.db.execute(delete(model).where(model.shot_id == shot_id))
        for index, id in enumerate(ids):
            self.db.add(
                model(shot_id=shot_id, order_no=index, **{"asset_version_id" if refs else "line_id": id})
            )
        self.db.flush()
        self.prompt(shot)
        self.db.flush()
        return self.shot(shot)

    def shot(self, shot: Shot) -> dict[str, Any]:
        image = self.db.scalar(select(ShotCreativeImage).where(ShotCreativeImage.shot_id == shot.id))
        return {
            **dump(shot),
            "refs": [dump(x) for x in rows(self.db, ShotRef, shot_id=shot.id)],
            "lines": [dump(x) for x in rows(self.db, ShotLine, shot_id=shot.id)],
            "creative_keyframe_candidate_id": image.candidate_id if image else None,
            "creative_keyframe_file_id": image.file_id if image else None,
        }
