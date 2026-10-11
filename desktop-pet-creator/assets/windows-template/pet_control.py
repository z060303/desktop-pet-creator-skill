"""Chat-friendly controls; never stop unrelated Python or desktop pet processes."""
from __future__ import annotations
import argparse
import json
import subprocess
import time
from pet_common import (CONTROL, HERE, PET_PID, SETTINGS, WATCHER_PID, config,
                        owner_token, python_background, read_json,
                        recorded_process, set_size, write_json)


def main():
    parser = argparse.ArgumentParser(description='桌宠控制')
    parser.add_argument('action', choices=['start', 'stop', 'shutdown', 'status', 'bigger', 'smaller', 'size'])
    parser.add_argument('pixels', type=int, nargs='?')
    args = parser.parse_args()
    cfg = config()
    window = cfg['window']
    watcher = recorded_process(WATCHER_PID, 'pet_watch.py')
    if args.action in ('bigger', 'smaller', 'size'):
        if args.action == 'size' and args.pixels is None:
            parser.error('size 需要像素值，例如 size 400')
        current = read_json(SETTINGS).get('size', window['default_size'])
        requested = args.pixels if args.action == 'size' else int(current) + window['step'] * (1 if args.action == 'bigger' else -1)
        print(f'桌宠大小：{set_size(requested)} 像素')
    elif args.action == 'start':
        write_json(CONTROL, {})
        if watcher is None:
            subprocess.Popen([python_background(), str(HERE / 'pet_watch.py')], cwd=HERE,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        print('已开启；跟随应用模式下，要打开对应应用才会显示。')
    elif args.action in ('stop', 'shutdown'):
        value = {'shutdown': True} if args.action == 'shutdown' else {'suppressed_token': owner_token()}
        write_json(CONTROL, value)
        for _ in range(40):
            if recorded_process(PET_PID, 'pet_app.py') is None and (args.action != 'shutdown' or recorded_process(WATCHER_PID, 'pet_watch.py') is None):
                break
            time.sleep(0.1)
        print('已关闭桌宠和监视器。' if args.action == 'shutdown' else '本次会话已关闭桌宠；可以随时重新开启。')
    else:
        print(json.dumps({'name': cfg['name'], 'mode': cfg['behavior']['mode'],
                          'owner': owner_token(), 'watcher': bool(watcher),
                          'pet': bool(recorded_process(PET_PID, 'pet_app.py')),
                          'size': read_json(SETTINGS).get('size', window['default_size']),
                          'control': read_json(CONTROL)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
