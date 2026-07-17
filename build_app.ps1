$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectDir "venv\Scripts\python.exe"
$spec = Join-Path $projectDir "GestureAssistant.spec"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project interpreter not found: $python"
}

Push-Location $projectDir
try {
    & $python -m PyInstaller --noconfirm --clean $spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Built: $projectDir\dist\GestureAssistant\GestureAssistant.exe"
