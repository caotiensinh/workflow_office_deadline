# W24A: GitHub-hosted ephemeral Windows only. 1-minute real clock repetitions, NOT institution 15-min acceptance.
# W24A: register one synthetic task and invoke it on disposable GitHub-hosted Windows.
# No self-hosted or institutional task may be touched.
[CmdletBinding()]
param([switch]$PlanOnly, [switch]$AutomaticHosted)
$ErrorActionPreference = 'Stop'
if ([bool]$PlanOnly -eq [bool]$AutomaticHosted) { throw 'Select exactly one mode' }
if ($PlanOnly) {
  [ordered]@{
    phase='W24A'; mode='plan-only'; task_interval_minutes=1
    real_task_created=$false; actual_scheduled_15m_cadence_observed=$false
    requires_ephemeral_github_hosted_runner=$true; outlook_accessed=$false
    smtp_sent=$false; production_accepted=$false
  } | ConvertTo-Json -Compress
  return
}
# Require explicit hosted identity and opt-in before ANY Task Scheduler operation.
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:RUNNER_OS -ne 'Windows' -or $env:W24_ALLOW_DISPOSABLE_TASK_CREATE -ne 'yes') {
  throw 'W24A_LIVE_TASK_BLOCKED_NON_HOSTED_OR_NO_OPT_IN'
}
if ([string]::IsNullOrWhiteSpace($env:RUNNER_TEMP) -or
    !(Test-Path -LiteralPath $env:RUNNER_TEMP -PathType Container)) {
  throw 'No disposable runner temp folder'
}
$token = [guid]::NewGuid().ToString('N')
$taskName = 'W24_Synthetic_Hosted_' + $token.Substring(0,16)
$stage = Join-Path $env:RUNNER_TEMP ('w24-scheduler-' + $token)
$created = $false
New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
try {
  $cmdFile = Join-Path $stage 'synthetic_tick.cmd'
  $marker = Join-Path $stage 'only_synthetic_tick.txt'
  $markerLine = 'echo W24_SYNTHETIC_TICK>>"' + $marker + '"'
  @('@echo off', $markerLine, 'exit /b 0') | Set-Content -LiteralPath $cmdFile -Encoding Ascii
  $syscmd = Join-Path $env:SystemRoot 'System32\cmd.exe'
  # Verify the same temporary action independently before Scheduler registers it;
  # never confuse this local check with the later Task Scheduler execution.
  if ($cmdFile -notmatch '^[A-Za-z]:\\[A-Za-z0-9_.\\-]+$') { throw 'Unsafe temporary CMD path' }
  & $syscmd /D /C call $cmdFile
  $localExit = $LASTEXITCODE
  $preflight = ($localExit -eq 0 -and (Test-Path -LiteralPath $marker -PathType Leaf))
  $numLines = @(Get-Content -LiteralPath $cmdFile).Count
  Write-Host "W24A_HOSTED_LOCAL_CMD_PREFLIGHT_OK=$preflight exit_code=$localExit script_lines=$numLines"
  if (-not $preflight) { throw 'W24A synthetic local command wiring is invalid' }
  Remove-Item -LiteralPath $marker -Force -ErrorAction Stop
  $action = New-ScheduledTaskAction -Execute $syscmd -Argument ('/D /C call ' + $cmdFile)
  # Two natural 1-minute activations fit within one hosted CI run; never mislabel 15 minutes.
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(35) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Minutes 5)
  $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
  $null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description 'W23 synthetic hosted CI task' -ErrorAction Stop
  $created = $true
  [xml]$xml = Export-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $interval = [string]$xml.Task.Triggers.TimeTrigger.Repetition.Interval
  $level = [string]$xml.Task.Principals.Principal.RunLevel
  $actualExe = [string]$xml.Task.Actions.Exec.Command
  $intervalOk = ($interval -eq 'PT1M')
  # Compare the actual registered principal enum, not XML display aliases.
  $registered = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $levelOk = ([string]$registered.Principal.RunLevel -eq 'Limited')
  $execOk = ([Environment]::ExpandEnvironmentVariables($actualExe) -eq $syscmd)
  # Safe booleans only: no paths, user identities or XML contents in public logs.
  Write-Host "W24A_TASK_XML_CHECK interval=$intervalOk limited=$levelOk executable=$execOk"
  if (-not ($intervalOk -and $levelOk -and $execOk)) {
    throw 'W24A hosted task settings did not match 1-minute least privilege'
  }
  # W24A: do NOT call Start-ScheduledTask; witness TWO clock-triggered firings.
  $observed = 0
  for ($i = 0; $i -lt 165; $i++) {
    if (Test-Path -LiteralPath $marker -PathType Leaf) {
      $lines = @(Get-Content -LiteralPath $marker)
      if ($lines.Count -gt 0 -and @($lines | Where-Object { $_ -ne 'W24_SYNTHETIC_TICK' }).Count -ne 0) {
        throw 'Unexpected synthetic task marker content'
      }
      $observed = $lines.Count
      if ($observed -ge 2) { break }
    }
    Start-Sleep -Seconds 1
  }
  if ($observed -lt 2) {
    $last = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
    $code = if ($null -eq $last) { 'UNAVAILABLE' } else { [string]$last.LastTaskResult }
    Write-Host "W24A_AUTOMATIC_FIRE_MISSING observed_count=$observed last_result=$code"
    throw 'W24A hosted 1-minute task failed to fire twice autonomously'
  }
  Write-Host 'W24A_AUTOMATIC_ONE_MINUTE_TWO_TRIGGERS_OBSERVED_NOT_15_MINUTES'

} finally {
  try {
    if ($created) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop }
  } finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Stop }
  }
}
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw 'W24A disposable task remains after cleanup'
}
Write-Host 'W24A_AUTOMATIC_TASK_CLEANUP_PASS_NO_INSTITUTIONAL_ACCEPTANCE'
