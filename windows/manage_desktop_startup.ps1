# Opt-in Startup-folder launcher. Never writes registry, services or Task Scheduler.
# Default -PlanOnly is read-only and works in service Session 0 for CI review.
[CmdletBinding()]
param(
    [switch]$PlanOnly,
    [switch]$Install,
    [switch]$Remove,
    [switch]$Verify,
    [string]$Executable = '',
    [string]$DbPath = '',
    [string]$TestStartupDir = '',
    [switch]$ReplaceExisting
)
$ErrorActionPreference = 'Stop'
if (([int]$Install.IsPresent + [int]$Remove.IsPresent + [int]$Verify.IsPresent + [int]$PlanOnly.IsPresent) -gt 1) {
    throw 'Choose only one of PlanOnly, Verify, Install or Remove'
}
if (-not $Install -and -not $Remove -and -not $Verify) { $PlanOnly = $true }
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
    action = $(if ($Install) { 'install' } elseif ($Remove) { 'remove' } elseif ($Verify) { 'verify' } else { 'preview' })
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

# All path and ownership checks are read-only. A valid shortcut does not prove
# that Explorer started the app at actual login or that its GUI was visible.
$ExpectedExecutable = [IO.Path]::GetFullPath($Executable)
$ExpectedArguments = '--db "' + [IO.Path]::GetFullPath($DbPath) + '"'
$ws = New-Object -ComObject WScript.Shell
$exists = Test-Path -LiteralPath $Shortcut -PathType Leaf
$owned = $false
$targetMatches = $false
$argumentsMatch = $false
if ($exists) {
    $current = $ws.CreateShortcut($Shortcut)
    $owned = ($current.Description -ceq 'Education Workflow Notification Center W5')
    $targetMatches = [string]::Equals($current.TargetPath, $ExpectedExecutable,
        [StringComparison]::OrdinalIgnoreCase)
    $argumentsMatch = [string]::Equals($current.Arguments, $ExpectedArguments,
        [StringComparison]::OrdinalIgnoreCase)
}
if ($Verify) {
    [ordered]@{
        mode = 'read-only-startup-verification'
        session_id = $sessionId
        is_interactive_session = [bool]($sessionId -ne 0)
        link_exists = [bool]$exists
        project_owned = [bool]$owned
        target_matches = [bool]$targetMatches
        arguments_match = [bool]$argumentsMatch
        executable_exists = [bool](Test-Path -LiteralPath $ExpectedExecutable -PathType Leaf)
        database_exists = [bool](Test-Path -LiteralPath $DbPath -PathType Leaf)
        valid_link = [bool]($exists -and $owned -and $targetMatches -and $argumentsMatch)
        actual_login_autorun_verified = $false
        changes_machine = $false
    } | ConvertTo-Json -Compress
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
if ($exists) {
    if (-not $owned) {
        throw 'Existing startup shortcut is not owned by this project; refusing to modify'
    }
    # Even a link with our descriptive label might point somewhere else.
    # Refuse to remove a mismatched shortcut; -ReplaceExisting remains
    # an explicit, user-approved repair/upgrade action on project-owned links.
    if ($Remove -and (-not $targetMatches -or -not $argumentsMatch)) {
        throw 'Startup shortcut target or DB arguments differ; refusing to remove an unexpected link'
    }
    if ($Install -and -not $ReplaceExisting) { throw 'Already installed; no overwrite without ReplaceExisting' }
} elseif ($Remove) {
    throw 'No W5 startup link found; nothing removed'
}
if ($Install) {
    New-Item -ItemType Directory -Force -Path $Startup | Out-Null
    $link = $ws.CreateShortcut($Shortcut)
    $link.TargetPath = $ExpectedExecutable
    $link.Arguments = $ExpectedArguments
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
