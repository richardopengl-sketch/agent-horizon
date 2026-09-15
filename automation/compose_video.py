from __future__ import annotations

import json
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    VideoFileClip,
)

ROOT = Path(__file__).resolve().parents[1]

VIDEO_PATH = (
    ROOT /
    "artifacts" /
    "agent-horizon-demo-v2.webm"
)

TIMELINE_PATH = (
    ROOT /
    "artifacts" /
    "record_timeline_v2.json"
)

VOICE_DIR = (
    ROOT /
    "artifacts" /
    "voice"
)

OUTPUT_PATH = (
    ROOT /
    "artifacts" /
    "agent-horizon-demo-v2.mp4"
)

MIN_GAP = 0.20


def main():

    timeline = json.loads(
        TIMELINE_PATH.read_text(
            encoding="utf-8"
        )
    )

    video = VideoFileClip(
        str(VIDEO_PATH)
    )

    tracks = []

    previous_end = 0.0

    print("\nNarration timeline:")
    print("-" * 80)

    for cue in timeline["cues"]:

        cue_id = cue["id"]

        path = (
            VOICE_DIR /
            f"{cue_id}.mp3"
        )

        if not path.exists():
            raise RuntimeError(
                f"Missing narration: {path}"
            )

        clip = AudioFileClip(
            str(path)
        )

        requested_start = float(
            cue["start"]
        )

        # -------------------------------------------------
        # Safety check
        # -------------------------------------------------

        if requested_start < previous_end:

            overlap = (
                previous_end -
                requested_start
            )

            print(
                f"WARNING: {cue_id} would overlap "
                f"previous narration by "
                f"{overlap:.2f}s"
            )

        # Hard guarantee:
        # narration can never overlap.
        actual_start = max(
            requested_start,
            previous_end + MIN_GAP,
        )

        actual_end = (
            actual_start +
            clip.duration
        )

        print(
            f"{cue_id:22s} "
            f"requested={requested_start:6.2f}s  "
            f"actual={actual_start:6.2f}s  "
            f"duration={clip.duration:6.2f}s  "
            f"end={actual_end:6.2f}s"
        )

        tracks.append(
            clip.with_start(
                actual_start
            )
        )

        previous_end = actual_end

    print("-" * 80)

    if previous_end > video.duration:

        print(
            f"WARNING: narration ends at "
            f"{previous_end:.2f}s "
            f"but video ends at "
            f"{video.duration:.2f}s"
        )

    audio = CompositeAudioClip(
        tracks
    )

    final_video = video.with_audio(
        audio
    )

    final_video.write_videofile(
        str(OUTPUT_PATH),
        codec="libx264",
        audio_codec="aac",
        fps=30,
    )

    print("\nFinal video:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()