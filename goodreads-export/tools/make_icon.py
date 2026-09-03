#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regenerate goodreads_export/images/icon.png (calibre-debug tools/make_icon.py)."""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'goodreads_export', 'images', 'icon.png')


def vertical_gradient(size, top, bottom):
    strip = Image.new('RGB', (1, size[1]))
    px = strip.load()
    for y in range(size[1]):
        t = y / float(max(1, size[1] - 1))
        px[0, y] = tuple(int(round(top[i] + (bottom[i] - top[i]) * t))
                         for i in range(3))
    return strip.resize(size, Image.Resampling.LANCZOS)


def main():
    scale = 4
    s = SIZE * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))

    # a sheet of rows: the CSV
    pw, ph = int(s * 0.62), int(s * 0.78)
    px, py = int(s * 0.07), (s - ph) // 2
    sheet = vertical_gradient((pw, ph), (247, 244, 236), (214, 208, 192))
    mask = Image.new('L', (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1],
                                           radius=int(s * 0.035), fill=255)
    img.paste(sheet.convert('RGBA'), (px, py), mask)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([px, py, px + pw - 1, py + ph - 1],
                           radius=int(s * 0.035), outline=(120, 104, 74, 230),
                           width=max(2, int(s * 0.007)))
    # the header row, then data rows
    m = int(pw * 0.11)
    y = py + int(ph * 0.13)
    draw.rounded_rectangle([px + m, y, px + pw - m, y + int(ph * 0.075)],
                           radius=int(ph * 0.02), fill=(122, 100, 62, 255))
    y += int(ph * 0.16)
    for frac in (1.0, 0.82, 0.9, 0.68):
        h = int(ph * 0.045)
        w = int((pw - 2 * m) * frac)
        draw.rounded_rectangle([px + m, y, px + m + w, y + h],
                               radius=h // 2, fill=(150, 140, 118, 220))
        y += int(h * 2.3)

    # the Goodreads-ish star, telling ratings travel with it
    gold = (226, 178, 74, 255)
    import math
    cx, cy, r = s * 0.775, s * 0.72, s * 0.20
    points = []
    for i in range(10):
        radius = r if i % 2 == 0 else r * 0.44
        angle = math.radians(i * 36 - 90)
        points.append((cx + radius * math.cos(angle),
                       cy + radius * math.sin(angle)))
    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(points, fill=gold)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.016)))
    img.alpha_composite(glow)

    out = os.path.normpath(OUT)
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out, 'PNG')
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
