"""Single watcher per pet installation. Watch the chosen app or run standalone."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time

from pet_common import (CONTROL, HERE, INSTANCE, PET_PID, WATCHER_PID,
                        owner_token, read_json, write_json)


def lock_instance(kind='Watcher'):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateMutexW(None, False, 'Local\\DesktopPet-' + kind + '-' + INSTANCE)
    if not handle or ctypes.get_last_error() == 183:
        if handle:
            kernel.CloseHandle(handle)
        return None, kernel
    return handle, kernel


def stop_child(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)
    PET_PID.unlink(missing_ok=True)
    return None


def main():
    handle, kernel = lock_instance()
    if handle is None:
        return
    WATCHER_PID.write_text(str(os.getpid()), encoding='ascii')
    state = read_json(CONTROL)
    state.pop('shutdown', None)
    # An explicit stop lasts for this Windows/app session, not forever.
    if state.get('suppressed_token') == 'standalone':
        state.pop('suppressed_token')
    write_json(CONTROL, state)
    child = None
    try:
        while True:
            state = read_json(CONTROL)
            if state.get('shutdown'):
                break
            token = owner_token()
            if token is None or state.get('suppressed_token') == token:
                child = stop_child(child)
            elif child is None or child.poll() is not None:
                environment = dict(os.environ, DESKTOP_PET_OWNER=token)
                child = subprocess.Popen([sys.executable, str(HERE / 'pet_app.py')],
                                         cwd=HERE, env=environment,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                PET_PID.write_text(str(child.pid), encoding='ascii')
            time.sleep(0.5)
    finally:
        stop_child(child)
        WATCHER_PID.unlink(missing_ok=True)
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    main()
