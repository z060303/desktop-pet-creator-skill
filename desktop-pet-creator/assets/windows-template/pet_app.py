"""A transparent Windows pet with pre-rendered animation and local music status."""
from __future__ import annotations

import argparse
import asyncio
import os
import threading
import time
import tkinter as tk
import traceback
from PIL import Image, ImageTk
from pet_common import CONTROL, HERE, SETTINGS, asset_path, config, read_json, write_json

TRANSPARENT = '#ff00ff'


class PlaybackState:
    def __init__(self):
        self.playing, self.status, self.running = False, '正在连接音乐…', True
        self.lock = threading.Lock()

    def set(self, playing, status):
        with self.lock:
            self.playing, self.status = playing, status

    def get(self):
        with self.lock:
            return self.playing, self.status


class AudioDetector:
    """Use audible peaks: a paused WASAPI session can still report ACTIVE."""
    def __init__(self, music):
        self.music, self.last_sound = music, None

    def sample(self):
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        found, audible = False, False
        names = [name.casefold() for name in self.music['process_names']]
        for session in AudioUtilities.GetAllSessions():
            try:
                if session.Process is None or session.Process.name().casefold() not in names:
                    continue
                found = True
                if session.State == 1:
                    meter = session._ctl.QueryInterface(IAudioMeterInformation)
                    audible |= meter.GetPeakValue() > self.music['peak_threshold']
            except Exception:
                continue
        now = time.monotonic()
        if not found:
            self.last_sound = None
            return False, '未发现目标播放器的音频会话'
        if audible:
            self.last_sound = now
        playing = self.last_sound is not None and now - self.last_sound < self.music['silence_hold']
        return playing, '播放中（音频输出）' if playing else '已暂停或无声'


async def get_media_manager():
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    return await GlobalSystemMediaTransportControlsSessionManager.request_async()


def media_worker(state, music):
    import comtypes
    comtypes.CoInitialize()
    manager, next_retry = None, 0
    detector = AudioDetector(music)
    try:
        while state.running:
            try:
                if manager is None and time.monotonic() >= next_retry:
                    try:
                        manager = asyncio.run(get_media_manager())
                    except Exception:
                        next_retry = time.monotonic() + 5
                keywords = [word.casefold() for word in music['media_keywords']]
                sessions = [s for s in manager.get_sessions()
                            if any(word in s.source_app_user_model_id.casefold() for word in keywords)] if manager else []
                if sessions:
                    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
                    playing = any(s.get_playback_info().playback_status == Status.PLAYING for s in sessions)
                    state.set(playing, '播放中' if playing else '已暂停')
                else:
                    state.set(*detector.sample())
            except Exception as exc:
                manager = None
                state.set(False, f'音乐检测：{type(exc).__name__}；可查看诊断命令')
                next_retry = time.monotonic() + 5
            time.sleep(0.3)
    finally:
        comtypes.CoUninitialize()


def load_strip(name, count, side=None):
    with Image.open(asset_path(name)) as source:
        image = source.convert('RGBA')
    side = side or image.height
    if image.size != (side * count, side):
        raise ValueError(f'{name}: expected {count} square frame(s), side {side}')
    return [image.crop((i * side, 0, (i + 1) * side, side)) for i in range(count)]


def source_frames(cfg):
    animation = cfg['animation']
    idle = load_strip(animation['idle'], 1)
    side = idle[0].height
    playing = load_strip(animation['playing'], animation['frames'], side)
    for key, behind in [('background', True), ('foreground', False)]:
        if not animation.get(key):
            continue
        with Image.open(asset_path(animation[key])) as image:
            count = image.width // side
        if count not in (1, len(playing)):
            raise ValueError(f'{key} must be one square or match the animation frame count')
        layers = load_strip(animation[key], count, side)
        result = []
        for i, frame in enumerate(playing):
            layer = layers[i % count]
            result.append(Image.alpha_composite(layer, frame) if behind else Image.alpha_composite(frame, layer))
        playing = result
    return idle, playing


class DesktopPet:
    def __init__(self, root, state, cfg, size):
        self.root, self.state, self.cfg, self.size = root, state, cfg, size
        self.drag_origin, self.manual_until, self.last_settings_check = None, 0, 0
        self.sources = source_frames(cfg)
        self.frames = self.render_frames(size)
        self.showing_playing, self.current_frame = False, 0
        root.title(cfg['name'])
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT)
        root.attributes('-topmost', True)
        root.wm_attributes('-transparentcolor', TRANSPARENT)
        saved = read_json(SETTINGS)
        x = int(saved.get('x', root.winfo_screenwidth() - size - 38))
        y = int(saved.get('y', root.winfo_screenheight() - size - 85))
        x, y = self.clamp_position(x, y)
        root.geometry(f'{size}x{size}+{x}+{y}')
        self.canvas = tk.Canvas(root, width=size, height=size, bg=TRANSPARENT, highlightthickness=0)
        self.canvas.pack()
        self.image_item = self.canvas.create_image(0, 0, image=self.frames[0][0], anchor='nw')
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label='正在连接…', state='disabled')
        self.menu.add_separator()
        self.menu.add_command(label='演示动作 5 秒', command=self.demo)
        self.menu.add_command(label='放大', command=lambda: self.change_size(cfg['window']['step']))
        self.menu.add_command(label='缩小', command=lambda: self.change_size(-cfg['window']['step']))
        self.menu.add_command(label='恢复默认大小', command=lambda: self.set_size(cfg['window']['default_size']))
        self.menu.add_command(label='关闭桌宠', command=self.close)
        self.canvas.bind('<ButtonPress-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.end_drag)
        self.canvas.bind('<Double-Button-1>', self.demo)
        self.canvas.bind('<MouseWheel>', self.wheel)
        self.canvas.bind('<Button-3>', self.show_menu)
        root.bind('<Escape>', lambda _: self.close())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.tick()

    def clamp_position(self, x, y):
        return max(0, min(x, self.root.winfo_screenwidth() - 60)), max(0, min(y, self.root.winfo_screenheight() - 60))

    def render_frames(self, size):
        result = []
        for sources in self.sources:
            frames = []
            for source in sources:
                frame = source.resize((size, size), Image.Resampling.LANCZOS)
                frame.putalpha(frame.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
                frames.append(ImageTk.PhotoImage(frame))
            result.append(frames)
        return result

    def save_settings(self):
        saved = read_json(SETTINGS)
        saved.update(size=self.size, x=self.root.winfo_x(), y=self.root.winfo_y())
        write_json(SETTINGS, saved)

    def start_drag(self, event):
        self.drag_origin = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def drag(self, event):
        if self.drag_origin:
            x, y = event.x_root - self.drag_origin[0], event.y_root - self.drag_origin[1]
            self.root.geometry(f'+{x}+{y}')

    def end_drag(self, _event=None):
        self.drag_origin = None
        self.save_settings()

    def demo(self, _event=None):
        self.manual_until = time.monotonic() + 5

    def wheel(self, event):
        self.change_size(self.cfg['window']['step'] * (1 if event.delta > 0 else -1))
        return 'break'

    def change_size(self, amount):
        self.set_size(self.size + amount)

    def set_size(self, requested):
        window = self.cfg['window']
        size = max(window['min_size'], min(window['max_size'], int(requested)))
        if size == self.size:
            return
        center = (self.root.winfo_x() + self.size // 2, self.root.winfo_y() + self.size // 2)
        self.size, self.frames = size, self.render_frames(size)
        self.canvas.configure(width=size, height=size)
        self.canvas.itemconfigure(self.image_item, image=self.frames[int(self.showing_playing)][self.current_frame])
        x, y = self.clamp_position(center[0] - size // 2, center[1] - size // 2)
        self.root.geometry(f'{size}x{size}+{x}+{y}')
        self.save_settings()

    def show_menu(self, event):
        self.menu.entryconfigure(0, label='音乐：' + self.state.get()[1])
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def tick(self):
        now = time.monotonic()
        if now - self.last_settings_check > 0.6:
            self.last_settings_check = now
            size = read_json(SETTINGS).get('size', self.size)
            if isinstance(size, int) and size != self.size:
                self.set_size(size)
        playing = self.state.get()[0] or now < self.manual_until
        frame = int(now * self.cfg['animation']['fps']) % len(self.frames[1]) if playing else 0
        if playing != self.showing_playing or frame != self.current_frame:
            self.showing_playing, self.current_frame = playing, frame
            self.canvas.itemconfigure(self.image_item, image=self.frames[int(playing)][frame])
        if self.state.running:
            self.root.after(40, self.tick)

    def close(self):
        owner = os.environ.get('DESKTOP_PET_OWNER')
        if owner:
            write_json(CONTROL, {'suppressed_token': owner})
        self.state.running = False
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='自定义 Windows 桌宠')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--size', type=int)
    parser.add_argument('--duration', type=float, help='自动结束预览的秒数')
    parser.add_argument('--check-assets', action='store_true')
    parser.add_argument('--list-sessions', action='store_true')
    args = parser.parse_args()
    cfg = config()
    if args.check_assets:
        idle, playing = source_frames(cfg)
        print(f'素材可加载：idle={len(idle)}, playing={len(playing)}, size={idle[0].size}')
        return
    if args.list_sessions:
        import comtypes
        comtypes.CoInitialize()
        try:
            try:
                manager = asyncio.run(get_media_manager())
                for session in manager.get_sessions():
                    print(session.source_app_user_model_id, session.get_playback_info().playback_status.name)
            except Exception as exc:
                print('Windows 媒体接口：', type(exc).__name__)
            print('目标音频输出：', AudioDetector(cfg['music']).sample()[1])
        finally:
            comtypes.CoUninitialize()
        return
    from pet_watch import lock_instance
    handle, kernel = lock_instance('App')
    if handle is None:
        return
    state = PlaybackState()
    try:
        if args.demo:
            state.set(True, '演示播放中')
        elif cfg['music']['enabled']:
            threading.Thread(target=media_worker, args=(state, cfg['music']), daemon=True).start()
        else:
            state.set(False, '未开启音乐联动；双击可演示动作')
        root = tk.Tk()
        window = cfg['window']
        size = args.size or read_json(SETTINGS).get('size', window['default_size'])
        size = max(window['min_size'], min(window['max_size'], int(size)))
        pet = DesktopPet(root, state, cfg, size)
        if args.duration:
            root.after(int(args.duration * 1000), pet.close)
        root.mainloop()
    finally:
        state.running = False
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (HERE / 'pet-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise
