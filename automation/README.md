# Deterministic Hackathon video pipeline

This folder turns the local Streamlit prototype into a repeatable narrated demo.
The final recording automatically runs **both** scenarios:

1. **Semantic Delta** — individually permitted observations compose into newly sensitive strategic knowledge; smokescreen events are filtered; external publication is blocked.
2. **Consequence Delta** — no sensitive content is involved; individually authorized operations compose into an effectively irreversible production state; approval is required.

## Components

- **Playwright** drives the UI and records the browser viewport to WebM.
- **edge-tts** generates segmented AI narration. No API key is required, but network access is required.
- **MoviePy** places each narration segment at the actual Playwright cue time and exports H.264/AAC MP4.
- `make_video.ps1` runs the whole production path after one-time setup.

## One-time setup

First make sure the normal demo virtual environment exists. From the repo root:

```powershell
.\run.ps1
```

Once Streamlit opens successfully, stop it with `Ctrl+C`.

Install the optional automation dependencies into the same environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-automation.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

The Chromium download is a one-time Playwright setup.

## Recommended: one-command final recording

From the repo root:

```powershell
.\automation\make_video.ps1
```

It will:

1. generate segmented AI narration;
2. start Streamlit in the background;
3. run and record Semantic Delta automatically;
4. scroll to the final assessment and comparison;
5. switch to Consequence Delta and run it automatically;
6. return to the thesis for the closing shot;
7. align narration clips to the actual recorded cue timestamps;
8. export the final MP4;
9. stop the background Streamlit process.

Outputs:

```text
artifacts/
  narration/                  # individual TTS clips
  voice_manifest.json         # real audio durations
  agent-horizon-demo.webm     # raw Playwright recording
  record_timeline.json        # actual visual cue timestamps
  agent-horizon-final.mp4     # narrated submission video
```

## Debug the Playwright path visually

To watch the automation before making the final recording:

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe automation\record_demo.py --headed
```

The browser will visibly click, run, scroll and switch scenarios by itself.

## TTS tuning

Default voice:

```text
en-US-AvaNeural
```

Default rate is `+5%` to preserve comfortable headroom under the Hackathon's 2-minute limit.

List available voices:

```powershell
.\.venv\Scripts\edge-tts.exe --list-voices
```

Regenerate faster if needed:

```powershell
.\.venv\Scripts\python.exe automation\generate_voice.py --rate +12%
```

Then re-run `record_demo.py` and `compose_video.py`, because the recorder uses the actual voice durations to determine visual hold times.

## If edge-tts is blocked

The core demo and Playwright recording still work. You can keep `agent-horizon-demo.webm`, generate narration with Clipchamp or another TTS provider, and combine it manually. No Azure service is required for the prototype itself.


## Raw recording vs final video

`record_demo.py` intentionally produces a **silent** WebM (`artifacts/agent-horizon-demo.webm`). Playwright records the browser viewport only; narration is not embedded at this stage.

Run `compose_video.py` (or `make_video.ps1`) to combine that video with the segmented TTS narration. The deliverable is `artifacts/agent-horizon-final.mp4`.

v0.5 also forces Streamlit's main content container to use the full 1600×900 recording viewport so the app does not appear as a narrow column with unused space on the right.
