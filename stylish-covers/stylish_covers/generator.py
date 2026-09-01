#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The rendering engine.

Everything in this module is pure Pillow: it knows nothing about calibre or
Qt, which makes it testable from a plain python prompt and reusable outside of
calibre.  The GUI layer only ever hands it a dict of settings and a BookInfo.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from PIL import Image, ImageDraw

from . import badges
from . import imageops
from . import presets as presets_mod
from . import textfx
from .fonts import FontBook
from .textfx import Effects


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

class BookInfo(object):
    """The text the cover needs, already resolved from calibre metadata."""

    def __init__(self, title='', authors='', series='', series_index='',
                 asian_title='', subtitle=''):
        self.title = title or ''
        self.authors = authors or ''
        self.series = series or ''
        self.series_index = series_index or ''
        self.asian_title = asian_title or ''
        self.subtitle = subtitle or ''

    def copy(self):
        return BookInfo(self.title, self.authors, self.series,
                        self.series_index, self.asian_title, self.subtitle)

    def __repr__(self):
        return 'BookInfo(%r, %r)' % (self.title, self.authors)


SETTINGS_DEFAULTS = {
    # OUTPUT
    'width': 1600,
    'height': 2400,
    'quality': 92,
    'output_format': 'JPEG',

    # STYLE
    'preset': presets_mod.DEFAULT_PRESET,
    'title_position': 'auto',      # auto|top|upper|center|lower|bottom
    'author_position': 'auto',     # auto|under_title|bottom
    'title_size_scale': 1.0,
    'author_size_scale': 1.0,
    'title_max_lines': 0,          # 0 = use the preset value
    'title_case': 'auto',          # auto|upper|none
    'show_series': True,
    'show_author': True,

    # FONTS (paths to user supplied .ttf/.otf, empty = automatic)
    'font_title': '',
    'font_author': '',
    'font_cjk': '',

    # EFFECTS (multipliers applied on top of the preset, 1.0 = as designed)
    'shadow': 1.0,
    'stroke': 1.0,
    'glow': 1.0,
    'gradient': 1.0,
    'auto_contrast': True,

    # ASIAN TITLE
    'asian_enabled': False,
    'asian_mode': 'auto',          # auto|horizontal|vertical
    'asian_source': 'column',      # column|manual
    'asian_column': '#original_title',
    'asian_text': '',
    'asian_size_scale': 1.0,

    # METADATA (calibre template language, empty = plain field)
    'title_template': '',
    'author_template': '',
    'author_swap': False,
    'mark_column': '',
    'mark_value': '',

    # BADGE (your own mark, stamped in the margins the presets keep free)
    'badge_enabled': False,
    'badge_preset': badges.DEFAULT_BADGE,
    'badge_text': '',
    'badge_side': 'auto',          # auto|left|right, or tl|tr|bl|br for a seal
    'badge_size_scale': 1.0,
    'badge_opacity': 1.0,
    'badge_color': '',             # empty = the badge's own colour
    'badge_ornament': True,
    'badge_scrim': True,
    'user_badges': {},

    # KOBO (writing covers onto a connected device)
    'kobo_use_driver_settings': True,
    'kobo_keep_aspect': True,
    'kobo_grayscale': False,
    'kobo_png': False,
    'kobo_dithered': False,
    'kobo_letterbox': False,
    'kobo_letterbox_color': '#000000',
    'kobo_match_by_uuid_only': False,

    # BEHAVIOUR
    'backup_covers': True,
    'image_library': '',
    'saved_styles': {},
    'user_presets': {},
}


def merged_settings(settings=None):
    out = dict(SETTINGS_DEFAULTS)
    out.update(settings or {})
    return out


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _apply_case(text, case):
    if not text:
        return text
    if case == 'upper':
        return text.upper()
    if case == 'lower':
        return text.lower()
    return text


def _format_index(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value or '')
    return str(int(number)) if abs(number - int(number)) < 1e-6 else ('%g' % number)


def _series_text(book, style):
    if not book.series:
        return ''
    template = style.get('format') or '{series} #{index}'
    index = _format_index(book.series_index)
    try:
        text = template.format(series=book.series, index=index)
    except (KeyError, IndexError, ValueError):
        text = '%s #%s' % (book.series, index)
    if not index:
        text = text.replace('#', '').replace('  ', ' ').strip()
    return text.strip()


def _effects_for(preset, element, scales, boost=0.0):
    """Build an Effects object from the preset, user scales and contrast boost."""
    params = dict(preset.get('effects', {}).get(element, {}))
    fx = Effects(**params)
    fx.shadow *= scales.get('shadow', 1.0) * (1.0 + 0.85 * boost)
    fx.glow *= scales.get('glow', 1.0) * (1.0 + 0.70 * boost)
    if fx.stroke > 0:
        fx.stroke *= scales.get('stroke', 1.0) * (1.0 + 0.55 * boost)
    elif boost > 0.45 and scales.get('stroke', 1.0) > 0:
        # bright, busy background and the preset has no outline: add a hairline
        fx.stroke = 0.006 * scales.get('stroke', 1.0) * boost
        fx.stroke_color = '#0A0A0F'
    return fx


def _rule_block(width_px, thickness_px, color, opacity):
    thickness_px = max(1, int(round(thickness_px)))
    width_px = max(2, int(round(width_px)))
    tile = Image.new('RGBA', (width_px, thickness_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    draw.rectangle([0, 0, width_px - 1, thickness_px - 1],
                   fill=textfx._rgba(color, opacity))
    return textfx.TextBlock(tile, (0, 0, width_px, thickness_px), thickness_px, [])


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

class _Layout(object):
    """Resolves preset + settings into the concrete stack of blocks."""

    def __init__(self, preset, settings, book, width, height):
        self.preset = preset
        self.settings = settings
        self.book = book
        self.W = width
        self.H = height
        self.book_fonts = FontBook(
            title=settings.get('font_title') or None,
            author=settings.get('font_author') or None,
            cjk=settings.get('font_cjk') or None,
            title_role=preset.get('font_roles', {}).get('title', 'serif'),
            author_role=preset.get('font_roles', {}).get('author', 'sans'))
        # settle the CJK face once, before anything is measured
        self.book_fonts.use_best_cjk_for(' '.join(
            filter(None, (book.title, book.authors, book.series,
                          book.asian_title))))
        self.measurer = textfx.Measurer(self.book_fonts)
        self.groups = self._resolve_groups()
        self.asian_text = self._asian_text()

    # -- element texts -----------------------------------------------------
    def _asian_text(self):
        if not self.settings.get('asian_enabled'):
            return ''
        return (self.book.asian_title or '').strip()

    def _asian_is_vertical(self):
        mode = self.settings.get('asian_mode', 'auto')
        if mode == 'vertical':
            return True
        if mode == 'horizontal':
            return False
        return self.preset.get('asian', {}).get('mode') == 'vertical_right'

    def text_for(self, element):
        if element == 'title':
            case = self.settings.get('title_case', 'auto')
            if case == 'auto':
                case = self.preset['title'].get('case', 'none')
            return _apply_case(self.book.title, case)
        if element == 'author':
            if not self.settings.get('show_author', True):
                return ''
            return _apply_case(self.book.authors,
                               self.preset['author'].get('case', 'none'))
        if element == 'series':
            if not self.settings.get('show_series', True):
                return ''
            return _apply_case(_series_text(self.book, self.preset['series']),
                               self.preset['series'].get('case', 'none'))
        if element == 'asian':
            if self._asian_is_vertical():
                return ''  # drawn separately, outside of the stack
            return self.asian_text
        return ''

    # -- group geometry ----------------------------------------------------
    def _resolve_groups(self):
        groups = [dict(g) for g in self.preset['groups']]
        for g in groups:
            g['order'] = list(g['order'])

        pos = self.settings.get('title_position', 'auto')
        if pos != 'auto':
            anchor, edge = {
                'top': ('top', 0.055),
                'upper': ('top', 0.200),
                'center': ('center', 0.500),
                'lower': ('bottom', 0.780),
                'bottom': ('bottom', 0.930),
            }[pos]
            for g in groups:
                if 'title' in g['order']:
                    g['anchor'], g['edge'] = anchor, edge

        apos = self.settings.get('author_position', 'auto')
        if apos != 'auto':
            for g in groups:
                if 'author' in g['order']:
                    g['order'].remove('author')
            if apos == 'under_title':
                for g in groups:
                    if 'title' in g['order']:
                        insert_at = g['order'].index('title') + 1
                        if 'rule' in g['order']:
                            insert_at = g['order'].index('rule') + 1
                        g['order'].insert(insert_at, 'author')
                        break
            else:  # bottom
                target = None
                for g in groups:
                    if g['anchor'] == 'bottom' and 'title' not in g['order']:
                        target = g
                        break
                if target is None:
                    target = {'anchor': 'bottom', 'edge': 0.945,
                              'align': 'center', 'margin': 0.09, 'order': []}
                    groups.append(target)
                target['order'].append('author')
        return [g for g in groups if g['order']]

    # -- block construction ------------------------------------------------
    def build_blocks(self, boost_map=None):
        """Render every block; returns a list of (group, [(element, block)])."""
        boost_map = boost_map or {}
        scales = {
            'shadow': float(self.settings.get('shadow', 1.0)),
            'stroke': float(self.settings.get('stroke', 1.0)),
            'glow': float(self.settings.get('glow', 1.0)),
        }
        out = []
        for gi, group in enumerate(self.groups):
            max_width = self.W * (1.0 - 2.0 * group.get('margin', 0.09))
            blocks = []
            for element in group['order']:
                boost = boost_map.get((gi, element), 0.0)
                block = self._build_block(element, max_width, group, scales, boost)
                if block is not None:
                    blocks.append((element, block))
            # a rule with nothing above and below it is pointless
            blocks = [(e, b) for e, b in blocks
                      if e != 'rule' or len(blocks) > 1]
            if blocks:
                out.append((group, blocks))
        return out

    def _build_block(self, element, max_width, group, scales, boost):
        style = self.preset.get(element, {})
        if element == 'rule':
            if not style.get('enabled'):
                return None
            return _rule_block(self.W * style.get('width', 0.15),
                               self.W * style.get('thickness', 0.0024),
                               style.get('color', '#FFFFFF'),
                               style.get('opacity', 0.8))

        text = self.text_for(element)
        if not text:
            return None

        if element == 'title':
            scale = float(self.settings.get('title_size_scale', 1.0))
            max_lines = int(self.settings.get('title_max_lines') or
                            style.get('max_lines', 3))
            role = self.book_fonts.best_role_for(text, 'title')
            max_size = self.W * style.get('size', 0.10) * scale
            min_size = self.W * style.get('min_size', 0.030)
        elif element == 'asian':
            scale = float(self.settings.get('asian_size_scale', 1.0))
            max_lines = 2
            role = 'cjk'
            max_size = self.W * style.get('size', 0.045) * scale
            min_size = self.W * 0.020
        else:
            scale = float(self.settings.get('author_size_scale', 1.0))
            max_lines = 2
            role = self.book_fonts.best_role_for(text, 'author')
            max_size = self.W * style.get('size', 0.032) * scale
            min_size = self.W * 0.016

        tracking = style.get('tracking', 0.0)
        line_spacing = style.get('line_spacing', 1.10)
        lines, size = textfx.fit_text(
            text, self.measurer, role, max_width, max_lines=max_lines,
            max_size=max(min_size + 1, max_size), min_size=min_size,
            tracking=tracking, line_spacing=line_spacing,
            max_height=self.H * style.get('max_height',
                                          0.42 if element == 'title' else 0.16))
        if not lines:
            return None
        return textfx.render_block(
            lines, self.book_fonts, self.measurer, role, size,
            color=style.get('color', '#FFFFFF'), tracking=tracking,
            line_spacing=style.get('line_spacing', 1.10),
            align=group.get('align', 'center'),
            effects=_effects_for(self.preset, element, scales, boost))

    # -- placement ---------------------------------------------------------
    def place(self, built):
        """Compute (group_index, element, block, x, y, anchor) for each block."""
        placements = []
        for gi, (group, blocks) in enumerate(built):
            gaps = []
            for i, (element, block) in enumerate(blocks):
                gap = 0.0 if i == 0 else self.W * self.preset.get(
                    element, {}).get('gap', 0.03)
                gaps.append(gap)
            total = sum(b.height for _e, b in blocks) + sum(gaps)
            edge = group['edge'] * self.H
            anchor = group.get('anchor', 'bottom')
            if anchor == 'top':
                y = edge
            elif anchor == 'center':
                y = edge - total / 2.0
            else:
                y = edge - total
            align = group.get('align', 'center')
            margin = self.W * group.get('margin', 0.09)
            if align == 'left':
                x, text_anchor = margin, 'left-top'
            elif align == 'right':
                x, text_anchor = self.W - margin, 'right-top'
            else:
                x, text_anchor = self.W / 2.0, 'center-top'
            for i, (element, block) in enumerate(blocks):
                y += gaps[i]
                placements.append((gi, element, block, x, y, text_anchor))
                y += block.height
        return placements

    @staticmethod
    def element_rects(placements):
        """Bounding box per (group index, element), in canvas pixels."""
        rects = {}
        for gi, element, block, x, y, anchor in placements:
            if anchor.startswith('center'):
                x0, x1 = x - block.width / 2.0, x + block.width / 2.0
            elif anchor.startswith('right'):
                x0, x1 = x - block.width, x
            else:
                x0, x1 = x, x + block.width
            rects[(gi, element)] = (x0, y, x1, y + block.height)
        return rects

    @staticmethod
    def union(rects):
        """Union of an iterable of boxes, or None."""
        boxes = list(rects)
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))


# --------------------------------------------------------------------------
# Public rendering entry points
# --------------------------------------------------------------------------

def build_background(image_source, preset, width, height):
    """Artwork scaled and graded, ready to receive the typography."""
    img = None
    if image_source is not None:
        try:
            img = imageops.load_image(image_source)
        except Exception:
            img = None
    if img is None:
        base = imageops.placeholder(width, height)
    else:
        cfg = preset.get('image', {})
        if cfg.get('mode') == 'contain':
            base = imageops.compose_contain(img, width, height)
        else:
            base = imageops.smart_fit(img, width, height,
                                      focus=cfg.get('focus', 'center'),
                                      zoom=cfg.get('zoom', 1.0))
    cfg = preset.get('image', {})
    return imageops.grade(base,
                          darken=cfg.get('darken', 0.0),
                          saturation=cfg.get('saturation', 1.0),
                          contrast=cfg.get('contrast', 1.0),
                          vignette=cfg.get('vignette', 0.0))


def _apply_scrims(canvas, preset, gradient_scale, extra_alpha=0.0):
    for scrim in preset.get('scrims', []):
        alpha = min(0.94, scrim.get('alpha', 0.6) * gradient_scale + extra_alpha)
        if alpha <= 0.005:
            continue
        layer = imageops.gradient_overlay(
            canvas.width, canvas.height, side=scrim.get('side', 'bottom'),
            extent=scrim.get('extent', 0.5), alpha=alpha,
            curve=scrim.get('curve', 1.8))
        canvas.alpha_composite(layer)
    return canvas


def render_cover(image_source, book, settings=None, preset=None):
    """Render one cover and return it as a PIL RGB image."""
    settings = merged_settings(settings)
    if preset is None:
        preset = presets_mod.get_preset(settings.get('preset'),
                                        settings.get('user_presets'))
    width = max(200, int(settings.get('width', 1600)))
    height = max(200, int(settings.get('height', 2400)))
    gradient_scale = float(settings.get('gradient', 1.0))

    background = build_background(image_source, preset, width, height)
    layout = _Layout(preset, settings, book, width, height)

    # --- pass 1: provisional layout, used only to probe the background ----
    built = layout.build_blocks()
    rects = layout.element_rects(layout.place(built))

    boost_map, extra_alpha = {}, 0.0
    if settings.get('auto_contrast', True):
        probe = _ensure_rgba(background.copy())
        _apply_scrims(probe, preset, gradient_scale)
        probe_rgb = probe.convert('RGB')
        for key, rect in rects.items():
            mean, sd = imageops.region_luminance(probe_rgb, rect)
            # bright backgrounds hurt, busy ones hurt a little too
            boost = max(0.0, min(1.0, (mean - 0.34) / 0.42))
            boost_map[key] = min(1.0, boost + max(0.0, sd - 0.22) * 0.9)
        if boost_map:
            extra_alpha = 0.30 * max(boost_map.values())

    # --- pass 2: final render ---------------------------------------------
    canvas = _ensure_rgba(background)
    _apply_scrims(canvas, preset, gradient_scale, extra_alpha)

    if settings.get('auto_contrast', True):
        # one soft band per group, covering the elements that need help
        for gi in set(key[0] for key in boost_map):
            hard = [rect for key, rect in rects.items()
                    if key[0] == gi and boost_map.get(key, 0.0) > 0.45]
            box = layout.union(hard)
            if box is None:
                continue
            strength = max(boost_map[key] for key in boost_map if key[0] == gi)
            pad = (box[3] - box[1]) * 0.40
            canvas.alpha_composite(imageops.band_overlay(
                width, height, box[1] - pad, box[3] + pad,
                alpha=0.30 * strength * max(0.4, gradient_scale)))

    built = layout.build_blocks(boost_map)
    for _gi, _element, block, x, y, anchor in layout.place(built):
        block.paste_on(canvas, x, y, anchor)

    _draw_vertical_asian(canvas, layout, preset, settings)
    badges.draw_badge(canvas, settings, layout.book_fonts, layout.measurer)
    return canvas.convert('RGB')


def _ensure_rgba(img):
    return img if img.mode == 'RGBA' else img.convert('RGBA')


def _draw_vertical_asian(canvas, layout, preset, settings):
    if not layout.asian_text or not layout._asian_is_vertical():
        return
    style = preset.get('asian', {})
    scales = {
        'shadow': float(settings.get('shadow', 1.0)),
        'stroke': float(settings.get('stroke', 1.0)),
        'glow': float(settings.get('glow', 1.0)),
    }
    size = canvas.width * style.get('size', 0.07) * \
        float(settings.get('asian_size_scale', 1.0))
    block = textfx.render_vertical(
        layout.asian_text, layout.book_fonts, layout.measurer, 'cjk', size,
        color=style.get('color', '#FFFFFF'),
        line_spacing=style.get('line_spacing', 1.10),
        effects=_effects_for(preset, 'asian', scales, 0.15),
        max_height=canvas.height * style.get('max_height', 0.6),
        min_size=canvas.width * 0.025)
    if block is not None:
        block.paste_on(canvas, canvas.width * style.get('x', 0.86),
                       canvas.height * style.get('top', 0.09), 'center-top')


def render_cover_bytes(image_source, book, settings=None, preset=None):
    """Render one cover and return encoded bytes ready for calibre."""
    settings = merged_settings(settings)
    img = render_cover(image_source, book, settings, preset)
    return imageops.to_bytes(img, settings.get('output_format', 'JPEG'),
                             settings.get('quality', 92))


def stamp_badge(image_source, settings=None):
    """Draw only the badge on an existing cover, keeping its own size.

    Used by "Apply badge to existing covers": the artwork is not regenerated,
    nothing is re-laid out, the mark is simply added.
    """
    settings = merged_settings(settings)
    canvas = _ensure_rgba(imageops.load_image(image_source))
    book_fonts = FontBook(
        title=settings.get('font_title') or None,
        author=settings.get('font_author') or None,
        cjk=settings.get('font_cjk') or None)
    measurer = textfx.Measurer(book_fonts)
    badges.draw_badge(canvas, settings, book_fonts, measurer)
    return canvas.convert('RGB')


def stamp_badge_bytes(image_source, settings=None):
    settings = merged_settings(settings)
    img = stamp_badge(image_source, settings)
    return imageops.to_bytes(img, settings.get('output_format', 'JPEG'),
                             settings.get('quality', 92))
