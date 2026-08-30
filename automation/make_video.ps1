$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    throw "Missing .venv. Run .\run.ps1 once first, then stop Streamlit with Ctrl+C."
}

try {
    $existing = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 1
    if ($existing.StatusCode -eq 200) {
        throw "Port 8501 is already in use. Stop the currently running Streamlit window with Ctrl+C, then run this script again."
    }
} catch {
    if ($_.Exception.Message -like "Port 8501 is already in use*") { throw }
}

Write-Host "[1/5] Generating segmented AI narration..." -ForegroundColor Cyan
& $python automation/generate_voice.py
if ($LASTEXITCODE -ne 0) { throw "TTS generation failed." }

Write-Host "[2/5] Starting Streamlit in the background..." -ForegroundColor Cyan
$streamlit = Start-Process -FilePath $python `
    -ArgumentList @("-m", "streamlit", "run", "app.py", "--server.headless=true", "--server.port=8501") `
    -WorkingDirectory $repo `
    -PassThru `
    -WindowStyle Hidden

try {
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {}
    }
    if (!$ready) { throw "Streamlit did not become ready on http://localhost:8501." }

    Write-Host "[3/5] Recording deterministic browser demo with Playwright..." -ForegroundColor Cyan
    & $python automation/record_demo.py
    if ($LASTEXITCODE -ne 0) { throw "Playwright recording failed." }

    Write-Host "[4/5] Composing narration + browser video..." -ForegroundColor Cyan
    & $python automation/compose_video.py
    if ($LASTEXITCODE -ne 0) { throw "Video composition failed." }

    Write-Host "[5/5] Done." -ForegroundColor Green
    Write-Host "Final video: artifacts\agent-horizon-final.mp4" -ForegroundColor Green
}
finally {
    if ($streamlit -and !$streamlit.HasExited) {
        Stop-Process -Id $streamlit.Id -Force -ErrorAction SilentlyContinue
    }
}
