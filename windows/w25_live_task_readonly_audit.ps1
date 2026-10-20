# W25B - opt-in, READ-ONLY audit of the exact local EducationAIWorkflow task.
# No registration, deletion, task execution, Event Log, credentials or mail access.
[CmdletBinding()]
param(
  [switch]$PlanOnly,
  [switch]$AuditLive,
  [switch]$ITAuthorized
)
$ErrorActionPreference='Stop'
if ([bool]$PlanOnly -eq [bool]$AuditLive) {
  throw 'Select exactly one of PlanOnly and AuditLive'
}
if ($PlanOnly) {
  [ordered]@{
    phase='W25B'; mode='plan-only'; task_name='EducationAIWorkflow'
    task_inspected=$false; machine_modified=$false
    requires_explicit_IT_authorization=$true
    fifteen_minute_runs_observed=$false
    it_approved=$false; production_accepted=$false
  } | ConvertTo-Json -Compress
  return
}
if (-not $ITAuthorized) {
  throw 'W25B_READ_ONLY_AUDIT_REQUIRES_EXPLICIT_IT_PERMISSION'
}
# Fixed exact task; no caller-supplied arbitrary task names, paths, recipients.
$taskName = 'EducationAIWorkflow'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) { throw 'W25B_APPROVED_TASK_NOT_FOUND' }
[xml]$xml = Export-ScheduledTask -TaskName $taskName -ErrorAction Stop
$actions = @($task.Actions)
$actionOk = $actions.Count -eq 1 -and
  [string]$actions[0].Execute -match '^(?i:powershell\.exe)$' -and
  [string]$actions[0].Arguments -cmatch '^-NoProfile -File "[A-Za-z]:\\(?:[A-Za-z0-9 _.-]+\\)*run_once\.ps1" -Channel file$'
$intervalOk = [string]$xml.Task.Triggers.TimeTrigger.Repetition.Interval -eq 'PT15M'
$triggerEnabled = [string]$xml.Task.Triggers.TimeTrigger.Enabled -eq 'true'
$limitedOk = [string]$task.Principal.RunLevel -eq 'Limited'
$activeOk = [string]$task.State -ne 'Disabled'
$checks = [ordered]@{
  exact_fixed_task_present = $true
  one_file_only_powershell_action = [bool]$actionOk
  fifteen_minute_trigger_configured = [bool]$intervalOk
  trigger_enabled = [bool]$triggerEnabled
  runs_as_limited_user = [bool]$limitedOk
  task_not_disabled = [bool]$activeOk
}
# Do not leak account, path, task XML, event history, or command line.
$result = [ordered]@{
  phase='W25B'
  status=$(if (@($checks.Values | Where-Object { -not $_ }).Count -eq 0) {
    'LIVE_CONFIG_MATCH_NOT_RUN_ACCEPTANCE'
  } else {
    'LIVE_CONFIG_MISMATCH_NOT_RUN_ACCEPTANCE'
  })
  checks=$checks
  read_only=$true
  task_found=$true
  task_executed_in_this_audit=$false
  fifteen_minute_runs_observed=$false
  login_autorun_verified=$false
  outlook_accessed=$false
  smtp_sent=$false
  it_approved=$false
  production_accepted=$false
  modifies_machine=$false
}
$result | ConvertTo-Json -Depth 5 -Compress
if ($result.status -ne 'LIVE_CONFIG_MATCH_NOT_RUN_ACCEPTANCE') { exit 3 }
