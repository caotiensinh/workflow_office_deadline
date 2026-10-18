param(
  [string]$Python = 'python',
  [ValidateSet('file','smtp','console')][string]$Channel='file',
  [switch]$ImportOutlookClassic
)
$ErrorActionPreference='Stop'
$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONPATH = Join-Path $Project 'python'
$Db = Join-Path $Project 'data\workflow.sqlite3'
$Rust = Join-Path $Project 'rust-core\target\release\edu_rules.exe'
if (!(Test-Path $Rust)) { throw 'Rust engine not compiled. Run: cargo build --release --manifest-path rust-core\Cargo.toml' }
if ($ImportOutlookClassic) {
  & $Python -m edu_workflow.cli --db $Db import-outlook-classic
  if ($LASTEXITCODE -ne 0) { throw "Outlook import failed: $LASTEXITCODE" }
}
& $Python -m edu_workflow.cli --db $Db tick --backend rust --rust-bin $Rust
if ($LASTEXITCODE -ne 0) { throw "Rust policy cycle failed: $LASTEXITCODE" }
& $Python -m edu_workflow.cli --db $Db deliver --channel $Channel --out-dir (Join-Path $Project 'notifications')
if ($LASTEXITCODE -ne 0) { throw "Alert dispatch failed: $LASTEXITCODE" }
