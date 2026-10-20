# W23A: register one synthetic task and invoke it on disposable GitHub-hosted Windows.
# No self-hosted or institutional task may be touched.
[CmdletBinding()]
param([switch]$PlanOnly, [switch]$LiveHosted)
$ErrorActionPreference = 'Stop'
if ([bool]$PlanOnly -eq [bool]$LiveHosted) { throw 'Select exactly one mode' }
if ($PlanOnly) {
  [ordered]@{
    phase='W23A'; mode='plan-only'; task_interval_minutes=15
    real_task_created=$false; actual_scheduled_15m_cadence_observed=$false
    requires_ephemeral_github_hosted_runner=$true; outlook_accessed=$false
    smtp_sent=$false; production_accepted=$false
  } | ConvertTo-Json -Compress
  return
}
# Require explicit hosted identity and opt-in before ANY Task Scheduler operation.
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:RUNNER_OS -ne 'Windows' -or $env:W23_ALLOW_DISPOSABLE_TASK_CREATE -ne 'yes') {
  throw 'W23A_LIVE_TASK_BLOCKED_NON_HOSTED_OR_NO_OPT_IN'
}
if ([string]::IsNullOrWhiteSpace($env:RUNNER_TEMP) -or
    !(Test-Path -LiteralPath $env:RUNNER_TEMP -PathType Container)) {
  throw 'No disposable runner temp folder'
}
$token = [guid]::NewGuid().ToString('N')
$taskName = 'W23_Synthetic_Hosted_' + $token.Substring(0,16)
$stage = Join-Path $env:RUNNER_TEMP ('w23-scheduler-' + $token)
$created = $false
New-Item -ItemType Directory -Path $stage -ErrorAction Stop | Out-Null
try {
  $cmdFile = Join-Path $stage 'synthetic_tick.cmd'
  $marker = Join-Path $stage 'only_synthetic_tick.txt'
  @('@echo off', 'echo W23_SYNTHETIC_TICK>>"' + $marker + '"', 'exit /b 0') | Set-Content -LiteralPath $cmdFile -Encoding Ascii
  $syscmd = Join-Path $env:SystemRoot 'System32\cmd.exe'
  # Verify the same temporary action independently before Scheduler registers it;
  # never confuse this local check with the later Task Scheduler execution.
  & $syscmd /D /C ('"' + $cmdFile + '"')
  $preflight = ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $marker -PathType Leaf))
  Write-Host "W23A_HOSTED_LOCAL_CMD_PREFLIGHT_OK=$preflight"
  if (-not $preflight) { throw 'W23A synthetic local command wiring is invalid' }
  Remove-Item -LiteralPath $marker -Force -ErrorAction Stop
  $action = New-ScheduledTaskAction -Execute $syscmd -Argument ('/D /C "' + $cmdFile + '"')
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Hours 24)
  $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
  $null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Description 'W23 synthetic hosted CI task' -ErrorAction Stop
  $created = $true
  [xml]$xml = Export-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $interval = [string]$xml.Task.Triggers.TimeTrigger.Repetition.Interval
  $level = [string]$xml.Task.Principals.Principal.RunLevel
  $actualExe = [string]$xml.Task.Actions.Exec.Command
  $intervalOk = ($interval -eq 'PT15M')
  # Compare the actual registered principal enum, not XML display aliases.
  $registered = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $levelOk = ([string]$registered.Principal.RunLevel -eq 'Limited')
  $execOk = ([Environment]::ExpandEnvironmentVariables($actualExe) -eq $syscmd)
  # Safe booleans only: no paths, user identities or XML contents in public logs.
  Write-Host "W23A_TASK_XML_CHECK interval=$intervalOk limited=$levelOk executable=$execOk"
  if (-not ($intervalOk -and $levelOk -and $execOk)) {
    throw 'W23A hosted task settings did not match 15-minute least privilege'
  }
  # On-demand run proves only action wiring, NOT 15-minute automatic recurrence.
  Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $observed = $false
  for ($i = 0; $i -lt 120; $i++) {
    if (Test-Path -LiteralPath $marker -PathType Leaf) {
      $lines = @(Get-Content -LiteralPath $marker)
      $observed = ($lines.Count -ge 1 -and $lines[0] -eq 'W23_SYNTHETIC_TICK')
      if ($observed) { break }
    }
    Start-Sleep -Milliseconds 250
  }
  if (-not $observed) {
    $detail = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
    $state = [string](Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue).State
    $exitCode = if ($null -eq $detail) { 'UNAVAILABLE' } else { [string]$detail.LastTaskResult }
    # No account name, private paths or command line is printed.
    Write-Host "W23A_SYNTHETIC_ACTION_DIAG state=$state last_result=$exitCode"
    throw 'W23A hosted on-demand task produced no synthetic marker'
  }
  Write-Host 'W23A_REAL_HOSTED_TASK_REGISTERED_AND_ONDEMAND_EXECUTED_NOT_15MIN_CADENCE'
} finally {
  try {
    if ($created) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop }
  } finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Stop }
  }
}
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
  throw 'W23A disposable task remains after cleanup'
}
Write-Host 'W23A_HOSTED_TASK_CLEANUP_PASS_NO_INSTITUTIONAL_ACCEPTANCE'
