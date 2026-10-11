"""Windows acceptance test in a temporary project; no startup changes or user pet writes.

Run with a Python environment containing the template's requirements:
    python tests/smoke.py
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'desktop-pet-creator'


def command(*args):
    result = subprocess.run([sys.executable, *map(str, args)], capture_output=True,
                            text=True, encoding='utf-8', env=dict(os.environ, PYTHONUTF8='1'), timeout=60)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout


def wait_for(predicate, label, timeout=8):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(0.1)
    raise AssertionError('Timed out: ' + label)


def gui_check(app, common):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    state = app.PlaybackState()
    pet = app.DesktopPet(root, state, common.config(), 180)

    def pump():
        until = time.monotonic() + .75
        while time.monotonic() < until:
            root.update()
            time.sleep(.015)

    try:
        pump()
        assert not pet.showing_playing and pet.current_frame == 0
        assert pet.sources[0][0].getpixel((106, 150))[3] == 0
        assert pet.sources[1][0].getpixel((106, 150))[3] > 0, 'Headphone overlay missing'
        state.set(True, 'test playing')
        pump()
        assert pet.showing_playing
        common.set_size(400)
        pump()
        assert pet.size == 400, 'External chat resize not reflected in GUI'
        state.set(False, 'test paused')
        pump()
        assert not pet.showing_playing and pet.current_frame == 0
        assert pet.canvas.itemcget(pet.image_item, 'image') == str(pet.frames[0][0])
        pet.demo()
        pump()
        assert pet.showing_playing
        pet.manual_until = 0
        pump()
        assert not pet.showing_playing
        pet.change_size(10000)
        assert pet.size == common.config()['window']['max_size']
        pet.change_size(-10000)
        assert pet.size == common.config()['window']['min_size']
        pet.start_drag(SimpleNamespace(x_root=root.winfo_x()+20, y_root=root.winfo_y()+20))
        pet.drag(SimpleNamespace(x_root=200, y_root=200))
        pump()
        pet.end_drag()
        assert common.read_json(common.SETTINGS)['x'] == root.winfo_x()
        assert common.read_json(common.SETTINGS)['size'] == pet.size
    finally:
        pet.close()
    print('PASS GUI idle/playing/paused, active-only overlay, external resize, demo, bounds, drag/settings')


def audio_check(app):
    import comtypes
    comtypes.CoInitialize()
    try:
        peak = [0.0]
        meter = SimpleNamespace(GetPeakValue=lambda: peak[0])
        session = SimpleNamespace(Process=SimpleNamespace(name=lambda: 'cloudmusic.exe'),
                                  State=1, _ctl=SimpleNamespace(QueryInterface=lambda _: meter))
        detector = app.AudioDetector({'process_names': ['cloudmusic.exe'], 'peak_threshold': .002, 'silence_hold': 1.25})
        with patch('pycaw.pycaw.AudioUtilities.GetAllSessions', return_value=[session]):
            with patch.object(app.time, 'monotonic', return_value=100):
                assert not detector.sample()[0], 'ACTIVE-but-silent must not mean playing'
                peak[0] = .1
                assert detector.sample()[0]
            peak[0] = 0
            with patch.object(app.time, 'monotonic', return_value=100.5):
                assert detector.sample()[0]
            with patch.object(app.time, 'monotonic', return_value=102):
                assert not detector.sample()[0]
        with patch('pycaw.pycaw.AudioUtilities.GetAllSessions', return_value=[]):
            assert not detector.sample()[0]
    finally:
        comtypes.CoUninitialize()
    print('PASS audio-peak fallback: active silence, play, hold, pause, absent player (simulated)')


def watcher_check(folder, common):
    owner_dir = folder / 'owner-env'
    command('-m', 'venv', '--without-pip', owner_dir)
    owner_python = owner_dir / 'Scripts' / 'python.exe'
    cfg = common.config()
    cfg['behavior'].update(mode='codex', process_names=['python.exe'], exe_contains=[str(owner_dir)])
    cfg['music']['enabled'] = False
    common.write_json(common.CONFIG, cfg)
    common.write_json(common.CONTROL, {})
    watcher = subprocess.Popen([sys.executable, str(folder / 'pet_watch.py')], creationflags=subprocess.CREATE_NO_WINDOW)
    owners = []
    pet = lambda: common.recorded_process(common.PET_PID, 'pet_app.py')
    try:
        wait_for(lambda: common.recorded_process(common.WATCHER_PID, 'pet_watch.py'), 'watcher start')
        time.sleep(.7)
        assert pet() is None, 'Pet visible without owner'
        duplicate = subprocess.run([sys.executable, str(folder / 'pet_watch.py')], timeout=5)
        assert duplicate.returncode == 0, 'Duplicate watcher should exit cleanly'
        owner = subprocess.Popen([str(owner_python), '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
        owners.append(owner)
        wait_for(pet, 'owner starts pet')
        command(folder / 'pet_control.py', 'stop')
        assert pet() is None
        time.sleep(.8)
        assert pet() is None, 'Suppressed pet reopened in same owner session'
        command(folder / 'pet_control.py', 'start')
        wait_for(pet, 'explicit start')
        owner.terminate()
        owner.wait(timeout=5)
        wait_for(lambda: pet() is None, 'owner exit hides pet')
        next_owner = subprocess.Popen([str(owner_python), '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
        owners.append(next_owner)
        wait_for(pet, 'new owner session')
        command(folder / 'pet_control.py', 'stop')
        next_owner.terminate()
        next_owner.wait(timeout=5)
        third_owner = subprocess.Popen([str(owner_python), '-c', 'import time; time.sleep(60)'], creationflags=subprocess.CREATE_NO_WINDOW)
        owners.append(third_owner)
        wait_for(pet, 'new session clears suppression')
        command(folder / 'pet_control.py', 'shutdown')
        watcher.wait(timeout=5)
        assert pet() is None
    finally:
        for owner in owners:
            if owner.poll() is None:
                owner.terminate()
                owner.wait(timeout=5)
        if watcher.poll() is None:
            command(folder / 'pet_control.py', 'shutdown')
            watcher.wait(timeout=5)
    print('PASS watcher absent/present/exit/new session, duplicate mutex, manual suppression/start/shutdown')


def main():
    if sys.platform != 'win32':
        raise SystemExit('This integration test requires Windows.')
    with tempfile.TemporaryDirectory(prefix='desktop-pet-skill-') as temporary:
        folder = Path(temporary) / 'test-pet'
        command(SKILL / 'scripts' / 'scaffold_pet.py', '--output', folder, '--id', 'acceptance-test', '--mode', 'standalone', '--demo')
        command(SKILL / 'scripts' / 'validate_assets.py', folder)
        command(folder / 'pet_app.py', '--check-assets')
        # Confirm re-scaffolding refuses to overwrite an existing project.
        duplicate = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'scaffold_pet.py'), '--output', str(folder), '--id', 'other'], capture_output=True)
        assert duplicate.returncode != 0
        sys.path.insert(0, str(folder))
        import pet_common as common
        import pet_app as app
        gui_check(app, common)
        audio_check(app)
        watcher_check(folder, common)
        # Also run the installed runtime's actual media diagnostics, without altering playback.
        print(command(folder / 'pet_app.py', '--list-sessions').strip())
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
