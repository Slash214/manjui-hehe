import os
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.snapshot import build_snapshot, digest
from app.domain.task_state import ACTIVE, transition
from app.models import Asset, AssetVersion, Candidate, File, GenerationTask, Shot, ShotRef, Workflow, utcnow
from app.repos.generation import active_count, lock_owner
from app.services.content import ContentService, Problem, dump


class GenerationService:
    def __init__(self, db: Session, user_id: str):
        self.db, self.user_id = db, user_id
        self.content = ContentService(db, user_id)

    def task(self, id: str) -> GenerationTask:
        task = self.db.get(GenerationTask, id)
        if task is None or task.owner_id != self.user_id:
            raise Problem(404, "NOT_FOUND", "任务不存在。")
        return task

    def submit(self, target_id: str, body: dict[str, Any], asset: bool = False,
               retry: GenerationTask | None = None) -> GenerationTask:
        lock_owner(self.db, self.user_id)
        request_hash = digest({"target": target_id, "asset": asset, "body": body,
                               "retry": retry.id if retry else None})
        existing = self.db.scalar(select(GenerationTask).where(
            GenerationTask.owner_id == self.user_id, GenerationTask.idempotency_key == body["idempotency_key"]))
        if existing:
            if existing.request_hash != request_hash:
                raise Problem(409, "IDEMPOTENCY_CONFLICT", "本次提交标识已用于其他参数，请重新提交。")
            return existing
        target = self.content.get(AssetVersion if asset else Shot, target_id)
        self.content.lock(target)
        # Refresh after project lock to snapshot the committed content and ordered references atomically.
        self.db.refresh(target)
        workflow = self.db.get(Workflow, body["workflow_id"])
        if workflow is None or not workflow.enabled or workflow.kind != body["kind"]:
            raise Problem(422, "WORKFLOW_REQUIRED", "请选择可用且类型匹配的工作流。")
        if asset and body["kind"] != "keyframe":
            raise Problem(422, "INVALID_INPUT", "资产仅支持参考图生成。")
        if workflow.provider == "comfy" and os.getenv("COMFYUI_ENABLED", "false").lower() != "true":
            raise Problem(503, "COMFY_DISABLED", "请先配置并启用 ComfyUI，再提交真实生成。")
        if active_count(self.db, self.user_id) >= 3 or (not asset and active_count(self.db, self.user_id, target_id) >= 2):
            raise Problem(429, "CONCURRENCY_LIMIT", "最多同时提交每镜头 2 个、每账号 3 个任务，请等待或取消已有任务。")
        overrides = body.get("overrides", {})
        if retry and not overrides:
            snapshot = deepcopy(retry.snapshot_json)
        else:
            params: dict[str, Any] = {"width": 320, "height": 568, "fps": 24, "frame_count": 24} if workflow.provider == "mock" else {}
            params.update(target.params_json)
            params.update(overrides)
            self.validate_params(params, workflow)
            refs, version_ids = [], []
            first_frame = None
            if not asset:
                for ref in self.db.scalars(select(ShotRef).where(ShotRef.shot_id == target.id).order_by(ShotRef.order_no, ShotRef.id)):
                    version = self.content.get(AssetVersion, ref.asset_version_id)
                    version_ids.append(version.id)
                    if version.reference_file_id:
                        refs.append({**self.file(version.reference_file_id), "order_no": ref.order_no,
                                     "asset_version_id": version.id})
                if body["kind"] == "video" and target.use_keyframe:
                    candidate = self.db.get(Candidate, target.adopted_keyframe_candidate_id) if target.adopted_keyframe_candidate_id else None
                    if candidate is None:
                        raise Problem(422, "KEYFRAME_REQUIRED", "请先采用关键画面，再生成视频。")
                    first_frame = self.file(candidate.file_id)
                prompt, version_no = target.prompt_text, target.content_version
            else:
                prompt, version_no = target.prompt, target.version_no
                version_ids = [target.id]
                if target.reference_file_id:
                    refs.append({**self.file(target.reference_file_id), "order_no": 0, "asset_version_id": target.id})
            snapshot = build_snapshot(content_version=version_no, prompt=prompt, references=refs,
                                      asset_version_ids=version_ids, workflow=dump(workflow), params=params, first_frame=first_frame)
            if workflow.provider == "comfy":
                required = {"prompt"} | {f"ref_image_{n}" for n in range(1, len(refs) + 1)}
                if first_frame:
                    required.add("first_frame")
                if required - workflow.param_map_json.keys():
                    raise Problem(422, "COMFY_VALIDATION", "工作流缺少提示词、参考图或首帧映射，请补全后提交。")
        task = GenerationTask(owner_id=self.user_id, project_id=self.content.project(target).id,
                              shot_id=None if asset else target.id, asset_version_id=target.id if asset else None,
                              kind=body["kind"], workflow_id=workflow.id, snapshot_json=snapshot,
                              seed=snapshot["seed"], idempotency_key=body["idempotency_key"], request_hash=request_hash,
                              retry_of_task_id=retry.id if retry else None)
        self.db.add(task)
        self.db.flush()
        # Durable queued rows are dispatched by the worker maintenance loop after this transaction commits.
        return task

    def file(self, id: str) -> dict[str, Any]:
        file = self.content.get(File, id)
        return {"file_id": file.id, "storage_key": file.storage_key, "mime": file.mime}

    @staticmethod
    def validate_params(params: dict[str, Any], workflow: Workflow) -> None:
        allowed = {"seed", "width", "height", "fps", "frame_count", "negative_prompt"}
        if workflow.provider == "mock":
            allowed |= {"mock_delay_sec", "mock_error"}
        if params.keys() - allowed:
            raise Problem(422, "INVALID_PARAMS", "参数不受当前生成适配器支持。")
        for name, low, high in (("width", 64, 2048), ("height", 64, 2048), ("fps", 1, 60),
                                ("frame_count", 1, 1800), ("seed", 0, 2147483647), ("mock_delay_sec", 0, 120)):
            if name in params and (type(params[name]) is not int or not low <= params[name] <= high):
                raise Problem(422, "INVALID_PARAMS", f"参数 {name} 超出允许范围。")
        if any(params.get(key, 64) % 2 for key in ("width", "height")):
            raise Problem(422, "INVALID_PARAMS", "图像宽高必须为偶数。")
        if "negative_prompt" in params and (not isinstance(params["negative_prompt"], str) or len(params["negative_prompt"]) > 10000):
            raise Problem(422, "INVALID_PARAMS", "反向提示词格式不正确。")
        from app.providers.generation.base import ERRORS
        if "mock_error" in params and params["mock_error"] not in ERRORS:
            raise Problem(422, "INVALID_PARAMS", "未知测试错误类型。")
        if workflow.provider == "comfy" and params.keys() - workflow.param_map_json.keys():
            raise Problem(422, "INVALID_PARAMS", "工作流缺少所选参数映射。")

    def cancel(self, id: str) -> GenerationTask:
        task = self.task(id)
        self.db.refresh(task, with_for_update=True)
        if task.status in ACTIVE:
            task.status = transition(task.status, "canceled")
            task.finished_at = utcnow()
            task.progress = None
        return task

    def adopt(self, candidate_id: str, target_id: str, base: int, asset: bool = False) -> dict[str, Any]:
        candidate = self.db.get(Candidate, candidate_id)
        if candidate is None:
            raise Problem(404, "NOT_FOUND", "候选不存在。")
        self.task(candidate.task_id)
        if (candidate.asset_version_id if asset else candidate.shot_id) != target_id:
            raise Problem(422, "INVALID_REFERENCE", "候选不属于当前目标。")
        if asset:
            original = self.content.get(AssetVersion, target_id)
            row = self.content.get(Asset, original.asset_id)
            self.content.bump(row, base)
            versions = list(self.db.scalars(select(AssetVersion).where(AssetVersion.asset_id == row.id)))
            version = AssetVersion(asset_id=row.id, version_no=max(v.version_no for v in versions) + 1,
                                   description=original.description, prompt=original.prompt,
                                   params_json=original.params_json, voice_config_json=original.voice_config_json,
                                   reference_file_id=candidate.file_id)
            self.db.add(version)
            self.db.flush()
            row.current_version_id = version.id
            return dump(version)
        shot = self.content.get(Shot, target_id)
        self.content.bump(shot, base)
        setattr(shot, f"adopted_{candidate.kind}_candidate_id", candidate.id)
        shot.review_status, shot.review_reasons_json = "confirmed", []
        self.db.flush()
        return self.content.shot(shot)
