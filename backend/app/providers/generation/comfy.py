import io
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from PIL import Image
from websockets.sync.client import connect

from app.domain.workflow_mapping import fill_workflow
from app.providers.generation.base import GenerationError, Output, Pulse, ReadFile


class ComfyGenerationProvider:
    def __init__(self) -> None:
        self.url = os.getenv("COMFYUI_BASE_URL", "").rstrip("/")
        parsed = urlsplit(self.url)
        if os.getenv("COMFYUI_ENABLED", "false").lower() != "true" or parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise GenerationError("COMFY_UNREACHABLE")

    def generate(self, snapshot: dict[str, Any], pulse: Pulse, read: ReadFile) -> Output:
        workflow = snapshot["workflow"]
        timeout = int(os.getenv("COMFY_TIMEOUT_KEYFRAME_SEC" if workflow["kind"] == "keyframe" else "COMFY_TIMEOUT_VIDEO_SEC", "300" if workflow["kind"] == "keyframe" else "1200"))
        values = {**snapshot["params"], "prompt": snapshot["prompt"]}
        client_id = str(uuid4())
        try:
            with httpx.Client(base_url=self.url, timeout=30, trust_env=False, follow_redirects=False) as client:
                for index, ref in enumerate(snapshot["references"], 1):
                    values[f"ref_image_{index}"] = self.upload(client, ref, read)
                if snapshot["first_frame"]:
                    values["first_frame"] = self.upload(client, snapshot["first_frame"], read)
                try:
                    graph = fill_workflow(workflow["comfy_json"], workflow["param_map_json"], values)
                except ValueError as exc:
                    raise GenerationError("COMFY_VALIDATION") from exc
                ws_url = self.url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
                with connect(f"{ws_url}/ws?clientId={client_id}", open_timeout=10, proxy=None, max_size=8 * 1024 * 1024) as ws:
                    response = client.post("/prompt", json={"prompt": graph, "client_id": client_id})
                    if response.status_code == 400:
                        raise GenerationError("COMFY_VALIDATION")
                    response.raise_for_status()
                    prompt_id = str(response.json()["prompt_id"])
                    pulse(prompt_id, None)
                    # Unknown/custom samplers remain indeterminate, including multi-sampler graphs.
                    samplers = [n for n in graph.values() if "sampler" in str(n.get("class_type", "")).lower()]
                    trusted = len(samplers) == 1 and samplers[0].get("class_type") in {"KSampler", "KSamplerAdvanced"}
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        pulse(prompt_id, None)
                        try:
                            raw = ws.recv(timeout=1)
                        except TimeoutError:
                            continue
                        if not isinstance(raw, str):
                            continue
                        event = json.loads(raw)
                        data = event.get("data", {})
                        if data.get("prompt_id") != prompt_id:
                            continue
                        if event["type"] in ("execution_error", "execution_interrupted"):
                            raise GenerationError("COMFY_EXECUTION")
                        if event["type"] == "progress" and trusted and data.get("max", 0) > 0:
                            pulse(prompt_id, min(1, max(0, data["value"] / data["max"])))
                        if (event["type"] == "executing" and data.get("node") is None) or event["type"] == "execution_success":
                            result = self.history(client, snapshot, prompt_id)
                            if result is None:
                                raise GenerationError("OUTPUT_MISSING")
                            return result
                    raise GenerationError("TIMEOUT")
        except httpx.TimeoutException as exc:
            raise GenerationError("TIMEOUT") from exc
        except (httpx.HTTPError, OSError) as exc:
            raise GenerationError("COMFY_UNREACHABLE") from exc
        except (KeyError, ValueError, TypeError) as exc:
            raise GenerationError("COMFY_EXECUTION") from exc

    @staticmethod
    def upload(client: httpx.Client, ref: dict[str, Any], read: ReadFile) -> str:
        response = client.post("/upload/image", files={"image": (f"{uuid4()}.png", read(ref["storage_key"]), ref["mime"])})
        response.raise_for_status()
        result = response.json()
        return str(result.get("subfolder", "")).strip("/") + ("/" if result.get("subfolder") else "") + str(result["name"])

    def recover(self, snapshot: dict[str, Any], prompt_id: str | None, read: ReadFile) -> Output | None:
        if not prompt_id:
            return None
        try:
            with httpx.Client(base_url=self.url, timeout=30, trust_env=False, follow_redirects=False) as client:
                return self.history(client, snapshot, prompt_id)
        except Exception as exc:
            raise GenerationError("WORKER_LOST") from exc

    @staticmethod
    def history(client: httpx.Client, snapshot: dict[str, Any], prompt_id: str) -> Output | None:
        response = client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        record = response.json().get(prompt_id)
        if not record:
            return None
        video = snapshot["workflow"]["kind"] == "video"
        for node in record.get("outputs", {}).values():
            for item in node.get("videos", []) + node.get("gifs", []) + node.get("images", []):
                suffix = Path(item.get("filename", "")).suffix.lower()
                if (video and suffix != ".mp4") or (not video and suffix not in {".png", ".jpg", ".jpeg", ".webp"}):
                    continue
                content = bytearray()
                with client.stream("GET", "/view", params={k: item.get(k, "output" if k == "type" else "") for k in ("filename", "subfolder", "type")}) as downloaded:
                    downloaded.raise_for_status()
                    for chunk in downloaded.iter_bytes():
                        content.extend(chunk)
                        if len(content) > (256 if video else 20) * 1024 * 1024:
                            raise GenerationError("OUTPUT_MISSING")
                if not video:
                    with Image.open(io.BytesIO(content)) as image:
                        if image.width * image.height > 32_000_000:
                            raise GenerationError("OUTPUT_MISSING")
                        image.load()
                        clean = io.BytesIO()
                        image.convert("RGB").save(clean, format="PNG")
                        return Output(clean.getvalue(), "image/png", image.width, image.height, None)
                with tempfile.TemporaryDirectory(prefix="manju-comfy-") as directory:
                    path = Path(directory) / "output.mp4"
                    path.write_bytes(content)
                    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], check=True, capture_output=True, timeout=20)
                    info = json.loads(probe.stdout)
                    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
                    return Output(bytes(content), "video/mp4", stream["width"], stream["height"], round(float(info["format"]["duration"]) * 1000))
        return None
