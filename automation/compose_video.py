"""Place segmented narration on the Playwright cue timeline and export MP4."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip


MAX_SUBMISSION_SECONDS = 120.0
SAFETY_TARGET_SECONDS = 116.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="artifacts/agent-horizon-demo.webm")
    parser.add_argument("--voice-manifest", default="artifacts/voice_manifest.json")
    parser.add_argument("--timeline", default="artifacts/record_timeline.json")
    parser.add_argument("--output", default="artifacts/agent-horizon-final.mp4")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    voice_manifest = json.loads(Path(args.voice_manifest).read_text(encoding="utf-8"))
    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    voice_by_id = {item["id"]: item for item in voice_manifest["segments"]}

    video = VideoFileClip(args.video)
    audio_clips = []
    last_audio_end = 0.0
    try:
        for cue in timeline["cues"]:
            cue_id = cue["id"]
            voice = voice_by_id[cue_id]
            clip = AudioFileClip(voice["file"]).with_start(float(cue["start"]))
            audio_clips.append(clip)
            last_audio_end = max(last_audio_end, float(cue["start"]) + float(voice["duration"]))

        if last_audio_end > SAFETY_TARGET_SECONDS:
            print(
                f"WARNING: narrated timeline ends at {last_audio_end:.1f}s. "
                f"Target is <= {SAFETY_TARGET_SECONDS:.0f}s for submission safety."
            )
        if last_audio_end >= MAX_SUBMISSION_SECONDS:
            raise SystemExit(
                f"Narration reaches {last_audio_end:.1f}s, exceeding the {MAX_SUBMISSION_SECONDS:.0f}s submission limit. "
                "Regenerate narration at a faster rate, for example `python automation/generate_voice.py --rate +12%`."
            )

        final_duration = min(video.duration, last_audio_end + 1.0)
        if final_duration <= last_audio_end:
            raise SystemExit(
                f"Recorded video ({video.duration:.1f}s) is shorter than narration ({last_audio_end:.1f}s)."
            )

        mixed_audio = CompositeAudioClip(audio_clips)
        final = video.subclipped(0, final_duration).with_audio(mixed_audio)
        try:
            final.write_videofile(
                str(output),
                codec="libx264",
                audio_codec="aac",
                fps=30,
                preset="medium",
                ffmpeg_params=["-crf", "20", "-movflags", "+faststart"],
            )
        finally:
            final.close()
            mixed_audio.close()
    finally:
        for clip in audio_clips:
            clip.close()
        video.close()

    print(f"Final video (WITH narration): {output}")
    print(f"Final duration: {final_duration:.1f}s")


if __name__ == "__main__":
    main()
