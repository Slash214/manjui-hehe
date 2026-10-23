import unittest

from app.domain.prompt import build_prompt
from app.domain.review import propagate


class ReviewTests(unittest.TestCase):
    def test_line_scoped_and_native(self) -> None:
        result = propagate(
            "line_changed",
            "line1",
            "now",
            shot_ids=("shot1",),
            dubbed_audio_ids=("audio1",),
            subtitle_ids=("sub1",),
            native_video_ids=("video1",),
        )
        self.assertEqual(
            {(x.kind, x.id) for x in result},
            {("duration", "shot1"), ("audio", "audio1"), ("subtitle", "sub1"), ("video", "video1")},
        )
        self.assertTrue(all(x.code == "line_changed" and x.source_id == "line1" for x in result))

    def test_shot_and_adjacency(self) -> None:
        result = propagate(
            "shot_changed", "s2", "now", adopted_ids=("keyframe", "video"), adjacent_ids=("s1", "s3")
        )
        self.assertEqual(
            [x.code for x in result], ["shot_changed", "shot_changed", "adjacent_changed", "adjacent_changed"]
        )

    def test_asset_update_is_only_offer(self) -> None:
        result = propagate("asset_updated", "asset1", "now", shot_ids=("s1",))
        self.assertEqual(result[0].kind, "asset_update_offer")

    def test_dialogue_source(self) -> None:
        result = propagate(
            "dialogue_source_changed",
            "s1",
            "now",
            shot_ids=("s1",),
            subtitle_ids=("sub1",),
            adopted_ids=("video1",),
        )
        self.assertEqual({x.kind for x in result}, {"duration", "subtitle", "video"})

    def test_duration_only_timeline(self) -> None:
        result = propagate(
            "duration_changed", "s1", "now", timeline_clip_ids=("clip1",), subtitle_ids=("unrelated",)
        )
        self.assertEqual([(x.kind, x.id) for x in result], [("timeline_clip", "clip1")])

    def test_voice_only_matching_tts(self) -> None:
        result = propagate(
            "voice_changed", "voice1", "now", tts_audio_ids=("tts1",), dubbed_audio_ids=("upload1",)
        )
        self.assertEqual([x.id for x in result], ["tts1"])

    def test_dedup_no_targets_and_unknown(self) -> None:
        self.assertEqual(propagate("line_changed", "x", "now"), ())
        self.assertEqual(len(propagate("voice_changed", "x", "now", tts_audio_ids=("a", "a"))), 1)
        with self.assertRaises(ValueError):
            propagate("invalid", "x", "now")

    def test_prompt_order(self) -> None:
        self.assertEqual(
            build_prompt("画风", ["角色", "地点"], "动作", "中景", "平视", "站位"),
            "画风\n角色\n地点\n动作\n中景\n平视\n站位",
        )


if __name__ == "__main__":
    unittest.main()
