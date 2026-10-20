# Build an unsigned, self-contained, consent-first fictional Windows UAT app.
# No installation, registry, Outlook, mail or actual Startup mutation.
[CmdletBinding()]
param([string]$Python='python')
$ErrorActionPreference='Stop'
$Project=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location $Project
try {
  $entry=Join-Path $PSScriptRoot 'field_uat_entry.py'
  $args=@('-m','PyInstaller','--onefile','--windowed','--clean','--noconfirm',
          '--name','EDUFieldUAT','--paths',(Join-Path $Project 'python'),$entry)
  & $Python @args
  if ($LASTEXITCODE -ne 0) { throw 'Field UAT EXE packaging failed' }
  $exe=Join-Path $Project 'dist\EDUFieldUAT.exe'
  if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Field UAT executable missing' }
  Write-Host "W8_UAT_UNSIGNED_SHA256=$((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash)"
} finally {
  Pop-Location
}
