$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studioPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) {
    $studioPython = Join-Path (Split-Path $PSScriptRoot -Parent) '.tools\python\python.exe'
}
if (-not (Test-Path -LiteralPath $studioPython)) { $studioPython = 'python' }
& $studioPython src/dashboard.py
