"""Configuration and local control shared by the Windows desktop pet."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import psutil

HERE = Path(__file__).resolve().parent
CONFIG = HERE / 'pet.json'
SETTINGS = HERE / 'pet-settings.json'
CONTROL = HERE / 'control-state.json'
PET_PID = HERE / 'pet.pid'
WATCHER_PID = HERE / 'watcher.pid'
INSTANCE = hashlib.sha256(str(HERE).casefold().encode()).hexdigest()[:20]


def read_json(path, default=None):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else (default or {})
    except (OSError, ValueError):
        return default or {}


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def config():
    value = read_json(CONFIG)
    if value.get('schema_version') != 1:
        raise ValueError('pet.json needs schema_version: 1')
    return value


def asset_path(name):
    path = (HERE / name).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError('Asset path must stay inside the pet directory')
    return path


def set_size(requested):
    window = config()['window']
    size = max(window['min_size'], min(window['max_size'], int(requested)))
    settings = read_json(SETTINGS)
    settings['size'] = size
    write_json(SETTINGS, settings)
    return size


def owner_token():
    behavior = config()['behavior']
    if behavior['mode'] == 'standalone':
        return 'standalone'
    names = [name.casefold() for name in behavior['process_names']]
    fragments = [part.replace('/', '\\').casefold() for part in behavior.get('exe_contains', [])]
    found = []
    for process in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
        try:
            info = process.info
            exe = (info['exe'] or '').replace('/', '\\').casefold()
            if (info['name'] or '').casefold() in names and (not fragments or any(part in exe for part in fragments)):
                found.append((info['pid'], info['create_time']))
        except psutil.Error:
            continue
    if not found:
        return None
    pid, created = min(found)
    return f'{pid}:{created}'


def recorded_process(path, script_name):
    try:
        process = psutil.Process(int(path.read_text(encoding='ascii')))
        expected = (HERE / script_name).resolve()
        if process.is_running() and any(Path(arg).resolve() == expected for arg in process.cmdline()):
            return process
    except (OSError, ValueError, psutil.Error):
        pass
    return None


def python_background():
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return str(pythonw if pythonw.exists() else sys.executable)
