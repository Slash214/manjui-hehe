import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from app.providers.generation.base import GenerationError, Output, Pulse, ReadFile


class MockGenerationProvider:
    def generate(self, snapshot: dict[str, Any], pulse: Pulse, read: ReadFile) -> Output:
        params = snapshot["params"]
        until = time.monotonic() + float(params.get("mock_delay_sec", 0))
        while time.monotonic() < until:
            pulse(None, None)
            time.sleep(min(0.5, max(0, until - time.monotonic())))
        pulse(None, None)
        if params.get("mock_error"):
            raise GenerationError(str(params["mock_error"]))
        video = snapshot["workflow"]["kind"] == "video"
        width, height = int(params.get("width", 320)), int(params.get("height", 568))
        fps = int(params.get("fps", 24))
        duration = int(params.get("frame_count", 24)) / fps
        with tempfile.TemporaryDirectory(prefix="manju-mock-") as directory:
            target = Path(directory) / ("mock.mp4" if video else "mock.png")
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                       f"color=c=0x202020:s={width}x{height}:r={fps}", "-vf",
                       "drawtext=text='MOCK - TEST OUTPUT':fontcolor=white:fontsize=20:x=(w-tw)/2:y=(h-th)/2"]
            command += (["-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p"] if video
                        else ["-frames:v", "1"])
            command += ["-threads", "1", str(target)]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=60)
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(target)],
                                       check=True, capture_output=True, timeout=10)
                info = json.loads(probe.stdout)["streams"][0]
            except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
                raise GenerationError("COMFY_EXECUTION") from exc
            pulse(None, None)
            return Output(target.read_bytes(), "video/mp4" if video else "image/png", info["width"],
                          info["height"], round(duration * 1000) if video else None)

    def recover(self, snapshot: dict[str, Any], prompt_id: str | None, read: ReadFile) -> Output | None:
        return None
