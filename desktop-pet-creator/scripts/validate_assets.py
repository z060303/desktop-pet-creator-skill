"""Validate config and transparent PNG frames before installation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from PIL import Image


def validate(folder):
    folder = Path(folder).resolve()
    cfg = json.loads((folder / 'pet.json').read_text(encoding='utf-8-sig'))
    if cfg.get('schema_version') != 1:
        raise ValueError('schema_version 必须为 1')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', cfg['id']) or len(cfg['id']) > 48:
        raise ValueError('角色 id 格式错误')
    behavior = cfg['behavior']
    if behavior['mode'] not in ('codex', 'standalone'):
        raise ValueError('mode 必须为 codex 或 standalone')
    if behavior['mode'] == 'codex' and not behavior['process_names']:
        raise ValueError('跟随应用模式需要 process_names')
    animation = cfg['animation']
    count = animation['frames']
    if not isinstance(count, int) or not 2 <= count <= 32 or not 1 <= animation['fps'] <= 30:
        raise ValueError('帧数应为 2–32，fps 应为 1–30')
    window = cfg['window']
    if not 80 <= window['min_size'] <= window['default_size'] <= window['max_size'] <= 1200 or window['step'] <= 0:
        raise ValueError('窗口大小或缩放步长错误')
    music = cfg['music']
    if not 0 < music['peak_threshold'] < 1 or not 0 <= music['silence_hold'] <= 10:
        raise ValueError('音频检测参数错误')
    if music['enabled'] and not (music['media_keywords'] or music['process_names']):
        raise ValueError('音乐联动需要目标播放器关键词或进程名')
    side, rows = None, []
    for key in ['idle', 'playing', 'background', 'foreground']:
        name = animation.get(key)
        if not name:
            if key in ('idle', 'playing'):
                raise ValueError(f'缺少 {key} 素材')
            continue
        path = (folder / name).resolve()
        if not path.is_relative_to(folder):
            raise ValueError('素材路径不能超出桌宠目录')
        with Image.open(path) as image:
            if image.format != 'PNG' or image.mode != 'RGBA':
                raise ValueError(f'{name} 必须为 RGBA PNG')
            if key == 'idle':
                side = image.height
                if image.width != side or not 64 <= side <= 2048:
                    raise ValueError('idle.png 必须为 64–2048 像素的正方形')
            expected = [1] if key == 'idle' else [count] if key == 'playing' else [1, count]
            if image.height != side or image.width not in [side * n for n in expected]:
                raise ValueError(f'{name} 的尺寸与帧数不匹配')
            for i in range(image.width // side):
                alpha = image.crop((i * side, 0, (i + 1) * side, side)).getchannel('A')
                low, high = alpha.getextrema()
                if low != 0 or high == 0:
                    raise ValueError(f'{name} 第 {i+1} 帧需要透明背景且不能全透明')
            rows.append(f'{key}: {image.width} × {image.height}')
    return rows


def main():
    parser = argparse.ArgumentParser(description='检查桌宠透明素材与配置')
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        rows = validate(args.folder)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'检查失败：{exc}\n')
    print('检查通过\n' + '\n'.join(rows))


if __name__ == '__main__':
    main()
