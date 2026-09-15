# Agent Horizon demo v2

Target: ~90–105 seconds, 1920×1080.

## Story
1. **Opening** — identity/authorization are necessary but per-action.
2. **Semantic Delta** — allowed reads compose into a new strategic fact.
3. **Boundary crossing** — external publish is blocked using accumulated context.
4. **Differentiation** — Horizon complements MCP/A2A/gateway/identity/guardrails.
5. **Consequence Delta** — no sensitive content; authorized operations remove rollback.
6. **Closing** — observe → reduce → compare → enforce.

## Generate the video

Terminal 1:

```powershell
streamlit run app.py
```

Terminal 2:

```powershell
.\automation\make_video.ps1
```

Output:
`artifacts\agent-horizon-demo-v2.mp4`

If Edge TTS voice availability changes, edit `voice` in
`automation/narration_segments.json`.
