"""Reproducible geometric fixture, not a style template for user characters."""
import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw

SIDE, COUNT = 384, 8
INK = '#393144'


def character(phase=None):
    image = Image.new('RGBA', (SIDE, SIDE))
    d = ImageDraw.Draw(image)
    # Static head, body and feet: only the left forearm waves in this fixture.
    d.line((192, 82, 192, 57), fill=INK, width=8)
    d.ellipse((182, 44, 202, 64), fill='#f6bdcf', outline=INK, width=5)
    d.rounded_rectangle((108, 90, 276, 222), radius=48, fill='#ddd3ec', outline=INK, width=7)
    d.rounded_rectangle((124, 123, 260, 191), radius=25, fill='#ffefce', outline=INK, width=5)
    for x in (158, 226):
        d.ellipse((x-7, 147, x+7, 167), fill=INK)
    d.arc((177, 160, 207, 184), 0, 180, fill=INK, width=4)
    d.rounded_rectangle((140, 219, 244, 309), radius=24, fill='#b8dacf', outline=INK, width=7)
    d.ellipse((177, 248, 207, 278), fill='#ffefce', outline=INK, width=4)
    for x in (160, 224):
        d.rounded_rectangle((x-18, 296, x+18, 336), radius=12, fill='#ddd3ec', outline=INK, width=6)
    d.line((245, 240, 275, 282), fill=INK, width=21)
    d.line((245, 240, 275, 282), fill='#ddd3ec', width=11)
    d.ellipse((264, 271, 288, 295), fill='#ddd3ec', outline=INK, width=5)
    shoulder = (138, 241)
    elbow = (111, 258)
    angle = -1.85 + (0.24 * math.sin(phase) if phase is not None else 0)
    hand = (elbow[0] + 39 * math.cos(angle), elbow[1] + 39 * math.sin(angle))
    d.line([shoulder, elbow, hand], fill=INK, width=23, joint='curve')
    d.line([shoulder, elbow, hand], fill='#ddd3ec', width=13, joint='curve')
    d.ellipse((hand[0]-12, hand[1]-12, hand[0]+12, hand[1]+12), fill='#ddd3ec', outline=INK, width=5)
    return image


def headphones():
    image = Image.new('RGBA', (SIDE, SIDE))
    d = ImageDraw.Draw(image)
    d.arc((91, 76, 293, 229), 185, 355, fill=INK, width=18)
    d.arc((91, 76, 293, 229), 185, 355, fill='#f8ccdf', width=11)
    for left, right in [(94, 114), (270, 290)]:
        d.rounded_rectangle((left-4, 136, right+4, 190), radius=11, fill='#595361', outline=INK, width=4)
        d.rounded_rectangle((left, 134, right, 186), radius=9, fill='#f8ccdf', outline=INK, width=4)
        d.line((left+5, 144, left+5, 172), fill='#fff0f7', width=3)
    return image


def waves(phase):
    image = Image.new('RGBA', (SIDE, SIDE))
    d = ImageDraw.Draw(image)
    for i, color in enumerate(['#ed97bd', '#b39ade', '#dfb75f', '#81c8b4']):
        for left in (True, False):
            x0 = 38 if left else 309
            points = [(x0 + j * 1.4, 104 + i * 22 + math.sin(j/5 + phase + i) * 5) for j in range(25)]
            d.line(points, fill=color, width=4)
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'assets' / 'demo')
    parser.add_argument('--preview', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    character().save(args.output / 'idle.png')
    strip = Image.new('RGBA', (SIDE * COUNT, SIDE))
    wave_strip = Image.new('RGBA', strip.size)
    headset = headphones()
    preview = []
    for i in range(COUNT):
        phase = i * 2 * math.pi / COUNT
        frame, wave = character(phase), waves(phase)
        strip.paste(frame, (i * SIDE, 0))
        wave_strip.paste(wave, (i * SIDE, 0))
        composite = Image.alpha_composite(Image.alpha_composite(wave, frame), headset)
        board = Image.new('RGBA', composite.size, '#faf8f4')
        board.alpha_composite(composite)
        preview.append(board.convert('RGB'))
    strip.save(args.output / 'playing.png')
    wave_strip.save(args.output / 'waves.png')
    headset.save(args.output / 'headphones.png')
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        preview[0].save(args.preview, save_all=True, append_images=preview[1:], duration=85, loop=0)
    print(f'Demo assets: {args.output}')


if __name__ == '__main__':
    main()
