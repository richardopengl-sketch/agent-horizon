"""Record the complete two-scenario Agent Horizon demo with Playwright.

v0.8 camera choreography:
- records at 1920x1080
- follows the live hero transitions while each scenario runs
- uses deterministic smooth pans instead of generic scrollIntoView
- deliberately walks the reviewer through final assessment -> evidence -> comparison
- reaches the real page bottom before leaving each scenario, so no conclusion is
  stranded below the viewport
- keeps cue timestamps compatible with compose_video.py

The raw Playwright capture is intentionally silent. compose_video.py overlays the
segmented TTS clips using record_timeline.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


DEFAULT_DURATION = 10.0
GAP_SECONDS = 0.55
VIDEO_WIDTH = 2560
VIDEO_HEIGHT = 1440


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"Missing {path}. Run `python automation/generate_voice.py` first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def duration_for(manifest: dict, cue_id: str) -> float:
    for segment in manifest["segments"]:
        if segment["id"] == cue_id:
            return float(segment["duration"])
    return DEFAULT_DURATION


def prepare_recording_layout(page: Page) -> None:
    """Make Streamlit fill the recorded viewport and remove recording chrome."""
    page.add_style_tag(
        content="""
        html { scroll-behavior: auto !important; }
        header[data-testid='stHeader'] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }

        html, body, [data-testid='stAppViewContainer'], [data-testid='stMain'],
        section.main, main {
            width: 100% !important;
            max-width: none !important;
            min-width: 0 !important;
        }

        [data-testid='stMainBlockContainer'], .stMainBlockContainer, .block-container {
            box-sizing: border-box !important;
            width: calc(100vw - 48px) !important;
            min-width: calc(100vw - 48px) !important;
            max-width: calc(100vw - 48px) !important;
            padding-top: 1.0rem !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            margin-left: 24px !important;
            margin-right: 24px !important;
        }

        [data-testid='stHorizontalBlock'] {
            width: 100% !important;
            max-width: none !important;
        }
        """
    )
    page.evaluate("document.documentElement.style.zoom = '1.0'")


def hold(page: Page, seconds: float) -> None:
    page.wait_for_timeout(max(0, int(seconds * 1000)))


def smooth_scroll_y(page: Page, target_y: float, duration_ms: int = 850) -> None:
    """Deterministically animate the camera to an absolute document Y position."""
    page.evaluate(
        """([targetY, duration]) => new Promise(resolve => {
            const startY = window.scrollY;
            const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
            const endY = Math.max(0, Math.min(targetY, maxY));
            const delta = endY - startY;
            if (Math.abs(delta) < 2) { window.scrollTo(0, endY); resolve(); return; }
            const start = performance.now();
            const ease = t => t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
            function frame(now) {
                const p = Math.min(1, (now - start) / duration);
                window.scrollTo(0, startY + delta * ease(p));
                if (p < 1) requestAnimationFrame(frame); else resolve();
            }
            requestAnimationFrame(frame);
        })""",
        [float(target_y), int(duration_ms)],
    )


def smooth_top(page: Page, duration_ms: int = 900) -> None:
    smooth_scroll_y(page, 0, duration_ms=duration_ms)
    page.wait_for_timeout(250)


def smooth_bottom(page: Page, duration_ms: int = 1000, settle_ms: int = 350) -> None:
    target = page.evaluate(
        "Math.max(0, document.documentElement.scrollHeight - window.innerHeight)"
    )
    smooth_scroll_y(page, float(target), duration_ms=duration_ms)
    page.wait_for_timeout(settle_ms)
    print("Camera -> PAGE BOTTOM")


def camera_to_locator(
    page: Page,
    locator,
    *,
    anchor: float = 0.20,
    duration_ms: int = 850,
    settle_ms: int = 300,
) -> None:
    """Place an element at a stable vertical anchor instead of blindly centering it.

    anchor=0.20 means the element's top lands around 20% down the viewport. That
    leaves room below for the complete card and the next piece of context.
    """
    box = locator.bounding_box()
    if box is None:
        locator.scroll_into_view_if_needed()
        page.wait_for_timeout(settle_ms)
        return
    current_y = float(page.evaluate("window.scrollY"))
    viewport_h = float(page.evaluate("window.innerHeight"))
    target_y = current_y + float(box["y"]) - viewport_h * anchor
    smooth_scroll_y(page, target_y, duration_ms=duration_ms)
    page.wait_for_timeout(settle_ms)


def focus_text(
    page: Page,
    text: str,
    *,
    timeout_ms: int = 15000,
    anchor: float = 0.20,
    duration_ms: int = 850,
    settle_ms: int = 300,
) -> bool:
    """Wait for a visual milestone and move the camera to it when it appears."""
    locator = page.get_by_text(text, exact=False).last
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        camera_to_locator(
            page,
            locator,
            anchor=anchor,
            duration_ms=duration_ms,
            settle_ms=settle_ms,
        )
        print(f"Camera -> {text}")
        return True
    except PlaywrightTimeoutError:
        print(f"Camera milestone not observed (continuing): {text}")
        return False


def finish_narration_hold(started: float, narration_seconds: float, page: Page) -> None:
    elapsed = time.monotonic() - started
    remaining = narration_seconds + GAP_SECONDS - elapsed
    if remaining > 0:
        hold(page, remaining)


def split_hold(page: Page, total_seconds: float, weights: list[float], index: int) -> None:
    """Use a portion of a narration cue as a stable reading pause."""
    if total_seconds <= 0:
        return
    weight_sum = sum(weights)
    hold(page, total_seconds * weights[index] / weight_sum)


def run_semantic_with_camera(page: Page, narration_seconds: float) -> None:
    """Run Semantic Delta with a deliberate camera narrative."""
    started = time.monotonic()
    page.get_by_role("button", name=re.compile(r"Run Semantic Delta")).click()

    # 1) Show that irrelevant events are present but not treated as evidence.
    if focus_text(
        page,
        "LOW-CONTRIBUTION EVENT",
        timeout_ms=12000,
        anchor=0.18,
        duration_ms=650,
    ):
        hold(page, 0.9)

    # 2) Hero moment. Keep the full Before -> After card comfortably in frame.
    if focus_text(
        page,
        "NEW KNOWLEDGE EMERGED",
        timeout_ms=18000,
        anchor=0.12,
        duration_ms=800,
    ):
        hold(page, 2.2)

    # 3) Follow the action that crosses the enterprise trust boundary.
    if focus_text(
        page,
        "EXTERNAL TRUST BOUNDARY",
        timeout_ms=22000,
        anchor=0.12,
        duration_ms=800,
    ):
        hold(page, 1.8)

    page.get_by_text("Scenario complete", exact=False).last.wait_for(timeout=45000)
    finish_narration_hold(started, narration_seconds, page)


def semantic_final_camera(page: Page, narration_seconds: float) -> None:
    """Walk final semantic result downward rather than freezing on one card."""
    started = time.monotonic()

    # Most important policy conclusion first.
    focus_text(
        page,
        "FINAL HORIZON ASSESSMENT",
        timeout_ms=10000,
        anchor=0.10,
        duration_ms=750,
    )
    hold(page, min(4.5, narration_seconds * 0.50))

    # Then reveal what evidence actually survived the reducer.
    focus_text(
        page,
        "Evidence that actually contributed",
        timeout_ms=8000,
        anchor=0.08,
        duration_ms=750,
    )

    finish_narration_hold(started, narration_seconds, page)


def semantic_difference_camera(page: Page, narration_seconds: float) -> None:
    """Show FP resistance, comparison, then deliberately land at the page bottom."""
    started = time.monotonic()

    # The user should visibly see that the smokescreen was discarded.
    if focus_text(
        page,
        "Smokescreen/noise filtered by contribution",
        timeout_ms=8000,
        anchor=0.08,
        duration_ms=700,
    ):
        hold(page, min(2.4, narration_seconds * 0.24))

    # Main product differentiation.
    focus_text(
        page,
        "Why this is different",
        timeout_ms=8000,
        anchor=0.08,
        duration_ms=800,
    )
    hold(page, min(4.5, narration_seconds * 0.50))

    # Finish the scene at the true bottom so the viewer knows the conclusion was
    # fully traversed, not clipped below the viewport.
    smooth_bottom(page, duration_ms=850, settle_ms=250)
    finish_narration_hold(started, narration_seconds, page)


def run_consequence_with_camera(page: Page, narration_seconds: float) -> None:
    """Run Consequence Delta and traverse transition -> decision -> bottom note."""
    started = time.monotonic()
    page.get_by_role("button", name=re.compile(r"Run Consequence Delta")).click()

    # Hero moment: authorized operation changes reversibility.
    if focus_text(
        page,
        "STATE TRANSITION",
        timeout_ms=18000,
        anchor=0.10,
        duration_ms=800,
    ):
        hold(page, min(4.2, narration_seconds * 0.38))

    page.get_by_text("Scenario complete", exact=False).last.wait_for(timeout=45000)

    # Show the policy decision as a distinct second shot.
    if focus_text(
        page,
        "FINAL HORIZON ASSESSMENT",
        timeout_ms=8000,
        anchor=0.08,
        duration_ms=800,
    ):
        hold(page, min(4.0, narration_seconds * 0.34))

    # Finish on the explicit statement that this was not content classification.
    focus_text(
        page,
        "No sensitive content was involved",
        timeout_ms=8000,
        anchor=0.08,
        duration_ms=750,
    )
    smooth_bottom(page, duration_ms=750, settle_ms=250)

    finish_narration_hold(started, narration_seconds, page)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--output", default="artifacts/agent-horizon-demo.webm")
    parser.add_argument("--voice-manifest", default="artifacts/voice_manifest.json")
    parser.add_argument("--timeline", default="artifacts/record_timeline.json")
    parser.add_argument("--headed", action="store_true", help="Show the automated browser while recording.")
    args = parser.parse_args()

    voice_manifest = load_manifest(Path(args.voice_manifest))
    output = Path(args.output).resolve()
    timeline_path = Path(args.timeline).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output.parent / "playwright-video"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    cues: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            viewport={"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT},
            record_video_dir=str(temp_dir),
            record_video_size={"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT},
            device_scale_factor=1,
        )

        record_start = time.monotonic()
        page = context.new_page()
        video = page.video
        page.goto(args.url, wait_until="networkidle", timeout=45000)
        prepare_recording_layout(page)
        smooth_top(page)
        metrics = page.evaluate("""() => {
            const main = document.querySelector('[data-testid="stMainBlockContainer"]');
            return {
                viewport: [window.innerWidth, window.innerHeight],
                mainWidth: main ? Math.round(main.getBoundingClientRect().width) : null,
                bodyWidth: Math.round(document.body.getBoundingClientRect().width),
            };
        }""")
        print(
            f"Recording layout: viewport={metrics['viewport']}, "
            f"mainWidth={metrics['mainWidth']}, bodyWidth={metrics['bodyWidth']}"
        )

        def cue(cue_id: str) -> float:
            start = time.monotonic() - record_start
            duration = duration_for(voice_manifest, cue_id)
            cues.append({"id": cue_id, "start": round(start, 3), "duration": duration})
            print(f"Cue {cue_id}: {start:.1f}s, audio {duration:.1f}s")
            return duration

        # 1. Opening thesis.
        d = cue("opening")
        hold(page, d + GAP_SECONDS)

        # 2. Semantic scenario overview. Keep the scenario table visible.
        page.get_by_text("Semantic Delta", exact=True).first.click()
        smooth_top(page)
        d = cue("semantic_setup")
        hold(page, d + GAP_SECONDS)

        # 3. Run hero scenario; camera follows live milestones.
        d = cue("semantic_run")
        run_semantic_with_camera(page, d)

        # 4. Final semantic decision, then pan into supporting evidence.
        d = cue("semantic_final")
        semantic_final_camera(page, d)

        # 5. Noise resilience + isolated-check comparison + true page bottom.
        d = cue("semantic_difference")
        semantic_difference_camera(page, d)

        # 6. Reset cleanly for consequence overview.
        smooth_top(page, duration_ms=950)
        page.get_by_text("Consequence Delta", exact=True).first.click()
        page.wait_for_timeout(700)
        smooth_top(page, duration_ms=500)
        d = cue("consequence_setup")
        hold(page, d + GAP_SECONDS)

        # 7. Run second scenario and fully traverse its conclusion.
        d = cue("consequence_run")
        run_consequence_with_camera(page, d)

        # 8. Closing thesis. Return to top only after the consequence bottom was shown.
        smooth_top(page, duration_ms=1000)
        d = cue("closing")
        hold(page, d + 2.0)

        page.close()
        context.close()

        if video is None:
            raise RuntimeError("Playwright did not create a video object.")
        recorded_path = Path(video.path())
        browser.close()

    shutil.copy2(recorded_path, output)
    timeline_path.write_text(
        json.dumps({"gap_seconds": GAP_SECONDS, "cues": cues}, indent=2),
        encoding="utf-8",
    )
    print(
        f"Recorded: {output} ({VIDEO_WIDTH}x{VIDEO_HEIGHT}, raw/silent Playwright capture)"
    )
    print(f"Timeline: {timeline_path}")


if __name__ == "__main__":
    main()
