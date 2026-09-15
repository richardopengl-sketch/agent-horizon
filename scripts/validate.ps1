$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
python scripts\validate_repo.py
if ($LASTEXITCODE -ne 0) { throw "Repository validation failed." }
Write-Host "Repository validation passed."
