$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
python -m pip install -r requirements.txt
pytest -q
python -m py_compile app.py core\*.py scenarios\*.py automation\*.py
Write-Host "Validation passed."
