from __future__ import annotations

import asyncio
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "automation" / "narration_segments.json"
OUT = ROOT / "artifacts" / "voice"

async def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"segments":[]}
    for seg in cfg["segments"]:
        path = OUT / f'{seg["id"]}.mp3'
        communicate = edge_tts.Communicate(seg["text"], cfg["voice"], rate=cfg.get("rate","+0%"))
        await communicate.save(str(path))
        manifest["segments"].append({"id":seg["id"],"path":str(path)})
        print("wrote", path)
    (ROOT/"artifacts"/"voice_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
