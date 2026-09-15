# Agent Horizon

**Contextual Security & Privacy for Agentic AI**

> Individually permitted agent actions can compose into unsafe outcomes.

Agent Horizon is a local Hackathon prototype that evaluates the **contextual delta** created by an agent trajectory rather than treating each content object or action independently.

## What v0.2 adds

The demo UI is now optimized for reviewer comprehension and recording:

- explicit **Before → After** delta cards,
- visible **sensitivity uplift** for derived knowledge,
- smokescreen/noise shown as **low-contribution evidence** rather than ordinary allowed events,
- a final **Horizon Assessment** card,
- a compact **current state** view that always shows the latest snapshot,
- a direct comparison between isolated checks and trajectory-aware evaluation,
- optional Playwright + AI narration automation under `automation/`.

## What the demo proves

### 1. Semantic Delta (hero scenario)

An agent is independently allowed to read three internal sources:

- Product roadmap: Project Nova targets a Q4 launch window.
- Supply reservation: high-volume manufacturing capacity begins October 14.
- Executive calendar: a global launch-readiness review is scheduled for October 2.

No individual source explicitly states an exact launch date. The agent correlates the evidence and derives:

> **Project Nova is likely scheduled for a mid-to-late October launch.**

The demo models the individual source sensitivity as **Internal** while the newly derived strategic conclusion becomes **Strategic / Highly Sensitive**. Agent Horizon detects this **Semantic Delta**. When the agent attempts to publish the derived conclusion externally, the action is blocked.

Optional weather and cafeteria events demonstrate **smokescreen resistance**: low-relevance activity remains in the trajectory but does not materially contribute to the active security state.

### 2. Consequence Delta

An agent performs individually authorized deployment operations. The final operation removes the last rollback artifact and changes the system from **reversible → effectively irreversible**.

No sensitive content is involved. Agent Horizon detects the **Consequence Delta** and requires human approval.

## Architecture

```text
Agent trajectory
      ↓
Structured AgentEvent
      ↓
Contextual State Reducer
      ↓
Delta Engine
 ┌───────────────┐
 │               │
Semantic      Consequence
 Delta           Delta
 │               │
 └───────┬───────┘
         ↓
Impact Assessment
         ↓
Fast Path / optional Slow Path
         ↓
ALLOW / AUDIT / CONSTRAIN / APPROVAL / BLOCK
```

The prototype deliberately keeps external dependencies mocked. The **Horizon engine itself is real code**: structured events, compact state, relevance-aware evidence handling, derived-sensitivity tracking, delta detection, and policy decisions all run locally.

## Why local-only for the Hackathon

The prototype does **not** require Azure, Purview, SharePoint, Outlook, or a live LLM. This keeps the demo deterministic and avoids auth/tenant/network dependencies. Those systems are integration points, not the innovation being demonstrated.

A future production architecture could receive events from native agent runtimes, tool middleware, MCP/A2A gateways, agent gateways, or audit streams.

## Run on Windows

### Fast path

```powershell
cd agent-horizon
.\run.ps1
```

### Manual setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints, normally `http://localhost:8501`.

## Engineering & validation

The repository is structured so humans and coding agents can understand, change, and validate it through the same bounded engineering loop.

Key entry points:

- `docs/architecture.md` — component boundaries, invariants, failure containment, and validation flow.
- `docs/agentic-loop.md` — agent contract, machine-readable completion signal, and review loop.
- `CONTRIBUTING.md` — development and pull-request expectations.
- `SECURITY.md` — secret handling and security review expectations.
- `.github/copilot-instructions.md` — repository guidance for GitHub Copilot.
- `scripts/validate_repo.py` — canonical deterministic validation command.

Run the full validation loop:

```powershell
python -m pip install -r requirements-dev.txt
python scripts\validate_repo.py
```

The validator runs tests, linting, type checks, compilation, and secret scanning, then writes:

```text
.reports/validation-report.json
```

For a quick test-only run:

```powershell
pytest -q
```

CI, scheduled repository-health checks, security scanning, dependency updates, code-owner review, and machine-readable validation artifacts are defined under `.github/`.

## Optional automated video pipeline

The `automation/` folder contains a repeatable recording/narration pipeline:

```text
Playwright → silent WebM recording
edge-tts  → AI narration MP3
MoviePy   → final H.264/AAC MP4
```

Setup:

```powershell
pip install -r requirements-automation.txt
python -m playwright install chromium
```

Then, while Streamlit is already running:

```powershell
python automation/record_demo.py
python automation/generate_voice.py
python automation/compose_video.py
```

See `automation/README.md` for details.

**Note:** Playwright's native browser video recording is WebM. `edge-tts` does not require an API key, but it uses an online TTS service and therefore requires network access.

## Scope / non-goals

- Not a content-classification or SIT scanner.
- Not a production DLP replacement.
- Not an agent that continuously watches another agent.
- Not a production-grade risk model.
- No external service is required for the MVP.

## Future extensions

- Replace the deterministic semantic reassessment stub with an LLM/classifier slow path.
- Add privacy-specific impact evaluators such as identifiability, linkability, purpose limitation, and consent context.
- Add an agent-runtime / MCP / A2A / gateway adapter.
- Integrate enterprise policy and audit providers such as Microsoft Purview.
