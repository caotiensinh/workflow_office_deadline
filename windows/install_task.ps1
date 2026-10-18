param([ValidateRange(5,1439)][int]$IntervalMinutes=15)
$ErrorActionPreference='Stop'
$Script = (Resolve-Path (Join-Path $PSScriptRoot 'run_once.ps1')).Path
$Project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Rust = Join-Path $Project 'rust-core\target\release\edu_rules.exe'
if (!(Test-Path $Rust)) { throw 'Build Rust first: cargo build --release --manifest-path rust-core\Cargo.toml' }
$TaskCommand = 'powershell.exe -NoProfile -File "{0}" -Channel file' -f $Script
# Uses the current user, limited rights. Local group policy can still block registration.
& schtasks.exe /Create /F /SC MINUTE /MO $IntervalMinutes /TN EducationAIWorkflow /TR $TaskCommand /RL LIMITED
if ($LASTEXITCODE -ne 0) { throw "Task Scheduler registration failed with exit code $LASTEXITCODE" }
& schtasks.exe /Query /TN EducationAIWorkflow
Write-Host 'Notification channel: local file spool only. No emails will be sent.'
