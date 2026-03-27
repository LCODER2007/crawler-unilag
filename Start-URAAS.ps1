$PSScriptRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
if (-not $PSScriptRoot) {
    $PSScriptRoot = (Get-Location).Path
}

Write-Host "Setting up PYTHONPATH..."
$env:PYTHONPATH = $PSScriptRoot

Write-Host "Running Database Initialization..."
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\init_db.py"

Write-Host "Starting Dashboard..."
& "$PSScriptRoot\venv\Scripts\python.exe" "$PSScriptRoot\uraas\dashboard\app.py"
