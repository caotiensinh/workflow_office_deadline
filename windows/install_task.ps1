# Register a limited-rights user task. Default: rule evaluation only; no Outlook or SMTP.
# PlanOnly never touches Task Scheduler and is safe for IT review / CI.
[CmdletBinding()]
param(
  [ValidateRange(5,1439)][int]$IntervalMinutes = 15,
  [string]$ImportEmlDir = '',
  [switch]$ImportOutlookClassic,
  [switch]$PlanOnly,
  [switch]$ReplaceExisting
)
$ErrorActionPreference = 'Stop'
$TaskName = 'EducationAIWorkflow'
$Script = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'run_once.ps1')).Path
$Project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Rust = Join-Path $Project 'rust-core\target\release\edu_rules.exe'

if ($ImportOutlookClassic -and -not [string]::IsNullOrWhiteSpace($ImportEmlDir)) {
  throw 'Choose either Outlook Classic or an EML folder, not both'
}
$folder = ''
if (-not [string]::IsNullOrWhiteSpace($ImportEmlDir)) {
  $folder = (Resolve-Path -LiteralPath $ImportEmlDir).Path
  if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
    throw 'EML input source must be a directory'
  }
}
foreach ($path in @($Script, $folder)) {
  if ($path -match '[\x00-\x1F"]') {
    throw 'Unsafe path characters in task command'
  }
}
# Task Scheduler executes the command as the current user (no elevation).
# Quoting the paths prevents whitespace in installation or EML folder paths
# from being interpreted as additional flags.
$TaskCommand = 'powershell.exe -NoProfile -File "' + $Script + '" -Channel file'
if ($ImportOutlookClassic) {
  $TaskCommand += ' -ImportOutlookClassic'
}
if ($folder) {
  $TaskCommand += ' -ImportEmlDir "' + $folder + '"'
}
$plan = [ordered]@{
  task_name = $TaskName
  interval_minutes = $IntervalMinutes
  command = $TaskCommand
  source = $(if ($ImportOutlookClassic) { 'outlook-classic' } elseif ($folder) { 'eml' } else { 'none' })
  notification_channel = 'file'
  replaces_existing = [bool]$ReplaceExisting
}
if ($PlanOnly) {
  $plan | ConvertTo-Json -Compress
  return
}
if (!(Test-Path -LiteralPath $Rust -PathType Leaf)) {
  throw 'Build Rust first: cargo build --release --manifest-path rust-core\Cargo.toml'
}
& schtasks.exe /Query /TN $TaskName *> $null
$exists = ($LASTEXITCODE -eq 0)
if ($exists -and -not $ReplaceExisting) {
  throw 'Existing scheduled task detected; use -ReplaceExisting only after reviewing its current configuration'
}
$createArgs = @('/Create','/SC','MINUTE','/MO',[string]$IntervalMinutes,
                '/TN',$TaskName,'/TR',$TaskCommand,'/RL','LIMITED')
if ($ReplaceExisting) { $createArgs += '/F' }
& schtasks.exe @createArgs
if ($LASTEXITCODE -ne 0) {
  throw "Task Scheduler registration failed with exit code $LASTEXITCODE"
}
& schtasks.exe /Query /TN $TaskName
if ($LASTEXITCODE -ne 0) {
  throw 'Task created but query failed: state UNKNOWN; inspect Task Scheduler before retrying'
}
Write-Host 'Task registered as current user. File-only notifications; no SMTP is enabled.'
if ($ImportOutlookClassic) {
  Write-Warning 'Outlook COM requires IT approval and a suitable interactive Outlook Classic session.'
}
