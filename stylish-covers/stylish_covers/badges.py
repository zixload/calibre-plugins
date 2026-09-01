#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Badges: a small personal mark stamped onto a cover.

A badge is not part of the book: it is your library's signature, a name in the
margin, a seal in a corner.  It is drawn last, in the margins the presets keep
free, so it never collides with the title or the author.

Like presets, a badge is plain data expressed in fractions of the canvas, so
it renders identically at any resolution.  Pillow only, no calibre, no Qt.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import math
import random

from PIL import Image, ImageDraw

from . import imageops, textfx
from .textfx import Effects

# --------------------------------------------------------------------------
# Ornaments
# --------------------------------------------------------------------------

def blossom(size, color, petals=5, line=2):
    """A small five petal flower, drawn once then rotated."""
    size = max(6, int(size))
    tile = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    petal = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(petal)
    width, height, centre = size * 0.24, size * 0.42, size / 2.0
    box = [centre - width / 2, size * 0.06, centre + width / 2, size * 0.06 + height]
    if line:
        draw.ellipse(box, outline=color, width=max(1, int(line)))
    else:
        draw.ellipse(box, fill=color)
    for i in range(petals):
        tile.alpha_composite(petal.rotate(i * 360.0 / petals,
                                          resample=Image.BICUBIC,
                                          center=(centre, centre)))
    radius = size * 0.055
    ImageDraw.Draw(tile).ellipse(
        [centre - radius, centre - radius, centre + radius, centre + radius],
        fill=color)
    return tile


def _rgba(color, alpha):
    rgb = textfx._rgba(color, 1.0)[:3]
    return rgb + (int(max(0, min(255, round(alpha * 255)))),)


# --------------------------------------------------------------------------
# Where to put it
# --------------------------------------------------------------------------

def quietest_side(image, band=0.13, top=0.16, bottom=0.72):
    """Which vertical margin carries the least detail.

    It measures busyness, so it steers the badge away from a crowded margin.
    It cannot recognise lettering already painted into the artwork, which is
    why the side can always be forced by hand.
    """
    rgb = image.convert('RGB')
    width, height = rgb.size
    span = width * band
    scores = {}
    for side, x0 in (('left', 0.0), ('right', width - span)):
        mean, sd = imageops.region_luminance(
            rgb, (x0, height * top, x0 + span, height * bottom))
        scores[side] = sd + max(0.0, mean - 0.55) * 0.5
    return min(scores, key=scores.get), scores


def quietest_corner(image, size=0.30):
    """Which corner carries the least detail."""
    rgb = image.convert('RGB')
    width, height = rgb.size
    w, h = width * size, height * size * 0.75
    boxes = {
        'tl': (0, 0, w, h), 'tr': (width - w, 0, width, h),
        'bl': (0, height - h, w, height),
        'br': (width - w, height - h, width, height),
    }
    scores = {}
    for name, box in boxes.items():
        mean, sd = imageops.region_luminance(rgb, box)
        scores[name] = sd + max(0.0, mean - 0.55) * 0.5
    return min(scores, key=scores.get), scores


# --------------------------------------------------------------------------
# The badges themselves
# --------------------------------------------------------------------------

VINE = {
    'id': 'vine',
    'label': 'Vine',
    'description': 'Vertical text in the margin, framed by two hairlines, with '
                   'a trail of small flowers. The most decorative one.',
    'layout': 'margin',
    'text_size': 0.058, 'color': '#F4EEE0', 'opacity': 1.0,
    'margin': 0.085, 'top': 0.20, 'max_height': 0.46, 'line_spacing': 1.26,
    'rules': True, 'ornament': 'flowers', 'ornament_count': 5,
    'ornament_alpha': 0.31, 'ornament_size': 0.040,
    'scrim': {'extent': 0.17, 'alpha': 0.55, 'curve': 1.6},
    'effects': {'shadow': 1.0, 'shadow_offset': 0.028, 'shadow_blur': 0.075,
                'glow': 0.25, 'glow_color': '#000000', 'glow_radius': 0.16},
}

MARK = {
    'id': 'mark',
    'label': 'Mark',
    'description': 'The same vertical text, but bare: no flowers, no gradient. '
                   'The discreet one.',
    'layout': 'margin',
    'text_size': 0.046, 'color': '#F0EADC', 'opacity': 0.92,
    'margin': 0.070, 'top': 0.30, 'max_height': 0.40, 'line_spacing': 1.22,
    'rules': True, 'ornament': 'none',
    'scrim': None,
    'effects': {'shadow': 1.0, 'shadow_offset': 0.030, 'shadow_blur': 0.085},
}

SEAL = {
    'id': 'seal',
    'label': 'Seal',
    'description': 'A round stamp in the quietest corner, ringed with flowers. '
                   'Reads like a library stamp.',
    'layout': 'seal',
    'text_size': 0.052, 'color': '#F6F0E2', 'opacity': 1.0,
    'radius': 0.105, 'inset': 0.135,
    'ring_color': '#EBE1CD', 'fill': '#12101499',
    'ornament': 'flowers', 'ornament_count': 8, 'ornament_alpha': 0.28,
    'ornament_size': 0.048,
    'scrim': None,
    'effects': {'shadow': 0.9, 'shadow_offset': 0.02, 'shadow_blur': 0.06},
}

RIBBON = {
    'id': 'ribbon',
    'label': 'Ribbon',
    'description': 'A thin horizontal strip along the very bottom edge, under '
                   'everything else.',
    'layout': 'ribbon',
    'text_size': 0.030, 'color': '#E6DDC8', 'opacity': 1.0,
    'height': 0.052, 'tracking': 0.24,
    'rules': True, 'ornament': 'flowers', 'ornament_count': 6,
    'ornament_alpha': 0.22, 'ornament_size': 0.028,
    'scrim': {'extent': 0.10, 'alpha': 0.62, 'curve': 2.0},
    'effects': {'shadow': 0.9, 'shadow_offset': 0.03, 'shadow_blur': 0.09},
}

BUILTIN_BADGES = [VINE, MARK, SEAL, RIBBON]
_BY_ID = dict((b['id'], b) for b in BUILTIN_BADGES)
DEFAULT_BADGE = 'vine'


def badge_choices(user_badges=None):
    out = [(b['id'], b['label']) for b in BUILTIN_BADGES]
    for bid, data in sorted((user_badges or {}).items()):
        out.append((bid, data.get('label', bid) + '  (custom)'))
    return out


def get_badge(badge_id, user_badges=None):
    user_badges = user_badges or {}
    if badge_id in user_badges:
        base = get_badge(user_badges[badge_id].get('base', DEFAULT_BADGE))
        from .presets import deep_merge
        return deep_merge(base, copy.deepcopy(user_badges[badge_id]))
    return copy.deepcopy(_BY_ID.get(badge_id, _BY_ID[DEFAULT_BADGE]))


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def _effects(spec, scale, opacity):
    fx = Effects(**dict(spec.get('effects', {})))
    fx.shadow *= scale
    fx.glow *= scale
    fx.opacity = opacity
    return fx


def _draw_margin(canvas, spec, book, measurer, text, settings):
    width, height = canvas.size
    side = settings.get('badge_side', 'auto')
    if side not in ('left', 'right'):
        side, _scores = quietest_side(canvas)

    scrim = spec.get('scrim')
    if scrim and settings.get('badge_scrim', True):
        canvas.alpha_composite(imageops.gradient_overlay(
            width, height, side=side, extent=scrim['extent'],
            alpha=scrim['alpha'], curve=scrim.get('curve', 1.6)))

    margin = spec.get('margin', 0.085)
    axis = width * (1.0 - margin) if side == 'right' else width * margin
    scale = float(settings.get('badge_size_scale', 1.0))
    opacity = float(settings.get('badge_opacity', 1.0))
    size = width * spec.get('text_size', 0.055) * scale

    block = textfx.render_vertical(
        text, book, measurer, 'cjk', size,
        color=settings.get('badge_color') or spec.get('color', '#FFFFFF'),
        line_spacing=spec.get('line_spacing', 1.24),
        effects=_effects(spec, 1.0, opacity),
        max_height=height * spec.get('max_height', 0.46),
        min_size=width * 0.020)
    if block is None:
        return canvas
    top = height * spec.get('top', 0.20)
    rect = block.paste_on(canvas, axis, top, 'center-top')

    draw = ImageDraw.Draw(canvas, 'RGBA')
    gap = height * 0.030
    rule = _rgba(spec.get('color', '#FFFFFF'), 0.62 * opacity)
    if spec.get('rules', True):
        draw.line([(axis, top - gap * 1.9), (axis, top - gap * 0.6)],
                  fill=rule, width=max(1, int(width * 0.0020)))
        draw.line([(axis, rect[3] + gap * 0.6), (axis, rect[3] + gap * 1.9)],
                  fill=rule, width=max(1, int(width * 0.0020)))

    if spec.get('ornament') == 'flowers' and settings.get('badge_ornament', True):
        _vine_flowers(canvas, spec, axis, rect, top, gap, opacity)
    return canvas


def _vine_flowers(canvas, spec, axis, rect, top, gap, opacity):
    width, height = canvas.size
    rng = random.Random(int(axis) * 7 + 13)
    layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    colour = _rgba('#F6EEDC', spec.get('ornament_alpha', 0.30) * opacity)
    base = width * spec.get('ornament_size', 0.040)
    for i in range(int(spec.get('ornament_count', 5))):
        size = int(base * rng.uniform(0.8, 1.25))
        y = int(rect[3] + gap * 2.6 + i * height * 0.043)
        if y + size > height * 0.97:
            break
        x = int(axis - size / 2 + rng.uniform(-width * 0.012, width * 0.012))
        layer.alpha_composite(
            blossom(size, colour).rotate(rng.uniform(0, 360),
                                         resample=Image.BICUBIC), (x, y))
    for i in range(2):
        size = int(base * rng.uniform(0.65, 0.9))
        y = int(top - gap * 2.4 - i * height * 0.040) - size
        if y < height * 0.03:
            break
        layer.alpha_composite(blossom(size, colour), (int(axis - size / 2), y))
    canvas.alpha_composite(layer)


def _draw_seal(canvas, spec, book, measurer, text, settings):
    width, height = canvas.size
    corner = settings.get('badge_side', 'auto')
    if corner not in ('tl', 'tr', 'bl', 'br'):
        corner, _scores = quietest_corner(canvas)

    scale = float(settings.get('badge_size_scale', 1.0))
    opacity = float(settings.get('badge_opacity', 1.0))
    radius = int(width * spec.get('radius', 0.105) * scale)
    inset = spec.get('inset', 0.135)
    cx = width * (1.0 - inset) if corner in ('tr', 'br') else width * inset
    cy = height * (1.0 - inset * 0.72) if corner in ('bl', 'br') \
        else height * inset * 0.72

    if spec.get('ornament') == 'flowers' and settings.get('badge_ornament', True):
        petals = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        colour = _rgba('#F5ECD8', spec.get('ornament_alpha', 0.28) * opacity)
        size = int(width * spec.get('ornament_size', 0.048) * scale)
        for i in range(int(spec.get('ornament_count', 8))):
            angle = math.radians(i * 360.0 / spec.get('ornament_count', 8))
            petals.alpha_composite(
                blossom(size, colour),
                (int(cx + math.cos(angle) * (radius + size * 0.55) - size / 2),
                 int(cy + math.sin(angle) * (radius + size * 0.55) - size / 2)))
        canvas.alpha_composite(petals)

    seal = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(seal)
    fill = spec.get('fill', '#12101499')
    alpha = int(fill[7:9], 16) / 255.0 if len(fill) >= 9 else 0.6
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 fill=_rgba(fill[:7], alpha * opacity),
                 outline=_rgba(spec.get('ring_color', '#FFFFFF'), 0.80 * opacity),
                 width=max(2, int(width * 0.0028)))
    inner = radius - int(width * 0.010)
    draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
                 outline=_rgba(spec.get('ring_color', '#FFFFFF'), 0.38 * opacity),
                 width=max(1, int(width * 0.0012)))
    canvas.alpha_composite(seal)

    head, tail = (text.split(' ', 1) + [''])[:2] if ' ' in text else (text, '')
    size = width * spec.get('text_size', 0.052) * scale
    lines, fitted = textfx.fit_text(head, measurer, 'cjk', radius * 1.55,
                                    max_lines=1, max_size=size,
                                    min_size=size * 0.5)
    block = textfx.render_block(
        lines, book, measurer, 'cjk', fitted,
        color=settings.get('badge_color') or spec.get('color', '#FFFFFF'),
        align='center', effects=_effects(spec, 1.0, opacity))
    if block is not None:
        block.paste_on(canvas, cx, cy - (radius * 0.10 if tail else 0),
                       'center-middle')
    if tail:
        lines, fitted = textfx.fit_text(tail, measurer, 'cjk', radius * 1.4,
                                        max_lines=1, max_size=size * 0.38,
                                        min_size=size * 0.22, tracking=0.18)
        small = textfx.render_block(
            lines, book, measurer, 'cjk', fitted, color=spec.get('color'),
            tracking=0.18, align='center', effects=_effects(spec, 1.0,
                                                            0.78 * opacity))
        if small is not None:
            small.paste_on(canvas, cx, cy + radius * 0.50, 'center-middle')
    return canvas


def _draw_ribbon(canvas, spec, book, measurer, text, settings):
    width, height = canvas.size
    scale = float(settings.get('badge_size_scale', 1.0))
    opacity = float(settings.get('badge_opacity', 1.0))
    band = height * spec.get('height', 0.052) * scale
    top = height - band

    scrim = spec.get('scrim')
    if scrim and settings.get('badge_scrim', True):
        canvas.alpha_composite(imageops.gradient_overlay(
            width, height, side='bottom', extent=scrim['extent'],
            alpha=scrim['alpha'], curve=scrim.get('curve', 2.0)))

    size = width * spec.get('text_size', 0.030) * scale
    tracking = spec.get('tracking', 0.24)
    lines, fitted = textfx.fit_text(text, measurer, 'cjk', width * 0.62,
                                    max_lines=1, max_size=size,
                                    min_size=size * 0.55, tracking=tracking)
    block = textfx.render_block(
        lines, book, measurer, 'cjk', fitted,
        color=settings.get('badge_color') or spec.get('color', '#FFFFFF'),
        tracking=tracking, align='center',
        effects=_effects(spec, 1.0, opacity))
    if block is None:
        return canvas
    rect = block.paste_on(canvas, width / 2.0, top + band / 2.0, 'center-middle')

    if spec.get('ornament') == 'flowers' and settings.get('badge_ornament', True):
        layer = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        colour = _rgba('#F6EEDC', spec.get('ornament_alpha', 0.22) * opacity)
        size_px = int(width * spec.get('ornament_size', 0.028) * scale)
        rng = random.Random(5)
        count = int(spec.get('ornament_count', 6))
        for i in range(count):
            left = i < count / 2
            span = (rect[0] - width * 0.06) if left else (width * 0.94 - rect[2])
            if span < size_px * 1.4:
                continue
            x = rng.uniform(width * 0.06, rect[0] - size_px) if left else \
                rng.uniform(rect[2], width * 0.94 - size_px)
            y = top + band / 2.0 - size_px / 2 + rng.uniform(-band * 0.2, band * 0.2)
            layer.alpha_composite(blossom(size_px, colour), (int(x), int(y)))
        canvas.alpha_composite(layer)
    return canvas


LAYOUTS = {'margin': _draw_margin, 'seal': _draw_seal, 'ribbon': _draw_ribbon}


def draw_badge(canvas, settings, book_fonts, measurer, user_badges=None):
    """Stamp the configured badge onto an RGBA canvas, in place."""
    text = (settings.get('badge_text') or '').strip()
    if not settings.get('badge_enabled') or not text:
        return canvas
    spec = get_badge(settings.get('badge_preset', DEFAULT_BADGE),
                     user_badges or settings.get('user_badges'))
    handler = LAYOUTS.get(spec.get('layout', 'margin'), _draw_margin)
    book_fonts.use_best_cjk_for(text)
    return handler(canvas, spec, book_fonts, measurer, text, settings)
