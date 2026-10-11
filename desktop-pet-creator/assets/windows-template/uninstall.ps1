$ErrorActionPreference = 'Stop'
$target = Split-Path -Parent $MyInvocation.MyCommand.Path
$config = Get-Content -LiteralPath (Join-Path $target 'pet.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($config.id -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') { throw 'Invalid pet id.' }
$python = Join-Path $target '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $python) {
    & $python (Join-Path $target 'pet_control.py') shutdown
}
$shortcut = Join-Path ([Environment]::GetFolderPath('Startup')) ('Desktop Pet - ' + $config.id + '.lnk')
if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut }
Write-Output 'Stopped this pet and disabled its login startup. Character files and settings are retained.'
Write-Output "You may delete this folder manually: $target"
