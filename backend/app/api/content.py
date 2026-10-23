import hashlib
from collections.abc import Callable
from io import BytesIO
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Form, Query, UploadFile
from PIL import Image, UnidentifiedImageError

from app.api.auth import DB, CurrentUser
from app.models import Asset, AssetVersion, Content, Episode, File, Line, Project, Scene, ScriptVersion, Shot
from app.providers.storage import StorageProvider, storage
from app.repos import rows
from app.schemas import (
    AssetVersionInput,
    ConfirmBody,
    CurrentBody,
    LinesBody,
    OrderBody,
    RefsBody,
    VersionBody,
)
from app.services.content import ContentService, Problem, dump

router = APIRouter()


def service(db: DB, user: CurrentUser) -> ContentService:
    return ContentService(db, user.id)


Service = Annotated[ContentService, Depends(service)]
Storage = Annotated[StorageProvider, Depends(storage)]


def register_resource(model: type[Content], collection: str, single: str, parent_field: str | None) -> None:
    def listing(
        svc: Service,
        parent_id: str | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
    ) -> dict[str, Any]:
        if parent_field:
            from app.services.content import PARENTS

            svc.get(PARENTS[model][1], str(parent_id))
            values = rows(svc.db, model, **{parent_field: parent_id})
        else:
            values = rows(svc.db, Project, owner_id=svc.user_id)
        return {
            "items": [
                svc.shot(x) if isinstance(x, Shot) else dump(x) for x in values[offset : offset + limit]
            ],
            "total": len(values),
        }

    def create(
        svc: Service, data: Annotated[dict[str, Any], Body()], parent_id: str | None = None
    ) -> dict[str, Any]:
        row = svc.create(model, data, parent_id)
        return svc.shot(row) if isinstance(row, Shot) else dump(row)

    def get(id: str, svc: Service) -> dict[str, Any]:
        row = svc.get(model, id)
        return svc.shot(row) if isinstance(row, Shot) else dump(row)

    def patch(id: str, svc: Service, data: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        row = svc.patch(model, id, data)
        return svc.shot(row) if isinstance(row, Shot) else dump(row)

    def remove(id: str, svc: Service, base_version: int = Query(..., ge=1)) -> dict[str, bool]:
        svc.remove(model, id, base_version)
        return {"deleted": True}

    routes: list[tuple[str, str, Callable[..., Any]]] = [
        ("GET", collection, listing),
        ("POST", collection, create),
        ("GET", single, get),
        ("PATCH", single, patch),
        ("DELETE", single, remove),
    ]
    for method, path, handler in routes:
        router.add_api_route(path, handler, methods=[method], name=f"{method}_{model.__tablename__}")


register_resource(Project, "/projects", "/projects/{id}", None)
register_resource(Episode, "/projects/{parent_id}/episodes", "/episodes/{id}", "project_id")
register_resource(Scene, "/episodes/{parent_id}/scenes", "/scenes/{id}", "episode_id")
register_resource(Line, "/scenes/{parent_id}/lines", "/lines/{id}", "scene_id")
register_resource(Asset, "/projects/{parent_id}/assets", "/assets/{id}", "project_id")
register_resource(Shot, "/episodes/{parent_id}/shots", "/shots/{id}", "episode_id")


@router.post("/episodes/{id}/shots/reorder")
def order_shots(id: str, body: OrderBody, svc: Service) -> list[dict[str, Any]]:
    return [svc.shot(x) for x in svc.reorder(Shot, id, body.items)]


@router.post("/episodes/{id}/scenes/reorder")
def order_scenes(id: str, body: OrderBody, svc: Service) -> list[dict[str, Any]]:
    return [dump(x) for x in svc.reorder(Scene, id, body.items)]


@router.post("/scenes/{id}/lines/reorder")
def order_lines(id: str, body: OrderBody, svc: Service) -> list[dict[str, Any]]:
    return [dump(x) for x in svc.reorder(Line, id, body.items)]


@router.get("/episodes/{id}/script")
def script(id: str, svc: Service) -> dict[str, Any]:
    return svc.script(id)


@router.post("/episodes/{id}/script/confirm")
def confirm(id: str, body: ConfirmBody, svc: Service) -> dict[str, Any]:
    return dump(svc.confirm(id, body.base_version, body.note))


@router.get("/episodes/{id}/script/versions")
def versions(
    id: str, svc: Service, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)
) -> dict[str, Any]:
    svc.get(Episode, id)
    values = rows(svc.db, ScriptVersion, episode_id=id)
    return {"items": [dump(x) for x in values[offset : offset + limit]], "total": len(values)}


@router.post("/episodes/{id}/script/versions/{vid}/restore")
def restore(id: str, vid: str, body: VersionBody, svc: Service) -> dict[str, Any]:
    return svc.restore(id, vid, body.base_version)


@router.get("/assets/{id}/versions")
def asset_versions(
    id: str, svc: Service, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)
) -> dict[str, Any]:
    svc.get(Asset, id)
    values = rows(svc.db, AssetVersion, asset_id=id)
    return {"items": [dump(x) for x in values[offset : offset + limit]], "total": len(values)}


@router.get("/asset-versions/{id}")
def asset_version_detail(id: str, svc: Service) -> dict[str, Any]:
    version = svc.get(AssetVersion, id)
    asset = svc.get(Asset, version.asset_id)
    return {
        **dump(version),
        "asset_name": asset.name,
        "has_new_current": asset.current_version_id not in (None, version.id),
    }


class NewVersion(AssetVersionInput):
    base_version: int


@router.post("/assets/{id}/versions", status_code=201)
def add_version(id: str, body: NewVersion, svc: Service) -> dict[str, Any]:
    return dump(svc.asset_version(id, body.base_version, body.model_dump(exclude={"base_version"})))


@router.post("/assets/{id}/set-current")
def set_current(id: str, body: CurrentBody, svc: Service) -> dict[str, Any]:
    asset, version = svc.get(Asset, id), svc.get(AssetVersion, body.version_id)
    if version.asset_id != id:
        raise Problem(422, "INVALID_REFERENCE", "请选择该资产的版本。")
    svc.bump(asset, body.base_version)
    asset.current_version_id = version.id
    svc.db.flush()
    return dump(asset)


@router.post("/asset-versions/{id}/reference-image", status_code=201)
async def upload_image(
    id: str, file: UploadFile, svc: Service, store: Storage, base_version: Annotated[int, Form(ge=1)]
) -> dict[str, Any]:
    original = svc.get(AssetVersion, id)
    asset = svc.get(Asset, original.asset_id)
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise Problem(413, "FILE_TOO_LARGE", "图片不能超过 20MB，请压缩后上传。")
    try:
        with Image.open(BytesIO(content)) as image:
            if image.format not in ("PNG", "JPEG", "WEBP"):
                raise ValueError()
            width, height, mime = image.width, image.height, Image.MIME[image.format]
            image.verify()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as error:
        raise Problem(422, "INVALID_IMAGE", "请选择有效的 PNG、JPEG 或 WebP 图片。") from error
    svc.bump(asset, base_version)
    key = f"{asset.project_id}/{uuid4()}"
    try:
        store.put(key, content, mime)
    except Exception as error:
        raise Problem(503, "STORAGE_ERROR", "图片保存失败，请检查存储服务后重试。") from error
    saved = File(
        project_id=asset.project_id,
        storage_key=key,
        mime=mime,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        width=width,
        height=height,
    )
    svc.db.add(saved)
    svc.db.flush()
    values = {field: getattr(original, field) for field in AssetVersionInput.model_fields}
    new = AssetVersion(
        asset_id=asset.id,
        version_no=svc.next_version(AssetVersion, asset.id),
        reference_file_id=saved.id,
        **values,
    )
    svc.db.add(new)
    svc.db.flush()
    return dump(new)


@router.get("/files/{id}/url")
def file_url(id: str, svc: Service, store: Storage) -> dict[str, Any]:
    file = svc.get(File, id)
    return {"url": store.url(file.storage_key), "expires_in": 3600}


@router.put("/shots/{id}/refs")
def refs(id: str, body: RefsBody, svc: Service) -> dict[str, Any]:
    return svc.bindings(id, body.base_version, body.asset_version_ids, True)


@router.put("/shots/{id}/lines")
def lines(id: str, body: LinesBody, svc: Service) -> dict[str, Any]:
    return svc.bindings(id, body.base_version, body.line_ids, False)
