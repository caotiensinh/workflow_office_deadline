# W24B disposable hosted Windows Startup .lnk roundtrip only.
# PlanOnly reads no Startup folder. LiveHosted is hard-denied on self-hosted devices.
[CmdletBinding()]
param([switch]$PlanOnly, [switch]$LiveHosted)
$ErrorActionPreference = 'Stop'
if ([bool]$PlanOnly -eq [bool]$LiveHosted) { throw 'Select exactly one mode' }
if ($PlanOnly) {
  [ordered]@{
    phase='W24B'; mode='plan-only'; startup_link_created=$false
    actual_login_restart_observed=$false; user_profile_modified=$false
    outlook_accessed=$false; smtp_sent=$false; it_approved=$false
    production_accepted=$false
  } | ConvertTo-Json -Compress
  return
}
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted' -or
    $env:RUNNER_OS -ne 'Windows' -or $env:W24_ALLOW_DISPOSABLE_STARTUP_TEST -ne 'yes') {
  throw 'W24B_STARTUP_WRITE_BLOCKED_OUTSIDE_DISPOSABLE_GITHUB_WINDOWS'
}
$dir = [Environment]::GetFolderPath([Environment+SpecialFolder]::Startup)
if ([string]::IsNullOrWhiteSpace($dir) -or !(Test-Path -LiteralPath $dir -PathType Container)) {
  throw 'W24B valid Windows user Startup folder unavailable'
}
$token = [guid]::NewGuid().ToString('N')
$lnk = Join-Path $dir ('W24-Synthetic-Hosted-' + $token + '.lnk')
$cmd = Join-Path $env:SystemRoot 'System32\cmd.exe'
$created=$false
try {
  if (Test-Path -LiteralPath $lnk) { throw 'W24B refuses existing Startup entry overwrite' }
  $shell=New-Object -ComObject WScript.Shell
  $shortcut=$shell.CreateShortcut($lnk)
  $shortcut.TargetPath=$cmd
  $shortcut.Arguments='/D /C exit 0'
  $shortcut.Description='W24 synthetic hosted short-lived startup verifier'
  $shortcut.Save()
  $created=$true
  # Read back the actual .lnk properties from Windows Shell COM.
  $reopen=$shell.CreateShortcut($lnk)
  $targetOk=([string]$reopen.TargetPath -eq $cmd)
  $argsOk=([string]$reopen.Arguments -eq '/D /C exit 0')
  $uniqueOk=(Get-Item -LiteralPath $lnk -ErrorAction Stop).Length -gt 0
  Write-Host "W24B_REAL_STARTUP_LINK_CHECK target=$targetOk args=$argsOk file=$uniqueOk"
  if (-not ($targetOk -and $argsOk -and $uniqueOk)) {
    throw 'W24B saved Startup link did not round-trip'
  }
  Write-Host 'W24B_REAL_HOSTED_USER_STARTUP_SHORTCUT_READBACK_PASS_NOT_LOGIN_AUTORUN'
} finally {
  if ($created) { Remove-Item -LiteralPath $lnk -Force -ErrorAction Stop }
}
if (Test-Path -LiteralPath $lnk) { throw 'W24B synthetic Startup shortcut remains' }
Write-Host 'W24B_HOSTED_STARTUP_LINK_REMOVED_NO_INSTITUTIONAL_ACCEPTANCE'
