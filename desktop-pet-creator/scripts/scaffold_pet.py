"""Create an isolated Windows pet project from this skill's tested template."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil

SKILL = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='创建自定义 Windows 桌宠项目')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--id', required=True, help='英文小写与短横线，例如 moon-cat')
    parser.add_argument('--name', default='我的桌宠')
    parser.add_argument('--mode', choices=['codex', 'standalone'], default='codex')
    parser.add_argument('--demo', action='store_true', help='复制可运行的几何音乐机器人示例')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.id) or len(args.id) > 48:
        parser.error('--id 需要 1–48 个小写字母、数字或短横线，且不能以短横线开头或结尾')
    target = args.output.resolve()
    if target.exists() and any(target.iterdir()):
        parser.error('输出文件夹已有内容，请选择空文件夹，避免覆盖已有桌宠')
    shutil.copytree(SKILL / 'assets' / 'windows-template', target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    cfg_path = target / 'pet.json'
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    cfg.update(id=args.id, name=args.name)
    cfg['behavior']['mode'] = args.mode
    if args.demo:
        for path in (SKILL / 'assets' / 'demo').glob('*.png'):
            shutil.copy2(path, target / path.name)
        cfg['animation'].update(background='waves.png', foreground='headphones.png')
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'已创建：{target}')
    print('下一步：检查素材、预览，再按照用户要求安装。' if args.demo else '下一步：制作 idle.png 与 playing.png，并验证素材。')


if __name__ == '__main__':
    main()
