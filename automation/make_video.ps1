$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "1/5 Installing automation dependencies..."
python -m pip install -r requirements-automation.txt
python -m playwright install chromium

Write-Host "2/5 Generating AI narration..."
python automation/generate_voice.py

Write-Host "3/5 Start Streamlit in another terminal if it is not already running:"
Write-Host "    streamlit run app.py"
Read-Host "Press Enter when http://localhost:8501 is ready"

Write-Host "4/5 Recording automated demo..."
python automation/record_demo.py --url http://localhost:8501 --headed

Write-Host "5/5 Composing narration + video..."
python automation/compose_video.py

Write-Host ""
Write-Host "DONE: artifacts/agent-horizon-demo-v2.mp4"
