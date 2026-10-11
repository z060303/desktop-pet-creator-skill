param(
    [switch]$AutoStart,
    [switch]$ControlSkill,
    [switch]$NoLaunch,
    [string]$Target
)
$ErrorActionPreference = 'Stop'
$source = Split-Path -Parent $MyInvocation.MyCommand.Path
$config = Get-Content -LiteralPath (Join-Path $source 'pet.json') -Raw -Encoding utf8 | ConvertFrom-Json
if ($config.id -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$' -or $config.id.Length -gt 48) {
    throw 'pet.json id must be a short lower-case identifier.'
}
if (-not $Target) {
    # A packaged desktop app may virtualize AppData. Documents is shared with login processes.
    $Target = Join-Path ([Environment]::GetFolderPath('MyDocuments')) ('DesktopPets\' + $config.id)
}
$Target = [IO.Path]::GetFullPath($Target)
if ($Target -eq [IO.Path]::GetFullPath($source)) { throw 'Installation target must differ from source.' }
$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python -c "import sys,struct; assert sys.platform=='win32' and (3,11)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')==8, 'Use Windows x64 Python 3.11-3.13'"
if ($LASTEXITCODE -ne 0) { throw 'Python environment check failed.' }
$installedPython = Join-Path $Target '.venv\Scripts\python.exe'
$oldControl = Join-Path $Target 'pet_control.py'
if ((Test-Path -LiteralPath $installedPython) -and (Test-Path -LiteralPath $oldControl)) {
    & $installedPython $oldControl shutdown
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the existing installation.' }
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
$files = @('pet_common.py','pet_app.py','pet_watch.py','pet_control.py','make_control_skill.py','pet.json','requirements.txt','start.cmd','uninstall.ps1')
$files += @($config.animation.idle, $config.animation.playing, $config.animation.background, $config.animation.foreground) | Where-Object { $_ }
foreach ($name in ($files | Select-Object -Unique)) {
    $sourceFile = [IO.Path]::GetFullPath((Join-Path $source $name))
    $targetFile = [IO.Path]::GetFullPath((Join-Path $Target $name))
    if (-not $sourceFile.StartsWith($source.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not $targetFile.StartsWith($Target.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Asset path must stay inside its pet directory.'
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetFile) | Out-Null
    Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
}
if (-not (Test-Path -LiteralPath $installedPython)) {
    & $python -m venv (Join-Path $Target '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Creating the pet environment failed.' }
}
& $installedPython -m pip install --disable-pip-version-check -r (Join-Path $Target 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Installing dependencies failed; check network and Python version.' }
& $installedPython (Join-Path $Target 'pet_app.py') --check-assets
if ($LASTEXITCODE -ne 0) { throw 'The character assets are incomplete or malformed.' }
if ($ControlSkill) {
    & $installedPython (Join-Path $Target 'make_control_skill.py')
    if ($LASTEXITCODE -ne 0) { throw 'Creating the local chat control skill failed.' }
}
$pythonw = Join-Path $Target '.venv\Scripts\pythonw.exe'
$watcher = Join-Path $Target 'pet_watch.py'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) ('Desktop Pet - ' + $config.id + '.lnk')
if ($AutoStart) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = '"' + $watcher + '"'
    $shortcut.WorkingDirectory = $Target
    $shortcut.Description = 'Custom desktop pet: ' + $config.name
    $shortcut.Save()
}
# Without AutoStart, retain a previously enabled login shortcut during updates.
if (-not $NoLaunch) {
    & $installedPython (Join-Path $Target 'pet_control.py') start
    if ($LASTEXITCODE -ne 0) { throw 'Starting the desktop pet failed.' }
}
Write-Output "Installed: $Target"
Write-Output "Login startup: $(Test-Path -LiteralPath $shortcutPath)"
Write-Output 'Drag to move; scroll to resize; double-click to demo; right-click for controls.'
