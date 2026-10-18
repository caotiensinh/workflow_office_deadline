# Read-only by default. Scheduled run must never silently fall back to Python policy.
param(
  [string]$Python = 'python',
  [ValidateSet('file','smtp','console')][string]$Channel = 'file',
  [switch]$ImportOutlookClassic,
  [string]$DbPath = '',
  [string]$OutDir = '',
  [string]$At = ''
)
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONPATH = Join-Path $Project 'python'
if ([string]::IsNullOrWhiteSpace($DbPath)) { $DbPath = Join-Path $Project 'data\workflow.sqlite3' }
if ([string]::IsNullOrWhiteSpace($OutDir)) { $OutDir = Join-Path $Project 'notifications' }
$Rust = Join-Path $Project 'rust-core\target\release\edu_rules.exe'
if (!(Test-Path $Rust)) { throw 'Rust engine not compiled. Run: cargo build --release --manifest-path rust-core\Cargo.toml' }
if ($ImportOutlookClassic) {
  & $Python -m edu_workflow.cli --db $DbPath import-outlook-classic
  if ($LASTEXITCODE -ne 0) { throw "Outlook import failed: $LASTEXITCODE" }
}
$TickArgs = @('-m', 'edu_workflow.cli', '--db', $DbPath, 'tick', '--backend', 'rust', '--rust-bin', $Rust)
if (-not [string]::IsNullOrWhiteSpace($At)) { $TickArgs += @('--at', $At) }
& $Python @TickArgs
if ($LASTEXITCODE -ne 0) { throw "Rust policy cycle failed: $LASTEXITCODE" }
& $Python -m edu_workflow.cli --db $DbPath deliver --channel $Channel --out-dir $OutDir
if ($LASTEXITCODE -ne 0) { throw "Alert dispatch failed: $LASTEXITCODE" }
