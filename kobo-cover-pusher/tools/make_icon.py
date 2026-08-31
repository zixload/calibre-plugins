#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regenerate kobo_cover_pusher/images/icon.png (calibre-debug tools/make_icon.py)."""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                   'kobo_cover_pusher', 'images', 'icon.png')


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

    # the e-reader
    dw, dh = int(s * 0.60), int(s * 0.84)
    dx, dy = int(s * 0.06), (s - dh) // 2
    body = vertical_gradient((dw, dh), (60, 64, 72), (22, 24, 28)).convert('RGBA')
    mask = Image.new('L', (dw, dh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, dw - 1, dh - 1],
                                           radius=int(s * 0.05), fill=255)
    img.paste(body, (dx, dy), mask)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([dx, dy, dx + dw - 1, dy + dh - 1],
                           radius=int(s * 0.05), outline=(150, 156, 166, 235),
                           width=max(2, int(s * 0.007)))
    # its screen, holding a cover
    m = int(dw * 0.11)
    sx0, sy0 = dx + m, dy + int(dh * 0.07)
    sx1, sy1 = dx + dw - m, dy + dh - int(dh * 0.13)
    screen = vertical_gradient((sx1 - sx0, sy1 - sy0), (46, 38, 70), (14, 12, 20))
    img.paste(screen.convert('RGBA'), (sx0, sy0))
    draw.rectangle([sx0, sy0, sx1, sy1], outline=(96, 100, 112, 220),
                   width=max(1, int(s * 0.004)))
    for frac, alpha in ((0.72, 255), (0.48, 190)):
        w = int((sx1 - sx0) * frac)
        h = int(s * 0.020)
        y = sy1 - int(s * 0.13) + (0 if frac > 0.6 else int(s * 0.048))
        x = sx0 + ((sx1 - sx0) - w) // 2
        draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2,
                               fill=(240, 234, 220, alpha))

    # the arrow pushing a cover into the device
    gold = (214, 168, 78, 255)
    ay = s // 2
    ax0, ax1 = int(s * 0.72), int(s * 0.955)
    t = int(s * 0.05)
    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.rounded_rectangle([ax0, ay - t // 2, ax1, ay + t // 2],
                            radius=t // 2, fill=gold)
    head = int(s * 0.105)
    gdraw.polygon([(ax0 + int(s * 0.02), ay - head), (ax0 - int(s * 0.10), ay),
                   (ax0 + int(s * 0.02), ay + head)], fill=gold)
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(s * 0.016)))
    img.alpha_composite(glow)

    out = os.path.normpath(OUT)
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out, 'PNG')
    print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
