#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pure Pillow image helpers: loading, aspect preserving fill, gradients,
vignette and luminance sampling.  No calibre and no Qt imports here.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import io
import os

from PIL import Image, ImageEnhance, ImageFilter

try:  # Pillow >= 9.1
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - very old Pillow
    RESAMPLE_LANCZOS = Image.LANCZOS


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_image(source):
    """Open *source* (bytes, path or PIL image) as an RGB image."""
    if source is None:
        return None
    if isinstance(source, Image.Image):
        img = source
    elif isinstance(source, (bytes, bytearray, memoryview)):
        img = Image.open(io.BytesIO(bytes(source)))
    elif isinstance(source, str) and os.path.isfile(source):
        img = Image.open(source)
    else:
        raise ValueError('Unsupported image source: %r' % type(source))
    img.load()
    if img.mode in ('RGBA', 'LA', 'P'):
        # flatten transparency onto black so the artwork never shows checkers
        rgba = img.convert('RGBA')
        flat = Image.new('RGB', rgba.size, (0, 0, 0))
        flat.paste(rgba, mask=rgba.split()[3])
        return flat
    return img.convert('RGB')


def placeholder(width, height, top=(38, 30, 58), bottom=(8, 7, 14)):
    """Vertical gradient used when a book has no cover at all."""
    base = Image.new('RGB', (1, height))
    px = base.load()
    for y in range(height):
        t = y / float(max(1, height - 1))
        px[0, y] = tuple(int(round(top[i] + (bottom[i] - top[i]) * t)) for i in range(3))
    return base.resize((width, height), RESAMPLE_LANCZOS)


# --------------------------------------------------------------------------
# Aspect preserving fill (never distorts)
# --------------------------------------------------------------------------

def smart_fit(img, width, height, focus='center', zoom=1.0):
    """Scale *img* to cover width x height then crop, without distortion.

    *focus* biases the crop window vertically: "top" keeps heads and faces,
    "center" is neutral, "bottom" keeps the lower part of the artwork.
    """
    src_w, src_h = img.size
    if src_w <= 0 or src_h <= 0:
        return placeholder(width, height)
    scale = max(width / float(src_w), height / float(src_h)) * max(1.0, float(zoom))
    new_w = max(width, int(round(src_w * scale)))
    new_h = max(height, int(round(src_h * scale)))
    resized = img.resize((new_w, new_h), RESAMPLE_LANCZOS)

    bias = {'top': 0.0, 'upper': 0.25, 'center': 0.5, 'lower': 0.75,
            'bottom': 1.0}.get(focus, 0.5)
    left = int(round((new_w - width) * 0.5))
    top = int(round((new_h - height) * bias))
    return resized.crop((left, top, left + width, top + height))


def blurred_backdrop(img, width, height, radius_frac=0.06, darken=0.55):
    """Fallback backdrop: heavily blurred, darkened copy of the artwork."""
    back = smart_fit(img, width, height, focus='center')
    back = back.filter(ImageFilter.GaussianBlur(max(2, int(width * radius_frac))))
    return ImageEnhance.Brightness(back).enhance(1.0 - darken)


def fit_inside(img, width, height):
    """Scale down so the whole image is visible (letterboxed), no distortion."""
    src_w, src_h = img.size
    scale = min(width / float(src_w), height / float(src_h))
    return img.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))),
                      RESAMPLE_LANCZOS)


def compose_contain(img, width, height):
    """Whole artwork centred over a blurred version of itself."""
    canvas = blurred_backdrop(img, width, height)
    fitted = fit_inside(img, width, height)
    canvas.paste(fitted, ((width - fitted.width) // 2,
                          (height - fitted.height) // 2))
    return canvas


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------

def grade(img, darken=0.0, saturation=1.0, contrast=1.0, vignette=0.0):
    """Apply the light colour grading a preset asks for."""
    out = img
    if abs(saturation - 1.0) > 1e-3:
        out = ImageEnhance.Color(out).enhance(saturation)
    if abs(contrast - 1.0) > 1e-3:
        out = ImageEnhance.Contrast(out).enhance(contrast)
    if darken > 1e-3:
        out = ImageEnhance.Brightness(out).enhance(max(0.05, 1.0 - darken))
    if vignette > 1e-3:
        out = apply_vignette(out, vignette)
    return out


def apply_vignette(img, strength=0.35):
    """Soft radial darkening of the corners."""
    w, h = img.size
    small_w, small_h = max(16, w // 8), max(16, h // 8)
    mask = Image.new('L', (small_w, small_h), 0)
    px = mask.load()
    cx, cy = (small_w - 1) / 2.0, (small_h - 1) / 2.0
    max_d = (cx ** 2 + cy ** 2) ** 0.5
    for y in range(small_h):
        for x in range(small_w):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / max_d
            t = max(0.0, (d - 0.55) / 0.45)
            px[x, y] = int(255 * min(1.0, t * t) * strength)
    mask = mask.resize((w, h), RESAMPLE_LANCZOS).filter(
        ImageFilter.GaussianBlur(max(2, w // 60)))
    dark = Image.new('RGB', (w, h), (0, 0, 0))
    return Image.composite(dark, img, mask)


# --------------------------------------------------------------------------
# Gradient scrims (the automatic contrast helper)
# --------------------------------------------------------------------------

def gradient_overlay(width, height, side='bottom', extent=0.55, alpha=0.75,
                     color=(0, 0, 0), curve=1.6):
    """RGBA layer fading from *alpha* at *side* to fully transparent."""
    layer = Image.new('RGBA', (width, height), color + (0,))
    if extent <= 0 or alpha <= 0:
        return layer
    top_alpha = int(max(0, min(255, round(alpha * 255))))

    if side in ('bottom', 'top'):
        span = max(1, int(round(height * extent)))
        strip = Image.new('L', (1, span))
        px = strip.load()
        for i in range(span):
            t = i / float(max(1, span - 1))
            if side == 'bottom':
                value = t ** curve
            else:
                value = (1.0 - t) ** curve
            px[0, i] = int(round(top_alpha * value))
        mask = strip.resize((width, span), RESAMPLE_LANCZOS)
        full = Image.new('L', (width, height), 0)
        full.paste(mask, (0, height - span if side == 'bottom' else 0))
    else:  # left / right
        span = max(1, int(round(width * extent)))
        strip = Image.new('L', (span, 1))
        px = strip.load()
        for i in range(span):
            t = i / float(max(1, span - 1))
            value = (t ** curve) if side == 'right' else ((1.0 - t) ** curve)
            px[i, 0] = int(round(top_alpha * value))
        mask = strip.resize((span, height), RESAMPLE_LANCZOS)
        full = Image.new('L', (width, height), 0)
        full.paste(mask, (width - span if side == 'right' else 0, 0))

    layer.putalpha(full)
    return layer


def band_overlay(width, height, top, bottom, alpha=0.6, feather=0.35,
                 color=(0, 0, 0)):
    """Soft horizontal band of darkness between y=*top* and y=*bottom* (px)."""
    layer = Image.new('RGBA', (width, height), color + (0,))
    top = max(0, int(top))
    bottom = min(height, int(bottom))
    if bottom <= top or alpha <= 0:
        return layer
    mask = Image.new('L', (width, height), 0)
    mask.paste(int(max(0, min(255, round(alpha * 255)))),
               (0, top, width, bottom))
    radius = max(2, int((bottom - top) * feather))
    mask = mask.filter(ImageFilter.GaussianBlur(radius))
    layer.putalpha(mask)
    return layer


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def region_luminance(img, box):
    """Mean perceptual luminance (0..1) and contrast (0..1) inside *box*."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0 = max(0, min(img.width - 1, x0))
    y0 = max(0, min(img.height - 1, y0))
    x1 = max(x0 + 1, min(img.width, x1))
    y1 = max(y0 + 1, min(img.height, y1))
    region = img.crop((x0, y0, x1, y1)).convert('L')
    region = region.resize((min(64, region.width), min(96, region.height)),
                           RESAMPLE_LANCZOS)
    pixels = list(region.getdata())
    if not pixels:
        return 0.5, 0.0
    mean = sum(pixels) / float(len(pixels)) / 255.0
    variance = sum((p / 255.0 - mean) ** 2 for p in pixels) / float(len(pixels))
    return mean, variance ** 0.5


def to_bytes(img, fmt='JPEG', quality=92):
    """Encode a PIL image, returning raw bytes suitable for calibre."""
    buf = io.BytesIO()
    fmt = (fmt or 'JPEG').upper()
    if fmt in ('JPG', 'JPEG'):
        img.convert('RGB').save(buf, 'JPEG', quality=int(quality),
                                optimize=True, progressive=True, subsampling=0)
    else:
        img.save(buf, fmt)
    return buf.getvalue()
