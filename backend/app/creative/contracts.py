from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ModelInput(Strict):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["text", "image"]
    provider: Literal["mock", "openai_compatible"]
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=100)
    secret_env: str = Field(default="", pattern=r"^(MANJU_MODEL_[A-Z0-9_]{1,70})?$")
    allow_local: bool = False


class Request(Strict):
    model_config_id: str
    operation: Literal["script", "dialogue", "assets", "shots", "prompt", "image"]
    instruction: str = Field(min_length=1, max_length=5000)
    target_id: str | None = None
    actual_call: bool = False
    image_target: Literal["asset", "shot"] = "asset"


class DraftLine(Strict):
    text: str = Field(min_length=1, max_length=3000)
    line_type: Literal["dialogue", "narration", "action"] = "dialogue"


class DraftScene(Strict):
    title: str = Field(min_length=1, max_length=200)
    lines: list[DraftLine] = Field(min_length=1, max_length=50)


class ScriptResult(Strict):
    scenes: list[DraftScene] = Field(min_length=1, max_length=20)


class TextResult(Strict):
    text: str = Field(min_length=1, max_length=5000)


class DraftAsset(Strict):
    name: str = Field(min_length=1, max_length=100)
    asset_type: Literal["character", "location", "prop", "voice"]
    description: str = Field(max_length=3000)


class AssetsResult(Strict):
    assets: list[DraftAsset] = Field(min_length=1, max_length=30)


class DraftShot(Strict):
    action_desc: str = Field(min_length=1, max_length=3000)
    blocking_desc: str = Field(default="", max_length=3000)
    est_duration_ms: int = Field(ge=100, le=120000)


class ShotsResult(Strict):
    shots: list[DraftShot] = Field(min_length=1, max_length=30)


class ImageResult(Strict):
    prompt: str = Field(min_length=1, max_length=5000)
    mock: bool
    media_created: bool
    file_id: str | None = None


OUTPUTS: dict[str, type[Strict]] = {"script": ScriptResult, "dialogue": TextResult,
    "assets": AssetsResult, "shots": ShotsResult, "prompt": TextResult, "image": ImageResult}
