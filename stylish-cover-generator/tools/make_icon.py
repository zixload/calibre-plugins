#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regenerate stylish_cover_generator/images/icon.png.

Run it with calibre's own python so Pillow is available:

    calibre-debug tools/make_icon.py
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'stylish_cover_generator', 'images', 'icon.png')


def vertical_gradient(size, top, bottom):
    strip = Image.new('RGB', (1, size[1]))
    px = strip.load()
    for y in range(size[1]):
        t = y / float(max(1, size[1] - 1))
        px[0, y] = tuple(int(round(top[i] + (bottom[i] - top[i]) * t))
                         for i in range(3))
    return strip.resize(size, Image.Resampling.LANCZOS)


def star(draw, cx, cy, radius, color):
    points = []
    for i in range(8):
        r = radius if i % 2 == 0 else radius * 0.30
        angle = i * 3.14159265 / 4.0
        points.append((cx + r * __import__('math').sin(angle),
                       cy - r * __import__('math').cos(angle)))
    draw.polygon(points, fill=color)


def main():
    scale = 4
    s = SIZE * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))

    # rounded book shape, 2:3, centred
    bw, bh = int(s * 0.56), int(s * 0.84)
    bx, by = (s - bw) // 2, (s - bh) // 2
    body = vertical_gradient((bw, bh), (58, 42, 92), (10, 9, 18)).convert('RGBA')
    mask = Image.new('L', (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1],
                                           radius=int(s * 0.045), fill=255)
    img.paste(body, (bx, by), mask)

    draw = ImageDraw.Draw(img)
    # gold hairline frame
    draw.rounded_rectangle([bx, by, bx + bw - 1, by + bh - 1],
                           radius=int(s * 0.045), outline=(199, 166, 94, 235),
                           width=max(2, int(s * 0.008)))
    # typography bars in the lower third
    margin = int(bw * 0.16)
    y = by + int(bh * 0.66)
    for width_frac, height_frac, color in ((1.00, 0.052, (246, 240, 226, 255)),
                                           (0.72, 0.052, (246, 240, 226, 255)),
                                           (0.44, 0.024, (199, 166, 94, 230))):
        w = int((bw - 2 * margin) * width_frac)
        h = int(bh * height_frac)
        x = bx + (bw - w) // 2
        draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=color)
        y += int(h * 2.1)

    # sparkle
    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    star(ImageDraw.Draw(glow), s * 0.735, s * 0.245, s * 0.115,
         (255, 226, 160, 255))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.02)))
    img.alpha_composite(glow)

    out = os.path.normpath(OUT)
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out, 'PNG')
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
