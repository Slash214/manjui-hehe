import os
from typing import Any

from fastapi import APIRouter, Query
from pydantic import ValidationError
from sqlalchemy import select

from app.api.auth import DB, CurrentUser
from app.api.content import Service, Storage
from app.creative.catalog import CATALOG, RULES, catalog_contracts, provenance
from app.creative.contracts import OUTPUTS, ModelInput, Request, Strict
from app.creative.images import save_image
from app.creative.providers import MockProvider, OpenAICompatible, validate_endpoint
from app.models import (
    Asset,
    AssetVersion,
    CreativeCandidate,
    Episode,
    File,
    Line,
    ModelConfig,
    Scene,
    Shot,
    ShotCreativeImage,
)
from app.repos import rows
from app.services.content import ContentService, Problem, dump

router = APIRouter()


@router.get("/creative/status")
def status(user: CurrentUser) -> dict[str, Any]:
    return {"network_enabled": os.getenv("MANJU_MODEL_NETWORK_ENABLED", "false").lower() == "true",
            "protocol": "OpenAI-compatible chat/completions and images/generations",
            "reference_image_editing": False}


class Approval(Strict):
    base_version: int


class Revision(Approval):
    output: dict[str, Any]


@router.post("/creative/candidates/{id}/revise", status_code=201)
def revise(id: str, data: Revision, svc: Service) -> dict[str, Any]:
    original = svc.db.get(CreativeCandidate, id)
    if original is None:
        raise Problem(404, "NOT_FOUND", "候选不存在。")
    episode = svc.get(Episode, original.episode_id)
    svc.lock(episode)
    svc.db.refresh(original)
    if original.version != data.base_version or original.approval_state != "pending":
        raise Problem(409, "VERSION_CONFLICT", "候选状态已变化，请刷新。")
    if original.operation == "image":
        raise Problem(422, "UNSUPPORTED_OPERATION", "此协议不支持参考图编辑，请重新生成候选。")
    try:
        output = OUTPUTS[original.operation].model_validate(data.output).model_dump()
    except ValidationError as error:
        raise Problem(422, "INVALID_INPUT", "编辑内容不符合结构要求。") from error
    item = CreativeCandidate(episode_id=original.episode_id, model_config_id=original.model_config_id,
        operation=original.operation, input_json=original.input_json, output_json=output,
        provenance_json={**original.provenance_json, "revised_from": original.id, "edited_by": svc.user_id})
    svc.db.add(item)
    svc.db.flush()
    return dump(item)


def config_view(row: ModelConfig) -> dict[str, Any]:
    result = dump(row)
    result["credential_configured"] = bool(row.secret_env and os.getenv(row.secret_env))
    result["live_enabled"] = os.getenv("MANJU_MODEL_NETWORK_ENABLED", "false").lower() == "true"
    return result


@router.get("/creative/skills")
def skills(user: CurrentUser) -> dict[str, Any]:
    return {"items": catalog_contracts(), "total": len(CATALOG)}


@router.get("/creative/models")
def models(db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    items = db.scalars(select(ModelConfig).where(ModelConfig.owner_id == user.id)).all()
    return {"items": [config_view(item) for item in items[offset:offset + limit]], "total": len(items)}


@router.post("/creative/models", status_code=201)
def create_model(data: ModelInput, db: DB, user: CurrentUser) -> dict[str, Any]:
    validate_endpoint(data)
    item = ModelConfig(owner_id=user.id, **data.model_dump())
    db.add(item)
    db.flush()
    return config_view(item)


def snapshot(svc: ContentService, episode_id: str) -> dict[str, Any]:
    episode = svc.get(Episode, episode_id)
    project = svc.project(episode)
    scenes = rows(svc.db, Scene, episode_id=episode_id)
    return {"episode": dump(episode), "project": dump(project),
            "scenes": [dump(scene) for scene in scenes],
            "lines": [dump(line) for scene in scenes for line in rows(svc.db, Line, scene_id=scene.id)],
            "shots": [svc.shot(shot) for shot in rows(svc.db, Shot, episode_id=episode_id)],
            "assets": [dump(asset) for asset in rows(svc.db, Asset, project_id=project.id)]}


def versions(saved: dict[str, Any]) -> dict[str, int]:
    return {item["id"]: item.get("content_version", item.get("version", 1))
            for name in ("episode", "project", "scenes", "lines", "shots", "assets")
            for item in ([saved[name]] if name in {"episode", "project"} else saved[name])}


@router.get("/episodes/{id}/creative/candidates")
def candidates(id: str, svc: Service, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    svc.get(Episode, id)
    items = svc.db.scalars(select(CreativeCandidate).where(CreativeCandidate.episode_id == id)
                          .order_by(CreativeCandidate.created_at.desc())).all()
    return {"items": [dump(item) for item in items[offset:offset + limit]], "total": len(items)}


@router.post("/episodes/{id}/creative/candidates", status_code=201)
def create_candidate(id: str, data: Request, svc: Service, store: Storage) -> dict[str, Any]:
    episode = svc.get(Episode, id)
    svc.lock(episode)
    config = svc.db.get(ModelConfig, data.model_config_id)
    if config is None or config.owner_id != svc.user_id:
        raise Problem(404, "NOT_FOUND", "模型配置不存在。")
    if config.kind != ("image" if data.operation == "image" else "text"):
        raise Problem(422, "MODEL_CAPABILITY", "请选择对应的文本或图片模型。")
    if config.provider != "mock":
        if not config.secret_env or not os.getenv(config.secret_env):
            raise Problem(503, "MODEL_NOT_CONFIGURED", "服务端尚未配置模型密钥引用；不会自动切换演示模型。")
        if not data.actual_call:
            raise Problem(422, "CALL_CONFIRMATION_REQUIRED", "请明确选择实际调用模型；请求可能产生费用。")
    saved = snapshot(svc, id)
    if data.operation in {"dialogue", "prompt"}:
        target = next((item for item in saved["lines" if data.operation == "dialogue" else "shots"] if item["id"] == data.target_id), None)
        if target is None:
            raise Problem(422, "TARGET_REQUIRED", "请选择本集要改写的台词或镜头。")
    if data.operation == "image" and config.provider != "mock":
        target = svc.get(Asset if data.image_target == "asset" else Shot, str(data.target_id))
        if svc.project(target).id != episode.project_id or isinstance(target, Shot) and target.episode_id != id:
            raise Problem(422, "INVALID_REFERENCE", "图片目标必须属于本项目或本集。")
    provider = (MockProvider() if config.provider == "mock" else OpenAICompatible(
        config.base_url, config.model, os.environ[config.secret_env], allow_local=config.allow_local))
    image_prompt = RULES["prompt"][1] + "\n全局画风：" + saved["project"]["style_prompt"] + "\n画面要求：" + data.instruction
    output = provider.generate_image(image_prompt) if data.operation == "image" else provider.generate(data.operation, data.instruction, saved)
    if data.operation == "image" and config.provider != "mock":
        saved_file = save_image(output, svc, episode.project_id, store)
        output = {"prompt": image_prompt, "mock": False, "media_created": True, "file_id": saved_file.id}
    try:
        output = OUTPUTS[data.operation].model_validate(output).model_dump()
    except ValidationError as error:
        raise Problem(502, "INVALID_MODEL_OUTPUT", "候选格式不合要求，当前内容未改变。") from error
    source = provenance(data.operation)
    source.update({"inputVersionIds": versions(saved), "modelConfigId": config.id,
                   "mock": config.provider == "mock", "inputSchema": Request.model_json_schema(),
                   "outputSchema": OUTPUTS[data.operation].model_json_schema()})
    item = CreativeCandidate(episode_id=id, model_config_id=config.id, operation=data.operation,
        input_json={"snapshot": saved, "instruction": data.instruction, "target_id": data.target_id, "image_target": data.image_target},
        output_json=output, provenance_json=source)
    svc.db.add(item)
    svc.db.flush()
    return dump(item)


@router.post("/creative/candidates/{id}/adopt")
def adopt(id: str, data: Approval, svc: Service) -> dict[str, Any]:
    item = svc.db.get(CreativeCandidate, id)
    if item is None:
        raise Problem(404, "NOT_FOUND", "候选不存在。")
    episode = svc.get(Episode, item.episode_id)
    svc.lock(episode)
    svc.db.refresh(item)
    if item.version != data.base_version or item.approval_state != "pending":
        raise Problem(409, "VERSION_CONFLICT", "此候选已处理，请刷新。")
    if item.operation == "image" and not item.output_json.get("media_created"):
        raise Problem(422, "NO_IMAGE_CREATED", "这是图片接口演示，没有真实图片可采用。")
    if versions(snapshot(svc, episode.id)) != item.provenance_json["inputVersionIds"]:
        raise Problem(409, "VERSION_CONFLICT", "输入内容已变化，请保留此候选并重新生成。")
    output = OUTPUTS[item.operation].model_validate(item.output_json).model_dump()
    target = item.input_json["target_id"]
    if item.operation == "image":
        file = svc.get(File, output["file_id"])
        if file.project_id != episode.project_id:
            raise Problem(422, "INVALID_REFERENCE", "图片不属于当前项目。")
        if item.input_json["image_target"] == "asset":
            asset = svc.get(Asset, target)
            original = svc.get(AssetVersion, asset.current_version_id) if asset.current_version_id else None
            values = {"description": original.description if original else "", "prompt": output["prompt"],
                      "params_json": original.params_json if original else {},
                      "voice_config_json": original.voice_config_json if original else {}, "reference_file_id": file.id}
            version = svc.asset_version(asset.id, item.provenance_json["inputVersionIds"][target], values)
            asset.current_version_id = version.id
        else:
            shot = svc.get(Shot, target)
            svc.bump(shot, item.provenance_json["inputVersionIds"][target])
            current = svc.db.scalar(select(ShotCreativeImage).where(ShotCreativeImage.shot_id == shot.id))
            if current is None:
                svc.db.add(ShotCreativeImage(shot_id=shot.id, candidate_id=item.id, file_id=file.id))
            else:
                current.candidate_id, current.file_id = item.id, file.id
    elif item.operation == "script":
        offset = len(rows(svc.db, Scene, episode_id=episode.id))
        for index, scene in enumerate(output["scenes"]):
            created = svc.create(Scene, {"title": scene["title"], "order_no": offset + index}, episode.id)
            for order, line in enumerate(scene["lines"]):
                svc.create(Line, {**line, "order_no": order}, created.id)
    elif item.operation == "assets":
        for asset in output["assets"]:
            created = svc.create(Asset, {"name": asset["name"], "asset_type": asset["asset_type"]}, episode.project_id)
            svc.asset_version(created.id, 1, {"description": asset["description"]})
    elif item.operation == "shots":
        offset = len(rows(svc.db, Shot, episode_id=episode.id))
        for index, shot in enumerate(output["shots"]):
            svc.create(Shot, {**shot, "order_no": offset + index}, episode.id)
    else:
        base = item.provenance_json["inputVersionIds"][target]
        if item.operation == "dialogue":
            svc.patch(Line, target, {"text": output["text"], "base_version": base})
        else:
            svc.patch(Shot, target, {"prompt_text": output["text"], "prompt_overridden": True, "base_version": base})
    item.approval_state = "adopted"
    item.version += 1
    svc.db.flush()
    return dump(item)
