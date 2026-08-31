#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cover presets.

A preset is plain data (no calibre, no Qt, no Pillow), which makes it trivial
to store user presets in the plugin configuration and to add new looks without
touching the rendering code.

Geometry is expressed in fractions so a preset renders identically at any
output resolution:
    * sizes, margins and gaps  -> fraction of the canvas WIDTH
    * vertical positions       -> fraction of the canvas HEIGHT
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

# --------------------------------------------------------------------------
# Preset 1 - Dark fantasy / Reverend Insanity
# --------------------------------------------------------------------------

DARK_FANTASY = {
    'id': 'dark_fantasy',
    'label': 'Dark Fantasy',
    'description': 'Illustration dominante, titre serif dans le tiers inferieur, '
                   'filet dore, ombre douce. Inspire des couvertures type '
                   'Reverend Insanity.',
    'font_roles': {'title': 'serif', 'author': 'sans'},
    'image': {'mode': 'fill', 'focus': 'upper', 'zoom': 1.0, 'darken': 0.06,
              'saturation': 0.97, 'contrast': 1.06, 'vignette': 0.38},
    'scrims': [
        {'side': 'bottom', 'extent': 0.58, 'alpha': 0.70, 'curve': 1.9},
    ],
    'groups': [
        {'anchor': 'bottom', 'edge': 0.915, 'align': 'center', 'margin': 0.100,
         'order': ['series', 'title', 'rule', 'author', 'asian']},
    ],
    'title': {'size': 0.108, 'max_lines': 3, 'tracking': 0.020,
              'line_spacing': 1.06, 'case': 'title', 'color': '#F5EFE1',
              'min_size': 0.038},
    'series': {'size': 0.026, 'gap': 0.028, 'tracking': 0.26, 'case': 'upper',
               'color': '#C7A65E', 'format': '{series} #{index}'},
    'rule': {'enabled': True, 'width': 0.15, 'thickness': 0.0024, 'gap': 0.030,
             'color': '#C7A65E', 'opacity': 0.75},
    'author': {'size': 0.034, 'gap': 0.040, 'tracking': 0.16, 'case': 'upper',
               'color': '#D3CABA'},
    'asian': {'size': 0.044, 'gap': 0.030, 'tracking': 0.12, 'color': '#B7AC96',
              'mode': 'below', 'opacity': 0.92},
    'effects': {
        'title': {'shadow': 0.80, 'shadow_offset': 0.028, 'shadow_blur': 0.075,
                  'stroke': 0.0, 'glow': 0.30, 'glow_color': '#000000',
                  'glow_radius': 0.16},
        'series': {'shadow': 0.70, 'shadow_offset': 0.05, 'shadow_blur': 0.12},
        'author': {'shadow': 0.70, 'shadow_offset': 0.04, 'shadow_blur': 0.10},
        'asian': {'shadow': 0.60, 'shadow_offset': 0.04, 'shadow_blur': 0.10},
    },
}

# --------------------------------------------------------------------------
# Preset 2 - Shadow Slave (modern webnovel)
# --------------------------------------------------------------------------

SHADOW_SLAVE = {
    'id': 'shadow_slave',
    'label': 'Shadow Slave',
    'description': 'Titre enorme en haut, typo bold tres lisible, contour leger '
                   'et drop shadow prononcee, auteur en bas.',
    'font_roles': {'title': 'display', 'author': 'sans_bold'},
    'image': {'mode': 'fill', 'focus': 'center', 'zoom': 1.0, 'darken': 0.05,
              'saturation': 1.02, 'contrast': 1.05, 'vignette': 0.26},
    'scrims': [
        {'side': 'top', 'extent': 0.46, 'alpha': 0.62, 'curve': 1.7},
        {'side': 'bottom', 'extent': 0.26, 'alpha': 0.55, 'curve': 2.0},
    ],
    'groups': [
        {'anchor': 'top', 'edge': 0.052, 'align': 'center', 'margin': 0.072,
         'order': ['title', 'series']},
        {'anchor': 'bottom', 'edge': 0.945, 'align': 'center', 'margin': 0.090,
         'order': ['asian', 'author']},
    ],
    'title': {'size': 0.195, 'max_lines': 3, 'tracking': -0.005,
              'line_spacing': 0.96, 'case': 'upper', 'color': '#FFFFFF',
              'min_size': 0.060},
    'series': {'size': 0.030, 'gap': 0.034, 'tracking': 0.30, 'case': 'upper',
               'color': '#C4C9D4', 'format': 'BOOK {index}'},
    'rule': {'enabled': False},
    'author': {'size': 0.040, 'gap': 0.030, 'tracking': 0.20, 'case': 'upper',
               'color': '#ECECEC'},
    'asian': {'size': 0.040, 'gap': 0.026, 'tracking': 0.14, 'color': '#C4C9D4',
              'mode': 'below', 'opacity': 0.9},
    'effects': {
        'title': {'shadow': 1.00, 'shadow_offset': 0.042, 'shadow_blur': 0.080,
                  'stroke': 0.016, 'stroke_color': '#0A0A0F',
                  'glow': 0.0},
        'series': {'shadow': 0.80, 'shadow_offset': 0.05, 'shadow_blur': 0.10},
        'author': {'shadow': 0.85, 'shadow_offset': 0.045, 'shadow_blur': 0.10,
                   'stroke': 0.008, 'stroke_color': '#0A0A0F'},
        'asian': {'shadow': 0.70, 'shadow_offset': 0.05, 'shadow_blur': 0.10},
    },
}

# --------------------------------------------------------------------------
# Preset 3 - Asian fantasy (wuxia / xianxia)
# --------------------------------------------------------------------------

ASIAN_FANTASY = {
    'id': 'asian_fantasy',
    'label': 'Asian Fantasy',
    'description': 'Titre latin principal, caracteres chinois/coreens en '
                   'decoration verticale sur le cote. Rendu wuxia / xianxia.',
    'font_roles': {'title': 'serif', 'author': 'sans'},
    'image': {'mode': 'fill', 'focus': 'center', 'zoom': 1.0, 'darken': 0.04,
              'saturation': 1.03, 'contrast': 1.04, 'vignette': 0.32},
    'scrims': [
        {'side': 'bottom', 'extent': 0.55, 'alpha': 0.64, 'curve': 1.9},
        {'side': 'right', 'extent': 0.30, 'alpha': 0.34, 'curve': 1.5},
    ],
    'groups': [
        {'anchor': 'bottom', 'edge': 0.905, 'align': 'center', 'margin': 0.115,
         'order': ['title', 'rule', 'author', 'series']},
    ],
    'title': {'size': 0.098, 'max_lines': 3, 'tracking': 0.055,
              'line_spacing': 1.10, 'case': 'title', 'color': '#F3EAD6',
              'min_size': 0.036},
    'series': {'size': 0.025, 'gap': 0.026, 'tracking': 0.28, 'case': 'upper',
               'color': '#B9976A', 'format': '{series} {index}'},
    'rule': {'enabled': True, 'width': 0.20, 'thickness': 0.0020, 'gap': 0.028,
             'color': '#B9976A', 'opacity': 0.70},
    'author': {'size': 0.032, 'gap': 0.032, 'tracking': 0.18, 'case': 'upper',
               'color': '#D8CDB6'},
    'asian': {'size': 0.075, 'mode': 'vertical_right', 'color': '#EFE4CC',
              'opacity': 0.95, 'x': 0.865, 'top': 0.085, 'max_height': 0.62,
              'line_spacing': 1.12, 'gap': 0.030, 'tracking': 0.10},
    'effects': {
        'title': {'shadow': 0.75, 'shadow_offset': 0.026, 'shadow_blur': 0.070,
                  'glow': 0.26, 'glow_color': '#000000', 'glow_radius': 0.16},
        'series': {'shadow': 0.65, 'shadow_offset': 0.05, 'shadow_blur': 0.11},
        'author': {'shadow': 0.70, 'shadow_offset': 0.04, 'shadow_blur': 0.10},
        'asian': {'shadow': 0.85, 'shadow_offset': 0.030, 'shadow_blur': 0.075,
                  'glow': 0.30, 'glow_color': '#000000', 'glow_radius': 0.18},
    },
}

# --------------------------------------------------------------------------
# Preset 4 - Minimal
# --------------------------------------------------------------------------

MINIMAL = {
    'id': 'minimal',
    'label': 'Minimal',
    'description': 'Priorite absolue a l illustration: petit titre propre, '
                   'auteur, quasiment aucun effet.',
    'font_roles': {'title': 'sans', 'author': 'sans'},
    'image': {'mode': 'fill', 'focus': 'center', 'zoom': 1.0, 'darken': 0.0,
              'saturation': 1.0, 'contrast': 1.0, 'vignette': 0.10},
    'scrims': [
        {'side': 'bottom', 'extent': 0.34, 'alpha': 0.52, 'curve': 2.2},
    ],
    'groups': [
        {'anchor': 'bottom', 'edge': 0.935, 'align': 'center', 'margin': 0.105,
         'order': ['title', 'author', 'asian', 'series']},
    ],
    'title': {'size': 0.064, 'max_lines': 2, 'tracking': 0.045,
              'line_spacing': 1.14, 'case': 'none', 'color': '#FFFFFF',
              'min_size': 0.030},
    'series': {'size': 0.022, 'gap': 0.020, 'tracking': 0.24, 'case': 'upper',
               'color': '#BFBFBF', 'format': '{series} #{index}'},
    'rule': {'enabled': False},
    'author': {'size': 0.028, 'gap': 0.026, 'tracking': 0.18, 'case': 'upper',
               'color': '#DCDCDC'},
    'asian': {'size': 0.032, 'gap': 0.022, 'tracking': 0.10, 'color': '#C8C8C8',
              'mode': 'below', 'opacity': 0.85},
    'effects': {
        'title': {'shadow': 0.45, 'shadow_offset': 0.016, 'shadow_blur': 0.050},
        'series': {'shadow': 0.40, 'shadow_offset': 0.03, 'shadow_blur': 0.08},
        'author': {'shadow': 0.40, 'shadow_offset': 0.03, 'shadow_blur': 0.08},
        'asian': {'shadow': 0.40, 'shadow_offset': 0.03, 'shadow_blur': 0.08},
    },
}


BUILTIN_PRESETS = [DARK_FANTASY, SHADOW_SLAVE, ASIAN_FANTASY, MINIMAL]
BUILTIN_IDS = [p['id'] for p in BUILTIN_PRESETS]
_BY_ID = dict((p['id'], p) for p in BUILTIN_PRESETS)

DEFAULT_PRESET = 'dark_fantasy'


def preset_choices(user_presets=None):
    """List of (id, label) for every available preset."""
    out = [(p['id'], p['label']) for p in BUILTIN_PRESETS]
    for pid, data in sorted((user_presets or {}).items()):
        out.append((pid, data.get('label', pid) + '  (custom)'))
    return out


def get_preset(preset_id, user_presets=None):
    """Deep copy of a preset, looked up in the built-ins then the user ones."""
    user_presets = user_presets or {}
    if preset_id in user_presets:
        base = get_preset(user_presets[preset_id].get('base', DEFAULT_PRESET))
        return deep_merge(base, copy.deepcopy(user_presets[preset_id]))
    return copy.deepcopy(_BY_ID.get(preset_id, _BY_ID[DEFAULT_PRESET]))


def deep_merge(base, override):
    """Recursively merge *override* into *base* (returns *base*, mutated)."""
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base
