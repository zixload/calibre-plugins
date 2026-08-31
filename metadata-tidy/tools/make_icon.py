#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regenerate metadata_tidy/images/icon.png.

    calibre-debug tools/make_icon.py
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'metadata_tidy', 'images', 'icon.png')


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

    # a metadata card
    cw, ch = int(s * 0.76), int(s * 0.62)
    cx, cy = (s - cw) // 2, int(s * 0.14)
    card = vertical_gradient((cw, ch), (44, 52, 74), (18, 21, 32)).convert('RGBA')
    mask = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1],
                                           radius=int(s * 0.05), fill=255)
    img.paste(card, (cx, cy), mask)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([cx, cy, cx + cw - 1, cy + ch - 1],
                           radius=int(s * 0.05), outline=(126, 168, 214, 230),
                           width=max(2, int(s * 0.008)))

    # metadata rows, the last one short and highlighted: the series line
    margin = int(cw * 0.13)
    y = cy + int(ch * 0.22)
    for width_frac, color in ((1.00, (232, 238, 248, 255)),
                              (0.78, (232, 238, 248, 210)),
                              (0.52, (232, 238, 248, 160))):
        w = int((cw - 2 * margin) * width_frac)
        h = int(ch * 0.085)
        draw.rounded_rectangle([cx + margin, y, cx + margin + w, y + h],
                               radius=h // 2, fill=color)
        y += int(h * 1.85)

    # the volume badge that the plugin extracts
    r = int(s * 0.155)
    bx, by = int(s * 0.72), int(s * 0.70)
    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([bx - r, by - r, bx + r, by + r],
                                 fill=(214, 168, 78, 255))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.018)))
    img.alpha_composite(glow)
    draw = ImageDraw.Draw(img)
    # a "#" drawn with strokes, so no font file is needed
    t = max(3, int(s * 0.018))
    gap = int(r * 0.20)   # small spacing, long strokes: reads as # not a frame
    for dx in (-gap, gap):
        draw.line([(bx + dx, by - int(r * 0.55)), (bx + dx, by + int(r * 0.55))],
                  fill=(28, 24, 16, 255), width=t)
    for dy in (-gap, gap):
        draw.line([(bx - int(r * 0.55), by + dy), (bx + int(r * 0.55), by + dy)],
                  fill=(28, 24, 16, 255), width=t)

    out = os.path.normpath(OUT)
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out, 'PNG')
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
