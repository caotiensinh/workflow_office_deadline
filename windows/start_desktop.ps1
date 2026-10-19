# Foreground notification center for the logged-in Windows user, not a service.
# Safe -PlanOnly preview for enterprise change review and CI.
[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$DbPath = '',
    [ValidateRange(5,3600)][int]$PollSeconds = 15,
    [switch]$PlanOnly
)
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($DbPath)) {
    $DbPath = Join-Path $Project 'data\workflow.sqlite3'
}
if ([string]::IsNullOrWhiteSpace($Python)) {
    throw 'A permitted Python interpreter is required'
}
# Explicitly no Task Scheduler registration, no Outlook access and no network.
$plan = [ordered]@{
    mode = 'interactive-desktop'
    python = $Python
    database = $DbPath
    poll_seconds = $PollSeconds
    notification_source = 'sqlite-delivered-alerts'
    performs_approvals = $false
    sends_network = $false
}
if ($PlanOnly) {
    $plan | ConvertTo-Json -Compress
    return
}
if (!(Test-Path -LiteralPath $DbPath -PathType Leaf)) {
    throw 'Database not found. First run a synthetic read-only intake and Rust alert cycle.'
}
$env:PYTHONPATH = Join-Path $Project 'python'
& $Python -m edu_workflow.desktop_app --db $DbPath --poll-seconds $PollSeconds
if ($LASTEXITCODE -ne 0) {
    throw "Interactive notification center failed ($LASTEXITCODE). Check Tkinter and signed-in desktop session."
}
