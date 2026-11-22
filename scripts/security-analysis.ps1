$ErrorActionPreference = "Continue"
Set-Location (Resolve-Path "$PSScriptRoot\..")

$report = "evidence\slither-latest.json"
New-Item -ItemType Directory -Force "evidence" | Out-Null
if (Test-Path $report) { Remove-Item $report }

Write-Host "Running Slither against production contract..."
python -m slither . `
  --filter-paths "node_modules|contracts/test" `
  --exclude "naming-convention,solc-version" `
  --json $report
$slitherExit = $LASTEXITCODE

if (!(Test-Path $report)) {
  throw "Slither failed without producing $report (exit $slitherExit)."
}

$result = Get-Content $report -Raw | ConvertFrom-Json
if ($result.success -ne $true -or $null -eq $result.results) {
  throw "Slither produced an unsuccessful or malformed JSON report (exit $slitherExit)."
}

if ($slitherExit -ne 0) {
  Write-Warning "Slither reported findings (exit $slitherExit). See audit/SECURITY_REPORT.md for interpretation."
} else {
  Write-Host "Slither completed with no detector findings."
}
Write-Host "Raw machine-readable output: $report"
