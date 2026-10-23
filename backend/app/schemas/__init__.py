from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    style_prompt: str = ""
    aspect_ratio: Literal["9:16", "16:9"] = "9:16"
    resolution: Literal["1080x1920", "1920x1080"] = "1080x1920"
    fps: int = Field(default=24, ge=1, le=60)
    production_type: Literal["dialogue_drama"] = "dialogue_drama"


class EpisodeInput(Input):
    title: str = Field(min_length=1, max_length=200)
    episode_no: int = Field(default=1, ge=1)
    target_duration_sec: int = Field(default=60, ge=1)


class SceneInput(Input):
    title: str = "新场次"
    summary: str = ""
    time_of_day: str = "白天"
    location_asset_id: str | None = None
    order_no: int = Field(default=0, ge=0)


class LineInput(Input):
    text: str = ""
    line_type: Literal["dialogue", "narration", "action"] = "dialogue"
    character_asset_id: str | None = None
    order_no: int = Field(default=0, ge=0)


class AssetInput(Input):
    name: str = Field(min_length=1, max_length=200)
    asset_type: Literal["character", "costume", "location", "prop", "voice"]
    parent_asset_id: str | None = None


class AssetVersionInput(Input):
    description: str = ""
    prompt: str = ""
    params_json: dict[str, Any] = Field(default_factory=dict)
    voice_config_json: dict[str, Any] = Field(default_factory=dict)


class ShotInput(Input):
    scene_id: str | None = None
    order_no: int = Field(default=0, ge=0)
    action_desc: str = ""
    shot_size: str = "中景"
    camera_angle: str = "平视"
    camera_movement: str = "固定"
    blocking_desc: str = ""
    est_duration_ms: int = Field(default=5000, ge=1, le=3600000)
    use_keyframe: bool = True
    dialogue_source: Literal["none", "dubbed", "native"] = "dubbed"
    sfx_note: str = ""
    prompt_text: str = ""
    prompt_overridden: bool = False
    params_json: dict[str, Any] = Field(default_factory=dict)


class Credentials(Input):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=128)


class VersionBody(Input):
    base_version: int = Field(ge=1)


class ConfirmBody(VersionBody):
    note: str = ""


class OrderBody(Input):
    items: dict[str, int]


class RefsBody(VersionBody):
    asset_version_ids: list[str]


class LinesBody(VersionBody):
    line_ids: list[str]


class CurrentBody(VersionBody):
    version_id: str
