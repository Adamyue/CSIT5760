$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

Write-Host "1/4 Compile"
npm run compile
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

Write-Host "2/4 Test"
npm test
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }

Write-Host "3/4 Coverage"
npm run coverage
if ($LASTEXITCODE -ne 0) { throw "Coverage failed." }

Write-Host "4/4 Security analysis"
powershell -ExecutionPolicy Bypass -File scripts/security-analysis.ps1
if ($LASTEXITCODE -ne 0) { throw "Security analysis command failed." }

Write-Host "All local verification stages completed."
