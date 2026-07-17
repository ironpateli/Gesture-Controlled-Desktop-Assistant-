$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$compilerCandidates = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1),
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

$compiler = $compilerCandidates | Select-Object -First 1
if (-not $compiler) {
    throw "Inno Setup was not found. Install Inno Setup 6 or 7, then rerun build_installer.ps1."
}

$app = Join-Path $projectDir "dist\GestureAssistant\GestureAssistant.exe"
if (-not (Test-Path -LiteralPath $app)) {
    throw "Packaged application not found. Run build_app.ps1 first."
}

$script = Join-Path $projectDir "installer\GestureAssistant.iss"
Push-Location $projectDir
try {
    & $compiler $script
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host "Built: $projectDir\release\GestureAssistant-Setup-0.1.1.exe"
