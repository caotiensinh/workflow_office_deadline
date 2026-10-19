[CmdletBinding()]
param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$Project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location $Project
try {
  $args = @('-m','PyInstaller','--onefile','--windowed','--clean','--noconfirm','--name','EDUNotifications','--paths',(Join-Path $Project 'python'),(Join-Path $PSScriptRoot 'notification_entry.py'))
  & $Python @args
  if ($LASTEXITCODE -ne 0) { throw 'PyInstaller packaging failed' }
  $file = Join-Path $Project 'dist\EDUNotifications.exe'
  if (!(Test-Path -LiteralPath $file -PathType Leaf)) { throw 'Desktop EXE not produced' }
  Write-Host ('Unsigned desktop EXE (IT review required): ' + $file)
  Write-Host ('SHA256: ' + (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash)
} finally {
  Pop-Location
}
