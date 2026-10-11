param([switch]$Update)
$ErrorActionPreference = 'Stop'
$source = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'desktop-pet-creator'
$root = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex\skills' }
$target = Join-Path $root 'desktop-pet-creator'
if ((Test-Path -LiteralPath $target) -and -not $Update) {
    throw 'The skill is already installed. To update it, run this script with -Update.'
}
New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem -LiteralPath $source | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force }
Write-Output "Installed skill: $target"
Write-Output 'Use $desktop-pet-creator in your next Codex turn. If it does not appear, restart Codex.'
