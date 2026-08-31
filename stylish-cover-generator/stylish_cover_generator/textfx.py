#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Typography engine: word wrapping, automatic size fitting, letter spacing,
mixed-script rendering and text effects (stroke, drop shadow, glow).

Text is always rendered into its own RGBA tile so effects can be applied
without touching the artwork, and so the caller can position the block by its
real ink box rather than by font metrics.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re

from PIL import Image, ImageDraw, ImageFilter

CJK_RANGES = (
    (0x1100, 0x11FF),   # hangul jamo
    (0x2E80, 0x303F),   # radicals, CJK punctuation
    (0x3040, 0x30FF),   # kana
    (0x3130, 0x318F),   # hangul compatibility jamo
    (0x3400, 0x4DBF),   # ext A
    (0x4E00, 0x9FFF),   # unified ideographs
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),   # hangul syllables
    (0xF900, 0xFAFF),   # compatibility ideographs
    (0xFF00, 0xFF65),   # fullwidth forms
    (0x20000, 0x2FA1F),  # ext B..F
)


def is_cjk(char):
    cp = ord(char)
    for lo, hi in CJK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def has_cjk(text):
    return any(is_cjk(c) for c in text or '')


# --------------------------------------------------------------------------
# Measuring
# --------------------------------------------------------------------------

class Measurer(object):
    """Caches per character advances for one FontBook."""

    def __init__(self, book):
        self.book = book
        self._cache = {}

    def advance(self, char, role, size):
        key = (char, role, int(size))
        val = self._cache.get(key)
        if val is None:
            font = self.book.font_for_char(char, role, size)
            try:
                val = font.getlength(char)
            except AttributeError:  # pragma: no cover - ancient Pillow
                val = font.getsize(char)[0]
            self._cache[key] = val
        return val

    def width(self, text, role, size, tracking_px=0.0):
        if not text:
            return 0.0
        total = sum(self.advance(c, role, size) for c in text)
        total += tracking_px * (len(text) - 1)
        return total

    def metrics(self, role, size):
        font = self.book.font(role, size)
        try:
            ascent, descent = font.getmetrics()
        except Exception:
            ascent, descent = int(size * 0.8), int(size * 0.2)
        return ascent, descent


# --------------------------------------------------------------------------
# Wrapping
# --------------------------------------------------------------------------

_WORD_RE = re.compile(r'\s+')

# hard ceiling when a title refuses to fit: more lines beats losing words
MAX_FALLBACK_LINES = 8


def chunks_of(text):
    """Split *text* into wrappable chunks: latin words and single CJK chars.

    Returns a list of (chunk, space_before) tuples, so a mixed latin/CJK title
    can break between ideographs but never inside a latin word.
    """
    out = []
    space_pending = False
    buf = ''
    for ch in text.strip():
        if ch.isspace():
            if buf:
                out.append((buf, space_pending))
                space_pending = False
                buf = ''
            space_pending = bool(out) or space_pending
            continue
        if is_cjk(ch):
            if buf:
                out.append((buf, space_pending))
                space_pending = False
                buf = ''
            out.append((ch, space_pending))
            space_pending = False
        else:
            if not buf and not out:
                space_pending = False
            buf += ch
    if buf:
        out.append((buf, space_pending))
    return out


def _join(chunks):
    parts = []
    for i, (chunk, space_before) in enumerate(chunks):
        if space_before and i:
            parts.append(' ')
        parts.append(chunk)
    return ''.join(parts)


def explode_long(chunks, measurer, role, size, tracking_px, max_width):
    """Break apart any chunk too wide to ever fit, character by character.

    Without this a single very long word (or a URL-like title) would overflow
    the canvas whatever the font size.
    """
    out = []
    for chunk, space_before in chunks:
        if len(chunk) > 1 and measurer.width(chunk, role, size,
                                             tracking_px) > max_width:
            for i, char in enumerate(chunk):
                out.append((char, space_before if i == 0 else False))
        else:
            out.append((chunk, space_before))
    return out


def greedy_wrap(chunks, measurer, role, size, tracking_px, max_width):
    """Classic greedy wrap; returns a list of chunk lists."""
    lines, current = [], []
    for item in chunks:
        candidate = current + [item]
        if current and measurer.width(_join(candidate), role, size, tracking_px) > max_width:
            lines.append(current)
            current = [(item[0], False)]
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def balanced_wrap(chunks, measurer, role, size, tracking_px, n_lines):
    """Split *chunks* into exactly *n_lines* lines with even widths."""
    if n_lines <= 1 or len(chunks) <= 1:
        return [chunks]
    n_lines = min(n_lines, len(chunks))
    widths = {}

    def line_width(i, j):
        key = (i, j)
        if key not in widths:
            widths[key] = measurer.width(_join(chunks[i:j]), role, size, tracking_px)
        return widths[key]

    best = {}

    def solve(start, remaining):
        key = (start, remaining)
        if key in best:
            return best[key]
        if remaining == 1:
            res = (line_width(start, len(chunks)), [len(chunks)])
            best[key] = res
            return res
        result = None
        for end in range(start + 1, len(chunks) - remaining + 2):
            cost, splits = solve(end, remaining - 1)
            here = max(line_width(start, end), cost)
            # tie-break on the sum so lines stay visually even
            score = (here, line_width(start, end))
            if result is None or score < result[0]:
                result = (score, [end] + splits)
        res = (result[0][0], result[1])
        best[key] = res
        return res

    _cost, splits = solve(0, n_lines)
    lines, prev = [], 0
    for cut in splits:
        lines.append(chunks[prev:cut])
        prev = cut
    return [ln for ln in lines if ln]


def fit_text(text, measurer, role, max_width, max_lines=3, max_size=200,
             min_size=12, tracking=0.0, balance=True, max_height=None,
             line_spacing=1.10):
    """Largest size at which *text* fits in *max_width* over <= *max_lines*.

    When *max_height* is given the block is also kept inside that height, so a
    long title cannot invade the rest of the composition.
    Returns (lines, size) where lines is a list of strings.
    """
    text = (text or '').strip()
    if not text:
        return [], min_size
    forced = [seg for seg in text.split('\n') if seg.strip()]
    if len(forced) > 1:
        # honour manual line breaks: fit each and take the smallest size
        size = max_size
        for seg in forced:
            _l, s = fit_text(seg, measurer, role, max_width, 1, size, min_size,
                             tracking, balance)
            size = min(size, s)
        return forced, size

    chunks = chunks_of(text)

    def fits(size, line_limit):
        tracking_px = tracking * size
        usable = explode_long(chunks, measurer, role, size, tracking_px,
                              max_width)
        lines = greedy_wrap(usable, measurer, role, size, tracking_px, max_width)
        if len(lines) > line_limit:
            return None
        if balance and 1 < len(lines) <= line_limit:
            lines = balanced_wrap(usable, measurer, role, size, tracking_px,
                                  len(lines))
        if any(measurer.width(_join(ln), role, size, tracking_px) > max_width
               for ln in lines):
            return None
        if max_height:
            ascent, descent = measurer.metrics(role, size)
            if (ascent + descent) * line_spacing * len(lines) > max_height:
                return None
        return [_join(ln) for ln in lines]

    def search(line_limit, floor_size):
        lo, hi = int(floor_size), int(max_size)
        found, found_size = None, lo
        while lo <= hi:
            mid = (lo + hi) // 2
            result = fits(mid, line_limit)
            if result is not None:
                found, found_size = result, mid
                lo = mid + 1
            else:
                hi = mid - 1
        return found, found_size

    best, best_size = search(max_lines, min_size)
    if best is None:
        # A title that cannot fit must never lose words: relax the line count
        # and the minimum size first, in that order.
        for line_limit, floor in ((max_lines + 2, min_size * 0.8),
                                  (MAX_FALLBACK_LINES, min_size * 0.55)):
            best, best_size = search(line_limit, max(6, floor))
            if best is not None:
                break
    if best is None:
        # pathological input: keep what fits rather than spill off the canvas
        floor = max(6, min_size * 0.55)
        tracking_px = tracking * floor
        usable = explode_long(chunks, measurer, role, floor, tracking_px,
                              max_width)
        lines = greedy_wrap(usable, measurer, role, floor, tracking_px,
                            max_width)[:MAX_FALLBACK_LINES]
        best, best_size = [_join(ln) for ln in lines], floor
    return best, best_size


# --------------------------------------------------------------------------
# Effects
# --------------------------------------------------------------------------

def _rgba(color, opacity=1.0):
    if isinstance(color, str):
        c = color.lstrip('#')
        if len(c) == 3:
            c = ''.join(ch * 2 for ch in c)
        rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    else:
        rgb = tuple(color[:3])
    alpha = int(max(0, min(255, round(255 * opacity))))
    return rgb + (alpha,)


class Effects(object):
    """Effect parameters expressed as fractions of the font size."""

    def __init__(self, shadow=0.0, shadow_color='#000000', shadow_offset=0.045,
                 shadow_blur=0.09, stroke=0.0, stroke_color='#000000',
                 glow=0.0, glow_color='#000000', glow_radius=0.22,
                 opacity=1.0):
        self.shadow = float(shadow)
        self.shadow_color = shadow_color
        self.shadow_offset = float(shadow_offset)
        self.shadow_blur = float(shadow_blur)
        self.stroke = float(stroke)
        self.stroke_color = stroke_color
        self.glow = float(glow)
        self.glow_color = glow_color
        self.glow_radius = float(glow_radius)
        self.opacity = float(opacity)

    def scaled(self, shadow=1.0, stroke=1.0, glow=1.0):
        clone = Effects(**self.__dict__)
        clone.shadow *= shadow
        clone.stroke *= stroke
        clone.glow *= glow
        return clone

    def padding(self, size):
        pad = 4
        if self.shadow > 0:
            pad = max(pad, (self.shadow_offset + self.shadow_blur * 2.5) * size)
        if self.glow > 0:
            pad = max(pad, self.glow_radius * 2.5 * size)
        if self.stroke > 0:
            pad = max(pad, self.stroke * size * 2)
        return int(round(pad)) + 2


class TextBlock(object):
    """A rendered RGBA tile plus the ink box of the glyphs inside it."""

    __slots__ = ('image', 'ink', 'size', 'lines')

    def __init__(self, image, ink, size, lines):
        self.image = image
        self.ink = ink            # (x0, y0, x1, y1) inside image
        self.size = size          # font size actually used
        self.lines = lines

    @property
    def width(self):
        return self.ink[2] - self.ink[0]

    @property
    def height(self):
        return self.ink[3] - self.ink[1]

    def paste_on(self, canvas, x, y, anchor='center-top'):
        """Composite so the ink box lands at (x, y) with the given anchor.

        Returns the ink rectangle in canvas coordinates.
        """
        ax, ay = anchor.split('-')
        ox = {'left': 0, 'center': self.width / 2.0, 'right': self.width}[ax]
        oy = {'top': 0, 'middle': self.height / 2.0, 'bottom': self.height}[ay]
        px = int(round(x - ox - self.ink[0]))
        py = int(round(y - oy - self.ink[1]))
        # clip against the canvas: alpha_composite refuses negative offsets
        crop_x, crop_y = max(0, -px), max(0, -py)
        crop_x2 = min(self.image.width, canvas.width - px)
        crop_y2 = min(self.image.height, canvas.height - py)
        if crop_x2 > crop_x and crop_y2 > crop_y:
            piece = self.image.crop((crop_x, crop_y, crop_x2, crop_y2))
            canvas.alpha_composite(piece, (px + crop_x, py + crop_y))
        return (px + self.ink[0], py + self.ink[1],
                px + self.ink[2], py + self.ink[3])


def _draw_run(draw, x, baseline, text, book, role, size, fill, tracking_px,
              stroke_width=0, stroke_fill=None):
    for ch in text:
        font = book.font_for_char(ch, role, size)
        if not ch.isspace():
            draw.text((x, baseline), ch, font=font, fill=fill, anchor='ls',
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
        try:
            adv = font.getlength(ch)
        except AttributeError:  # pragma: no cover
            adv = font.getsize(ch)[0]
        x += adv + tracking_px
    return x


def render_block(lines, book, measurer, role, size, color='#FFFFFF',
                 tracking=0.0, line_spacing=1.12, align='center',
                 effects=None, max_width=None):
    """Render *lines* into an RGBA tile with the requested effects."""
    effects = effects or Effects()
    if not lines:
        return None
    tracking_px = tracking * size
    widths = [measurer.width(ln, role, size, tracking_px) for ln in lines]
    ascent, descent = measurer.metrics(role, size)
    line_height = (ascent + descent) * line_spacing
    block_w = int(round(max(widths) if widths else 1))
    block_h = int(round(line_height * len(lines)))
    pad = effects.padding(size)
    tile_w = block_w + 2 * pad
    tile_h = block_h + 2 * pad

    text_layer = Image.new('RGBA', (tile_w, tile_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    fill = _rgba(color, effects.opacity)

    stroke_width = int(round(effects.stroke * size)) if effects.stroke > 0 else 0
    silhouette = None
    if stroke_width > 0 or effects.shadow > 0 or effects.glow > 0:
        silhouette = Image.new('RGBA', (tile_w, tile_h), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(silhouette)

    for i, line in enumerate(lines):
        baseline = pad + ascent + i * line_height
        if align == 'left':
            x = pad
        elif align == 'right':
            x = pad + block_w - widths[i]
        else:
            x = pad + (block_w - widths[i]) / 2.0
        if silhouette is not None:
            _draw_run(sdraw, x, baseline, line, book, role, size,
                      (255, 255, 255, 255), tracking_px,
                      stroke_width=stroke_width,
                      stroke_fill=(255, 255, 255, 255) if stroke_width else None)
        _draw_run(draw, x, baseline, line, book, role, size, fill, tracking_px)

    out = Image.new('RGBA', (tile_w, tile_h), (0, 0, 0, 0))
    mask = silhouette.split()[3] if silhouette is not None else None

    if effects.glow > 0 and mask is not None:
        radius = max(1.0, effects.glow_radius * size)
        glow_mask = mask.filter(ImageFilter.GaussianBlur(radius))
        glow_mask = glow_mask.point(
            lambda v: int(min(255, v * (1.4 * effects.glow))))
        glow_layer = Image.new('RGBA', (tile_w, tile_h),
                               _rgba(effects.glow_color, 1.0)[:3] + (0,))
        glow_layer.putalpha(glow_mask)
        out.alpha_composite(glow_layer)

    if effects.shadow > 0 and mask is not None:
        blur = max(0.5, effects.shadow_blur * size)
        offset = int(round(effects.shadow_offset * size))
        shadow_mask = mask.filter(ImageFilter.GaussianBlur(blur))
        shadow_mask = shadow_mask.point(
            lambda v: int(min(255, v * min(2.0, 1.15 * effects.shadow))))
        shifted = Image.new('L', (tile_w, tile_h), 0)
        shifted.paste(shadow_mask, (offset, offset))
        shadow_layer = Image.new('RGBA', (tile_w, tile_h),
                                 _rgba(effects.shadow_color, 1.0)[:3] + (0,))
        shadow_layer.putalpha(shifted)
        out.alpha_composite(shadow_layer)

    if stroke_width > 0 and silhouette is not None:
        stroke_layer = Image.new('RGBA', (tile_w, tile_h),
                                 _rgba(effects.stroke_color, 1.0)[:3] + (0,))
        stroke_layer.putalpha(silhouette.split()[3])
        out.alpha_composite(stroke_layer)

    out.alpha_composite(text_layer)

    ink = text_layer.getbbox() or (pad, pad, pad + block_w, pad + block_h)
    return TextBlock(out, ink, size, lines)


def render_vertical(text, book, measurer, role, size, color='#FFFFFF',
                    line_spacing=1.05, effects=None, max_height=None,
                    min_size=10):
    """Render *text* as a single top-to-bottom column (wuxia style)."""
    effects = effects or Effects()
    text = ''.join(ch for ch in (text or '') if not ch.isspace())
    if not text:
        return None
    if max_height:
        while size > min_size and len(text) * size * line_spacing > max_height:
            size -= 1
    step = size * line_spacing
    col_w = int(round(max(measurer.advance(c, role, size) for c in text)))
    col_h = int(round(step * len(text)))
    pad = effects.padding(size)
    tile = Image.new('RGBA', (col_w + 2 * pad, col_h + 2 * pad), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    silhouette = Image.new('RGBA', tile.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(silhouette)
    stroke_width = int(round(effects.stroke * size)) if effects.stroke > 0 else 0
    fill = _rgba(color, effects.opacity)
    cx = pad + col_w / 2.0
    for i, ch in enumerate(text):
        font = book.font_for_char(ch, role, size)
        y = pad + i * step + step / 2.0
        sdraw.text((cx, y), ch, font=font, fill=(255, 255, 255, 255),
                   anchor='mm', stroke_width=stroke_width,
                   stroke_fill=(255, 255, 255, 255) if stroke_width else None)
        draw.text((cx, y), ch, font=font, fill=fill, anchor='mm')

    out = Image.new('RGBA', tile.size, (0, 0, 0, 0))
    mask = silhouette.split()[3]
    if effects.glow > 0:
        gm = mask.filter(ImageFilter.GaussianBlur(max(1.0, effects.glow_radius * size)))
        gm = gm.point(lambda v: int(min(255, v * (1.4 * effects.glow))))
        layer = Image.new('RGBA', tile.size, _rgba(effects.glow_color)[:3] + (0,))
        layer.putalpha(gm)
        out.alpha_composite(layer)
    if effects.shadow > 0:
        sm = mask.filter(ImageFilter.GaussianBlur(max(0.5, effects.shadow_blur * size)))
        sm = sm.point(lambda v: int(min(255, v * min(2.0, 1.15 * effects.shadow))))
        offset = int(round(effects.shadow_offset * size))
        shifted = Image.new('L', tile.size, 0)
        shifted.paste(sm, (offset, offset))
        layer = Image.new('RGBA', tile.size, _rgba(effects.shadow_color)[:3] + (0,))
        layer.putalpha(shifted)
        out.alpha_composite(layer)
    if stroke_width > 0:
        layer = Image.new('RGBA', tile.size, _rgba(effects.stroke_color)[:3] + (0,))
        layer.putalpha(mask)
        out.alpha_composite(layer)
    out.alpha_composite(tile)
    ink = tile.getbbox() or (pad, pad, pad + col_w, pad + col_h)
    return TextBlock(out, ink, size, [text])
