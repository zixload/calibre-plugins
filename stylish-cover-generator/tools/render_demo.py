#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Render one sample cover per preset, without calibre's GUI.

    calibre-debug tools/render_demo.py [output_dir] [artwork.jpg]

If no artwork is given, a synthetic illustration is generated so the presets
can still be compared.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from stylish_cover_generator import presets as presets_mod  # noqa: E402
from stylish_cover_generator.generator import (BookInfo, merged_settings,  # noqa: E402
                                               render_cover)


def synthetic_artwork(width=1400, height=1900, bright=False):
    """A fake illustration: sky gradient, mountains, moon, mist."""
    random.seed(7)
    top = (192, 206, 226) if bright else (36, 30, 58)
    bottom = (238, 232, 220) if bright else (8, 7, 14)
    img = Image.new('RGB', (1, height))
    px = img.load()
    for y in range(height):
        t = y / float(height - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img, 'RGBA')

    moon = (255, 248, 226, 235) if not bright else (255, 255, 255, 220)
    draw.ellipse([width * 0.60, height * 0.10, width * 0.86, height * 0.29],
                 fill=moon)

    for layer, (shade, base) in enumerate((
            ((70, 62, 104), 0.62), ((44, 38, 70), 0.72), ((20, 17, 32), 0.84))):
        if bright:
            shade = tuple(min(255, c + 90) for c in shade)
        points = [(0, height)]
        x = 0
        while x < width:
            points.append((x, height * (base + random.uniform(-0.09, 0.06))))
            x += width // (6 + layer * 3)
        points += [(width, height), (width, height)]
        draw.polygon(points, fill=shade + (255,))

    mist = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    mdraw = ImageDraw.Draw(mist)
    for _ in range(24):
        y = random.uniform(height * 0.55, height * 0.95)
        x = random.uniform(-200, width * 0.9)
        mdraw.ellipse([x, y, x + random.uniform(300, 900),
                       y + random.uniform(30, 90)],
                      fill=(255, 255, 255, 26 if not bright else 60))
    img = Image.alpha_composite(img.convert('RGBA'),
                                mist.filter(ImageFilter.GaussianBlur(24)))
    return img.convert('RGB')


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'samples')
    artwork_path = sys.argv[2] if len(sys.argv) > 2 else None
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    dark = artwork_path or synthetic_artwork()
    bright = artwork_path or synthetic_artwork(bright=True)

    book = BookInfo(title='The Immortal Who Devoured the Heavens',
                    authors='Gu Zhen Ren', series='Reverend Insanity',
                    series_index=3, asian_title='蛊真人')
    short = BookInfo(title='Shadow Slave', authors='Guiltythree',
                     series='Nightmare Spell', series_index=1,
                     asian_title='그림자 노예')

    total = 0.0
    for preset in presets_mod.BUILTIN_PRESETS:
        for label, art, info in (('dark', dark, book), ('bright', bright, short)):
            settings = merged_settings({
                'preset': preset['id'], 'width': 1600, 'height': 2400,
                'asian_enabled': True,
            })
            start = time.time()
            image = render_cover(art, info, settings)
            elapsed = time.time() - start
            total += elapsed
            name = '%s_%s.jpg' % (preset['id'], label)
            image.save(os.path.join(out_dir, name), 'JPEG', quality=90)
            print('%-28s %5.2fs  %s' % (name, elapsed, image.size))
    print('total %.2fs -> %s' % (total, out_dir))
    return 0


if __name__ == '__main__':
    sys.exit(main())
