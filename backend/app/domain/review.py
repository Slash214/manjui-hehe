"""Pure propagation planner; no database writes, pointer changes or implicit adoption."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewTarget:
    kind: str
    id: str
    code: str
    source_id: str
    time: str


def propagate(
    change: str,
    source_id: str,
    time: str,
    *,
    shot_ids: tuple[str, ...] = (),
    dubbed_audio_ids: tuple[str, ...] = (),
    subtitle_ids: tuple[str, ...] = (),
    native_video_ids: tuple[str, ...] = (),
    adopted_ids: tuple[str, ...] = (),
    adjacent_ids: tuple[str, ...] = (),
    timeline_clip_ids: tuple[str, ...] = (),
    tts_audio_ids: tuple[str, ...] = (),
) -> tuple[ReviewTarget, ...]:
    groups: list[tuple[str, tuple[str, ...], str]] = []
    if change == "line_changed":
        groups = [
            ("audio", dubbed_audio_ids, change),
            ("subtitle", subtitle_ids, change),
            ("duration", shot_ids, change),
            ("video", native_video_ids, change),
        ]
    elif change == "shot_changed":
        groups = [("adopted", adopted_ids, change), ("shot", adjacent_ids, "adjacent_changed")]
    elif change == "asset_updated":
        groups = [("asset_update_offer", shot_ids, change)]  # User must choose update scope.
    elif change == "dialogue_source_changed":
        groups = [
            ("subtitle", subtitle_ids, change),
            ("duration", shot_ids, change),
            ("video", adopted_ids, change),
        ]
    elif change == "duration_changed":
        groups = [("timeline_clip", timeline_clip_ids, change)]
    elif change == "voice_changed":
        groups = [("audio", tts_audio_ids, change)]
    else:
        raise ValueError(change)
    return tuple(
        dict.fromkeys(
            ReviewTarget(kind, id, code, source_id, time) for kind, ids, code in groups for id in ids
        )
    )
