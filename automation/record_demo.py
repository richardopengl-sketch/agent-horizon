from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from pathlib import Path

from moviepy import AudioFileClip
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

VOICE_DIR = ROOT / "artifacts" / "voice"
TIMELINE_PATH = ROOT / "artifacts" / "record_timeline_v2.json"

GAP_SECONDS = 0.40


# ---------------------------------------------------------
# Audio timing
# ---------------------------------------------------------

def get_audio_duration(cue_id: str) -> float:
    path = VOICE_DIR / f"{cue_id}.mp3"

    if not path.exists():
        raise RuntimeError(f"Missing narration file: {path}")

    clip = AudioFileClip(str(path))

    try:
        return float(clip.duration)
    finally:
        clip.close()


def build_audio_durations() -> dict[str, float]:
    cue_ids = [
        "opening",
        "semantic_setup",
        "semantic_run",
        "semantic_final",
        "difference",
        "consequence_setup",
        "consequence_run",
        "closing",
    ]

    durations = {}

    print("\nNarration durations:")

    for cue_id in cue_ids:
        duration = get_audio_duration(cue_id)
        durations[cue_id] = duration
        print(f"  {cue_id:22s} {duration:6.2f}s")

    print()

    return durations


# ---------------------------------------------------------
# Streamlit / camera helpers
# ---------------------------------------------------------

def prepare_page(page):
    """
    Remove Streamlit chrome and make the page suitable for recording.
    """

    page.add_style_tag(
        content="""
        header[data-testid="stHeader"] {
            display: none !important;
        }

        #MainMenu {
            display: none !important;
        }

        footer {
            display: none !important;
        }

        html {
            scroll-behavior: smooth !important;
        }

        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container {
            padding-top: 1rem !important;
        }
        """
    )

    page.wait_for_timeout(500)


def camera_to_text(
    page,
    text: str,
    *,
    timeout: int = 20000,
    hold_ms: int = 900,
):
    """
    Scroll the REAL scrollable ancestor containing the target into view.

    scrollIntoView() is intentional here:
    unlike window.scrollTo(), it works when Streamlit owns the scroll container.
    """

    locator = page.get_by_text(
        text,
        exact=False,
    ).last

    locator.wait_for(
        state="visible",
        timeout=timeout,
    )

    locator.evaluate(
        """
        el => {
            el.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
                inline: 'nearest'
            });
        }
        """
    )

    page.wait_for_timeout(hold_ms)

    box = locator.bounding_box()

    if box:
        print(
            f"CAMERA -> {text!r} "
            f"(viewport y={box['y']:.0f})"
        )
    else:
        print(f"CAMERA -> {text!r}")


def camera_top(page, hold_ms: int = 900):
    """
    Scroll the Streamlit main container back to the top.
    """

    page.evaluate(
        """
        () => {
            const main =
                document.querySelector('[data-testid="stMain"]') ||
                document.querySelector('section.main');

            if (main) {
                main.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            }

            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        }
        """
    )

    page.wait_for_timeout(hold_ms)

    print("CAMERA -> TOP")


def hold(page, seconds: float):
    page.wait_for_timeout(
        max(0, int(seconds * 1000))
    )


# ---------------------------------------------------------
# Timeline
# ---------------------------------------------------------

def add_cue(
    cues: list,
    cue_id: str,
    recording_started: float,
    duration: float,
):
    start = time.monotonic() - recording_started

    cue = {
        "id": cue_id,
        "start": round(start, 3),
        "duration": round(duration, 3),
    }

    cues.append(cue)

    print(
        f"\nCUE {cue_id}: "
        f"start={start:.2f}s "
        f"duration={duration:.2f}s"
    )

    return start


def finish_cue(
    page,
    cue_started: float,
    duration: float,
):
    """
    Ensure the visual scene lasts at least as long as narration.
    """

    elapsed = time.monotonic() - cue_started

    remaining = duration + GAP_SECONDS - elapsed

    if remaining > 0:
        hold(page, remaining)


# ---------------------------------------------------------
# Semantic scenario
# ---------------------------------------------------------

def run_semantic(
    page,
    duration: float,
):
    started = time.monotonic()

    page.get_by_role(
        "button",
        name=re.compile(r"Run Semantic Delta"),
    ).click()

    # Show noise filtering.
    try:
        camera_to_text(
            page,
            "LOW-CONTRIBUTION EVENT",
            timeout=15000,
        )
        hold(page, 0.8)
    except Exception as exc:
        print("Noise camera skipped:", exc)

    # Main semantic-delta hero moment.
    try:
        camera_to_text(
            page,
            "NEW KNOWLEDGE",
            timeout=20000,
        )
        hold(page, 2.0)
    except Exception as exc:
        print("Semantic hero camera skipped:", exc)

    # External boundary.
    try:
        camera_to_text(
            page,
            "EXTERNAL TRUST BOUNDARY",
            timeout=25000,
        )
        hold(page, 2.0)
    except Exception as exc:
        print("Boundary camera skipped:", exc)

    page.get_by_text(
        "Scenario complete",
        exact=False,
    ).last.wait_for(
        timeout=45000
    )

    finish_cue(
        page,
        started,
        duration,
    )


def semantic_final(
    page,
    duration: float,
):
    started = time.monotonic()

    camera_to_text(
        page,
        "FINAL HORIZON ASSESSMENT",
        timeout=15000,
    )

    hold(page, 2.5)

    camera_to_text(
        page,
        "Evidence that actually contributed",
        timeout=15000,
    )

    hold(page, 2.5)

    finish_cue(
        page,
        started,
        duration,
    )


def semantic_difference(
    page,
    duration: float,
):
    started = time.monotonic()

    try:
        camera_to_text(
            page,
            "Smokescreen/noise filtered",
            timeout=10000,
        )
        hold(page, 1.5)
    except Exception as exc:
        print("Noise evidence camera skipped:", exc)

    camera_to_text(
        page,
        "Why this layer exists",
        timeout=15000,
    )

    hold(page, 3.0)

    finish_cue(
        page,
        started,
        duration,
    )


# ---------------------------------------------------------
# Consequence scenario
# ---------------------------------------------------------

def run_consequence(
    page,
    duration: float,
):
    started = time.monotonic()

    page.get_by_role(
        "button",
        name=re.compile(r"Run Consequence Delta"),
    ).click()

    try:
        camera_to_text(
            page,
            "NEW CAPABILITY STATE",
            timeout=20000,
        )

        hold(page, 2.5)

    except Exception as exc:
        print("Consequence hero camera skipped:", exc)

    page.get_by_text(
        "Scenario complete",
        exact=False,
    ).last.wait_for(
        timeout=45000
    )

    camera_to_text(
        page,
        "FINAL HORIZON ASSESSMENT",
        timeout=15000,
    )

    hold(page, 2.5)

    camera_to_text(
        page,
        "No sensitive content was involved",
        timeout=15000,
    )

    hold(page, 2.0)

    finish_cue(
        page,
        started,
        duration,
    )


# ---------------------------------------------------------
# Main recording
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--url",
        default="http://localhost:8501",
    )

    parser.add_argument(
        "--output",
        default="artifacts/agent-horizon-demo-v2.webm",
    )

    parser.add_argument(
        "--headed",
        action="store_true",
    )

    args = parser.parse_args()

    durations = build_audio_durations()

    output = (ROOT / args.output).resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_dir = (
        output.parent /
        "playwright-v2"
    )

    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    temp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    cues = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=not args.headed
        )

        context = browser.new_context(
            viewport={
                "width": VIDEO_WIDTH,
                "height": VIDEO_HEIGHT,
            },
            record_video_dir=str(temp_dir),
            record_video_size={
                "width": VIDEO_WIDTH,
                "height": VIDEO_HEIGHT,
            },
            device_scale_factor=1,
        )

        page = context.new_page()

        video = page.video

        page.goto(
            args.url,
            wait_until="networkidle",
            timeout=45000,
        )

        prepare_page(page)

        camera_top(page)

        recording_started = time.monotonic()

        # -------------------------------------------------
        # Opening
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "opening",
            recording_started,
            durations["opening"],
        )

        finish_cue(
            page,
            cue_started,
            durations["opening"],
        )

        # -------------------------------------------------
        # Semantic setup
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "semantic_setup",
            recording_started,
            durations["semantic_setup"],
        )

        finish_cue(
            page,
            cue_started,
            durations["semantic_setup"],
        )

        # -------------------------------------------------
        # Semantic run
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "semantic_run",
            recording_started,
            durations["semantic_run"],
        )

        run_semantic(
            page,
            durations["semantic_run"],
        )

        # -------------------------------------------------
        # Semantic final assessment
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "semantic_final",
            recording_started,
            durations["semantic_final"],
        )

        semantic_final(
            page,
            durations["semantic_final"],
        )

        # -------------------------------------------------
        # Differentiation
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "difference",
            recording_started,
            durations["difference"],
        )

        semantic_difference(
            page,
            durations["difference"],
        )

        # -------------------------------------------------
        # Consequence setup
        # -------------------------------------------------

        camera_top(
            page,
            hold_ms=1100,
        )

        page.get_by_text(
            "Consequence Delta",
            exact=True,
        ).first.click()

        page.wait_for_timeout(700)

        camera_top(
            page,
            hold_ms=600,
        )

        cue_started = add_cue(
            cues,
            "consequence_setup",
            recording_started,
            durations["consequence_setup"],
        )

        finish_cue(
            page,
            cue_started,
            durations["consequence_setup"],
        )

        # -------------------------------------------------
        # Consequence run
        # -------------------------------------------------

        cue_started = add_cue(
            cues,
            "consequence_run",
            recording_started,
            durations["consequence_run"],
        )

        run_consequence(
            page,
            durations["consequence_run"],
        )

        # -------------------------------------------------
        # Closing
        # -------------------------------------------------

        camera_top(
            page,
            hold_ms=1100,
        )

        cue_started = add_cue(
            cues,
            "closing",
            recording_started,
            durations["closing"],
        )

        finish_cue(
            page,
            cue_started,
            durations["closing"],
        )

        # End padding.
        hold(page, 1.0)

        page.close()

        context.close()

        if video is None:
            raise RuntimeError(
                "Playwright did not create video."
            )

        recorded_path = Path(
            video.path()
        )

        browser.close()

    shutil.copy2(
        recorded_path,
        output,
    )

    TIMELINE_PATH.write_text(
        json.dumps(
            {
                "gap_seconds": GAP_SECONDS,
                "cues": cues,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n===================================")
    print("Recording complete")
    print("===================================")

    print("Video:", output)
    print("Timeline:", TIMELINE_PATH)


if __name__ == "__main__":
    main()