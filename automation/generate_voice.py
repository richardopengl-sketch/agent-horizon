"""Generate segmented AI narration with edge-tts.

The segmented form lets the Playwright recorder align each visual scene with a
specific narration clip. edge-tts requires network access but no API key.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import edge_tts
from moviepy import AudioFileClip


async def synthesize(text: str, output: Path, voice: str, rate: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(str(output))


def audio_duration(path: Path) -> float:
    clip = AudioFileClip(str(path))
    try:
        return float(clip.duration)
    finally:
        clip.close()


async def generate_all(script: Path, output_dir: Path, manifest_path: Path, voice: str, rate: str) -> None:
    segments = json.loads(script.read_text(encoding="utf-8"))
    manifest = []

    for index, segment in enumerate(segments, start=1):
        segment_id = segment["id"]
        text = segment["text"].strip()
        output = output_dir / f"{index:02d}-{segment_id}.mp3"
        print(f"[{index}/{len(segments)}] TTS: {segment_id}")
        await synthesize(text, output, voice, rate)
        duration = audio_duration(output)
        manifest.append(
            {
                "id": segment_id,
                "text": text,
                "file": str(output.as_posix()),
                "duration": round(duration, 3),
            }
        )

    total_audio = sum(item["duration"] for item in manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "voice": voice,
                "rate": rate,
                "total_audio_duration": round(total_audio, 3),
                "segments": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Voice manifest: {manifest_path}")
    print(f"Narration audio only: {total_audio:.1f}s")
    if total_audio > 96:
        print("WARNING: narration is long. Consider --rate +12% or shortening text to preserve the 2-minute submission limit.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", default="automation/narration_segments.json")
    parser.add_argument("--output-dir", default="artifacts/narration")
    parser.add_argument("--manifest", default="artifacts/voice_manifest.json")
    parser.add_argument("--voice", default="en-US-AvaNeural")
    parser.add_argument("--rate", default="+8%")
    args = parser.parse_args()

    asyncio.run(
        generate_all(
            Path(args.script),
            Path(args.output_dir),
            Path(args.manifest),
            args.voice,
            args.rate,
        )
    )


if __name__ == "__main__":
    main()
