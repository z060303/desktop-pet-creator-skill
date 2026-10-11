# Windows implementation and commands

## Environment

The template targets Windows 10/11, x64 Python 3.11–3.13 with Tk. The bundled versions were exercised on Windows with Python 3.13; do not claim every OS/Python combination has been tested. Image generation requires a tool that can create/edit raster assets; this skill does not ship API keys. Pillow and the media libraries are downloaded by pip during installation, not included as a binary runtime in the skill.

`scaffold_pet.py` only copies the template and writes a manifest; no startup change or process starts occur at scaffold time. `--demo` adds reproducible geometric sample art. It is useful for testing, not a constraint on user designs.

## Configuration in pet.json

| Field | Meaning |
|---|---|
| `id` | 1–48 lower-case letters/digits, with internal hyphens; installation and shortcut identity |
| `name` | Window title; any user-friendly character name |
| `behavior.mode` | `codex`: follow configured application; `standalone`: independent pet |
| `behavior.process_names` | Exact executable names, case insensitive; used in follow-app mode |
| `behavior.exe_contains` | Optional OR list of path fragments to distinguish desktop Codex from other similarly named processes |
| `music.enabled` | Whether to run live media monitoring; demo still works when false |
| `music.media_keywords` | Substrings identifying Windows media session source IDs |
| `music.process_names` | Exact process names for the per-process output-level fallback |
| `music.peak_threshold` | Default .002, normalized output level |
| `music.silence_hold` | Default 1.25 seconds, prevents chatter during short silent gaps |
| `animation.idle/playing` | Relative PNG paths; frame count and fps as documented in the visual reference |
| `animation.background/foreground` | Optional relative overlay paths; empty string disables |
| `window` | Default310, minimum180, maximum620, step40; customizable |

Default source is NetEase Cloud Music. To support another player, discover its media source/process name and change both matching lists; do not match every system sound by default. Codex installation paths can change, so inspect actual executable paths before changing the follow-app path filter. If a configured app is absent, a running watcher with no visible pet is expected.

## Install and operate

Execute from the generated project folder:

```powershell
# Install and launch; omit -AutoStart if login startup wasn't requested.
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -AutoStart

# Installed paths; expand Documents via the shell, not a hard-coded username.
$petDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'DesktopPets\my-pet'
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" status
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" start
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" stop
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" size 400
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" bigger
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" smaller
```

`install.ps1 -NoLaunch` installs without showing a pet. `-Target <absolute path>` is for a known ordinary-user-visible location or an isolated test. Installing again updates this pet's scripts/assets while retaining settings, and retains previously enabled startup unless explicitly uninstalled. There is no need to modify the Codex installation or require admin privileges.

Add `-ControlSkill` when chat control is requested. It generates `<id>-control` in the configured Codex skill root, using the installed absolute paths. A conflicting unrelated skill is not overwritten.

Drag to move; wheel to scale; double-click to demonstrate for five seconds; right-click to close/scale/demo. Saved size and location persist. `stop` and the pet's close command suppress display for the current owner process token; a new app session or explicit `start` restores it. Standalone mode remains stopped until `start` or a new watcher session at next login. `shutdown` ends the watcher too. `uninstall.ps1` stops this installation and removes only its own startup link, retaining its folder and settings.

## Music status: two different sources

1. Query matching Windows media sessions. If present, use their PLAYING/PAUSED status.
2. If absent, enumerate the target process's audio sessions and read peak output. NetEase clients may not publish media controls; a WASAPI session may stay ACTIVE while paused, so checking State alone is wrong.

The fallback samples every .3 s and holds activity for1.25 s. It may pause on long silent passages or muted output; it is not an exact playback-state API. It currently watches the default output endpoint; a player routed to another device may require endpoint enumeration. Never claim that it reads the song's beat or that silence is always a user pause.

Diagnostics from the installed environment:

```powershell
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_app.py" --list-sessions
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_app.py" --check-assets
# Shut down watcher before a direct preview to avoid the per-pet instance lock.
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_control.py" shutdown
& "$petDir\.venv\Scripts\python.exe" "$petDir\pet_app.py" --demo --duration 5
```

`pet-error.log` records an app startup exception. Inspect it when no window appears; avoid printing private file contents as part of an unrelated report.

## Startup failure investigation

Windows login launches the watcher; follow-app mode shows the pet only after the configured app starts. Check both conditions before reporting a failure.

Verify the shortcut in `[Environment]::GetFolderPath('Startup')`, TargetPath, Arguments and WorkingDirectory; verify interpreter/assets under an ordinary user process, not only from inside a packaged application. Check Windows startup disablement in Task Manager and, if needed, StartupApproved records. Missing AppData files despite apparently successful installation can indicate packaged-app virtualization into private LocalCache. Shared Documents avoids the earlier failure.

If verification uses a temporary scheduled task, make it narrowly scoped, use the ordinary current user context, and remove it after the test. Do not create persistent tasks, elevate or reboot merely for a preview. Report “shortcut verified” separately from “reboot verified”.

## Local chat control skill

When the user requests control from Codex, use `install.ps1 -ControlSkill` or run the installed `make_control_skill.py`. It creates a uniquely named skill such as `moon-cat-control` in the user's configured skills root. It identifies the installed folder and invokes its `.venv/Scripts/python.exe pet_control.py <action>` with fully expanded paths. Use start/stop for normal interaction, shutdown when removing/updating. Never scan and kill all Python processes or another pet's watcher. Uninstall retains this small control skill; remove that specific skill folder too when the user requests complete removal.
