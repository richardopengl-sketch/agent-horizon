param(
  [string]$Repo = (Get-Location).Path
)
$ErrorActionPreference="Stop"
$patch = Split-Path -Parent $MyInvocation.MyCommand.Path
$backup = Join-Path $Repo ("upgrade-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $backup | Out-Null

$files = @(
  "app.py",
  "AGENT_READINESS.md",
  "DEMO_V2.md",
  ".github\copilot-instructions.md",
  "scripts\validate.ps1",
  "automation\narration_segments.json",
  "automation\generate_voice.py",
  "automation\record_demo.py",
  "automation\compose_video.py",
  "automation\make_video.ps1"
)

foreach($rel in $files) {
  $src = Join-Path $patch $rel
  $dst = Join-Path $Repo $rel
  if(Test-Path $dst) {
    $bak = Join-Path $backup $rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bak) | Out-Null
    Copy-Item $dst $bak -Force
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
  Copy-Item $src $dst -Force
}
Write-Host "Upgrade applied. Backup: $backup"
Write-Host "Next: .\scripts\validate.ps1"
