"""Install a small chat control skill for this pet, only when explicitly requested."""
from __future__ import annotations
import json
import os
from pathlib import Path
from pet_common import HERE, config


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    cfg = config()
    name = cfg['id'] + '-control'
    root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
    destination = root / name
    path = destination / 'SKILL.md'
    marker = f'<!-- desktop-pet-control:{cfg["id"]} -->'
    if path.exists() and marker not in path.read_text(encoding='utf-8-sig'):
        raise RuntimeError(f'{destination} is an unrelated skill; choose another pet id.')
    description = f'Control the locally installed {cfg["name"]} Windows desktop pet. Use to open, close, check, enlarge, shrink or resize this pet; 开启桌宠、关闭桌宠、放大、缩小、检查状态。'
    python = ps_quote(HERE / '.venv' / 'Scripts' / 'python.exe')
    control = ps_quote(HERE / 'pet_control.py')
    content = f'''---
name: {name}
description: {json.dumps(description, ensure_ascii=False)}
---

# {cfg['name']} control

{marker}

Control only this installed pet using these absolute paths. Check status when needed; execute the requested reversible control directly. Do not stop other Python processes or change art while handling a control request.

```powershell
& {python} {control} status
& {python} {control} start
& {python} {control} stop
& {python} {control} bigger
& {python} {control} smaller
& {python} {control} size 400
```

`stop` suppresses the current app/standalone session. `start` restores it. `shutdown` also stops the watcher and is for updates/removal. Do not disable login startup merely because the user asks to close the pet.
'''
    destination.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'Control skill installed: {destination}')


if __name__ == '__main__':
    main()
