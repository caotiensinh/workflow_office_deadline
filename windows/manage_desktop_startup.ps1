# Opt-in Startup-folder launcher. Never writes registry, services or Task Scheduler.
# Default -PlanOnly is read-only and works in service Session 0 for CI review.
[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [switch]$Install,
    [switch]$Remove,
    [string]$Executable = '',
    [string]$DbPath = '',
    [string]$TestStartupDir = '',
    [switch]$ReplaceExisting
)
$ErrorActionPreference = 'Stop'
if ($Install -and $Remove) { throw 'Install and Remove are mutually exclusive' }
if (-not $Install -and -not $Remove) { $PlanOnly = $true }
if ($PlanOnly -and ($Install -or $Remove)) { throw 'PlanOnly must not mutate startup' }
$Project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($Executable)) {
    $Executable = Join-Path $Project 'dist\EDUNotifications.exe'
}
if ([string]::IsNullOrWhiteSpace($DbPath)) {
    $DbPath = Join-Path $Project 'data\workflow.sqlite3'
}
foreach ($p in @($Executable,$DbPath,$TestStartupDir)) {
    if ($p -match '[\x00-\x1F"]') { throw 'Unsafe path characters in startup configuration' }
}
$sessionId = (Get-Process -Id $PID).SessionId
if ($TestStartupDir) {
    if ($env:GITHUB_ACTIONS -ne 'true') { throw 'TestStartupDir is permitted only in GitHub CI' }
    $tempRoot = [IO.Path]::GetFullPath($env:RUNNER_TEMP).TrimEnd('\') + '\'
    $dir = [IO.Path]::GetFullPath($TestStartupDir).TrimEnd('\') + '\'
    if (-not $dir.StartsWith($tempRoot,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'TestStartupDir must reside within RUNNER_TEMP'
    }
    $Startup = $dir.TrimEnd('\')
} else {
    $Startup = [Environment]::GetFolderPath('Startup')
    if (-not $Startup) { throw 'Current user Startup directory not available' }
}
$Shortcut = Join-Path $Startup 'EDU_Workflow_Notifications.lnk'
$plan = [ordered]@{
    action = $(if ($Install) { 'install' } elseif ($Remove) { 'remove' } else { 'preview' })
    startup = $Shortcut
    executable = $Executable
    database = $DbPath
    session_id = $sessionId
    installs_for = 'current-user-only'
    starts_with_windows_login = $true
    requires_interactive_session = $true
    modifies_registry = $false
    modifies_task_scheduler = $false
    requires_admin = $false
}
if ($PlanOnly) {
    $plan | ConvertTo-Json -Compress
    return
}
if ($sessionId -eq 0 -and -not $TestStartupDir) {
    throw 'Refusing to register interactive UI startup from Session 0 runner service'
}
if ($Install -and !(Test-Path -LiteralPath $Executable -PathType Leaf)) {
    throw 'Built EDUNotifications.exe not found; build the desktop package first'
}
if ($Install -and !(Test-Path -LiteralPath $DbPath -PathType Leaf)) {
    throw 'Workflow database not found; do not install a broken startup link'
}
$ws = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $Shortcut -PathType Leaf) {
    $current = $ws.CreateShortcut($Shortcut)
    if ($current.Description -ne 'Education Workflow Notification Center W5') {
        throw 'Existing startup shortcut is not owned by this project; refusing to modify'
    }
    if ($Install -and -not $ReplaceExisting) { throw 'Already installed; no overwrite without ReplaceExisting' }
} elseif ($Remove) {
    throw 'No W5 startup link found; nothing removed'
}
if ($Install) {
    New-Item -ItemType Directory -Force -Path $Startup | Out-Null
    $link = $ws.CreateShortcut($Shortcut)
    $link.TargetPath = [IO.Path]::GetFullPath($Executable)
    $link.Arguments = '--db "' + [IO.Path]::GetFullPath($DbPath) + '"'
    $link.WorkingDirectory = $Project
    $link.Description = 'Education Workflow Notification Center W5'
    $link.WindowStyle = 1
    $link.Save()
    if (!(Test-Path -LiteralPath $Shortcut)) { throw 'Shortcut creation not confirmed' }
    Write-Host 'W5 current-user Startup link installed (starts on next user login)'
} else {
    Remove-Item -LiteralPath $Shortcut -Force
    Write-Host 'W5 current-user Startup link removed'
}
