import base64
import binascii
import hashlib
import warnings
from io import BytesIO
from typing import Any
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.creative.network import request_bytes
from app.models import File
from app.providers.storage import StorageProvider
from app.services.content import ContentService, Problem

MAX_IMAGE = 20 * 1024 * 1024


def save_image(response: dict[str, Any], svc: ContentService, project_id: str,
               store: StorageProvider) -> File:
    try:
        data = response["data"]
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise ValueError()
        value = data[0]
        if bool(value.get("b64_json")) == bool(value.get("url")):
            raise ValueError()
        if value.get("b64_json"):
            encoded = value["b64_json"]
            if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_IMAGE + 2) // 3):
                raise ValueError()
            content = base64.b64decode(encoded, validate=True)
        else:
            if not isinstance(value["url"], str):
                raise ValueError()
            content, mime = request_bytes(value["url"], download=True, maximum=MAX_IMAGE)
            if mime not in {"image/png", "image/jpeg", "image/webp"}:
                raise ValueError()
        if not content or len(content) > MAX_IMAGE:
            raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if (image.format not in {"PNG", "JPEG", "WEBP"} or image.width > 8192 or
                    image.height > 8192 or image.width * image.height > 32_000_000 or
                    getattr(image, "n_frames", 1) != 1):
                    raise ValueError()
                width, height = image.size
                image.load()
                # Strip metadata and canonicalize the stored image; never persist SVG/HTML/polyglot payloads.
                clean = BytesIO()
                image.convert("RGB").save(clean, format="PNG")
                content = clean.getvalue()
                if len(content) > MAX_IMAGE:
                    raise ValueError()
    except (KeyError, ValueError, TypeError, binascii.Error, OSError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise Problem(422, "INVALID_IMAGE", "图片响应无效、尺寸过大或超过20MB；未创建候选。") from error
    key = f"{project_id}/creative/{uuid4()}.png"
    try:
        store.put(key, content, "image/png")
    except Exception as error:
        raise Problem(503, "STORAGE_ERROR", "图片保存失败，请检查存储服务。重新生成可能产生费用。") from error
    saved = File(project_id=project_id, storage_key=key, mime="image/png", size_bytes=len(content),
                 sha256=hashlib.sha256(content).hexdigest(), width=width, height=height)
    svc.db.add(saved)
    svc.db.flush()
    return saved
