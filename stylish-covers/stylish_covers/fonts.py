#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Font discovery, Unicode coverage detection and automatic fallback.

This module is completely independent from calibre and from Qt: it only needs
the standard library plus Pillow.  It is what allows the generator to render a
latin title with a serif display face while still drawing the CJK subtitle with
a font that actually owns the glyphs.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import struct
import sys
from bisect import bisect_right

try:
    from PIL import ImageFont
except ImportError:  # pragma: no cover - calibre always bundles Pillow
    ImageFont = None


# --------------------------------------------------------------------------
# System font locations
# --------------------------------------------------------------------------

def _font_dirs():
    dirs = []
    if sys.platform == 'win32':
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        dirs.append(os.path.join(windir, 'Fonts'))
        local = os.environ.get('LOCALAPPDATA')
        if local:
            dirs.append(os.path.join(local, 'Microsoft', 'Windows', 'Fonts'))
    elif sys.platform == 'darwin':
        dirs += ['/System/Library/Fonts', '/System/Library/Fonts/Supplemental',
                 '/Library/Fonts', os.path.expanduser('~/Library/Fonts')]
    else:
        dirs += ['/usr/share/fonts', '/usr/local/share/fonts',
                 os.path.expanduser('~/.local/share/fonts'),
                 os.path.expanduser('~/.fonts')]
    return [d for d in dirs if d and os.path.isdir(d)]


_INDEX_CACHE = None

FONT_EXTENSIONS = ('.ttf', '.otf', '.ttc', '.otc')


def system_font_index():
    """Map lowercase file base name -> full path for every installed font."""
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    index = {}
    for root_dir in _font_dirs():
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in FONT_EXTENSIONS:
                    index.setdefault(os.path.splitext(fn)[0].lower(),
                                     os.path.join(dirpath, fn))
            if len(index) > 20000:
                break
    _INDEX_CACHE = index
    return index


def find_system_font(*basenames):
    """Path of the first installed font file matching one of *basenames*."""
    index = system_font_index()
    for name in basenames:
        key = name.lower()
        if key in index:
            return index[key]
    # tolerant second pass: prefix match (georgia -> georgiab, malgun -> malgunbd)
    for name in basenames:
        key = name.lower()
        for have in sorted(index):
            if have.startswith(key):
                return index[have]
    return None


# Candidate lists per typographic role.  Windows first (priority platform),
# then macOS, then the usual free/linux faces.
ROLE_CANDIDATES = {
    'serif': ['constanb', 'constan', 'georgiab', 'georgia', 'cambriab',
              'cambria', 'pala', 'timesbd', 'times', 'Baskerville', 'Didot',
              'EBGaramond-Regular', 'DejaVuSerif', 'LiberationSerif-Regular',
              'NotoSerif-Regular'],
    'serif_bold': ['constanb', 'georgiab', 'cambriab', 'timesbd',
                   'DejaVuSerif-Bold', 'LiberationSerif-Bold', 'NotoSerif-Bold'],
    'display': ['bahnschrift', 'seguibl', 'arlrdbd', 'impact', 'ariblk',
                'framdit', 'HelveticaNeue', 'DejaVuSans-Bold',
                'LiberationSans-Bold', 'NotoSans-Bold'],
    'sans': ['segoeui', 'calibri', 'arial', 'Helvetica', 'DejaVuSans',
             'LiberationSans-Regular', 'NotoSans-Regular'],
    'sans_bold': ['seguisb', 'segoeuib', 'calibrib', 'arialbd', 'HelveticaNeue',
                  'DejaVuSans-Bold', 'LiberationSans-Bold', 'NotoSans-Bold'],
    # Korean / Simplified / Traditional / Japanese, then Noto CJK
    'cjk': ['malgunbd', 'malgun', 'msyhbd', 'msyh', 'msjhbd', 'msjh',
            'yugothb', 'yugothm', 'meiryob', 'meiryo', 'simhei', 'simsun',
            'AppleSDGothicNeo', 'HiraginoSans', 'NotoSansCJKsc-Bold',
            'NotoSansCJK-Regular', 'NotoSansKR-Bold', 'NotoSansSC-Bold',
            'SourceHanSans'],
}


def role_font(role):
    """Best available system font path for a typographic role."""
    return find_system_font(*ROLE_CANDIDATES.get(role, ROLE_CANDIDATES['sans']))


def role_chain(role, limit=10):
    """Every installed font for a role, in preference order, deduplicated.

    A single CJK face is never enough: Malgun Gothic covers hangul but only a
    fraction of the ideographs, YaHei covers simplified chinese but not kana.
    Walking a chain is what stops missing glyphs from rendering as tofu boxes.
    """
    chain, seen = [], set()
    for name in ROLE_CANDIDATES.get(role, ()):
        path = find_system_font(name)
        if path and path.lower() not in seen:
            seen.add(path.lower())
            chain.append(path)
        if len(chain) >= limit:
            break
    return chain


# --------------------------------------------------------------------------
# Unicode coverage: minimal sfnt "cmap" reader (formats 4, 6 and 12)
# --------------------------------------------------------------------------

class Coverage(object):
    """Sorted, non overlapping codepoint ranges supporting fast lookup."""

    __slots__ = ('starts', 'ends')

    def __init__(self, ranges):
        merged = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1] + 1:
                if end > merged[-1][1]:
                    merged[-1][1] = end
            else:
                merged.append([start, end])
        self.starts = [r[0] for r in merged]
        self.ends = [r[1] for r in merged]

    def __bool__(self):
        return bool(self.starts)

    __nonzero__ = __bool__

    def __contains__(self, codepoint):
        i = bisect_right(self.starts, codepoint) - 1
        return i >= 0 and codepoint <= self.ends[i]

    def covers(self, text, threshold=1.0):
        """True when at least *threshold* of the printable chars are present."""
        chars = [c for c in text if not c.isspace()]
        if not chars:
            return True
        if not self.starts:
            return False
        hits = sum(1 for c in chars if ord(c) in self)
        return (hits / float(len(chars))) >= threshold


_EMPTY_COVERAGE = Coverage([])
_COVERAGE_CACHE = {}


def _table_offset(data, base, tag):
    num_tables = struct.unpack_from('>H', data, base + 4)[0]
    for i in range(num_tables):
        rec = base + 12 + 16 * i
        if data[rec:rec + 4] == tag:
            return struct.unpack_from('>I', data, rec + 8)[0]
    return None


def _parse_format4(data, off):
    seg_x2 = struct.unpack_from('>H', data, off + 6)[0]
    seg = seg_x2 // 2
    ends = struct.unpack_from('>%dH' % seg, data, off + 14)
    starts = struct.unpack_from('>%dH' % seg, data, off + 16 + seg_x2)
    return [(s, e) for s, e in zip(starts, ends) if s <= e and s != 0xffff]


def _parse_format6(data, off):
    first, count = struct.unpack_from('>HH', data, off + 6)
    return [(first, first + count - 1)] if count else []


def _parse_format12(data, off):
    n_groups = min(struct.unpack_from('>I', data, off + 12)[0], 200000)
    out = []
    for i in range(n_groups):
        start, end, _glyph = struct.unpack_from('>III', data, off + 16 + 12 * i)
        if start <= end:
            out.append((start, end))
    return out


# Preference score per (platformID, encodingID); higher is better.
_CMAP_SCORES = {(3, 10): 5, (0, 4): 5, (0, 6): 5, (3, 1): 4, (0, 3): 4,
                (0, 2): 3, (0, 1): 3, (3, 0): 1}


def font_coverage(path):
    """Unicode Coverage of the font file at *path* (cached, never raises)."""
    if not path:
        return _EMPTY_COVERAGE
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        return _EMPTY_COVERAGE
    cached = _COVERAGE_CACHE.get(key)
    if cached is not None:
        return cached
    cov = _EMPTY_COVERAGE
    try:
        with open(path, 'rb') as f:
            data = f.read()
        base = 12 if data[:4] == b'ttcf' else 0
        if base:
            base = struct.unpack_from('>I', data, 12)[0]
        cmap = _table_offset(data, base, b'cmap')
        if cmap is not None:
            n = struct.unpack_from('>H', data, cmap + 2)[0]
            best, best_score = None, -1
            for i in range(n):
                pid, eid, sub = struct.unpack_from('>HHI', data, cmap + 4 + 8 * i)
                score = _CMAP_SCORES.get((pid, eid), 0)
                if score > best_score:
                    best, best_score = cmap + sub, score
            if best is not None:
                fmt = struct.unpack_from('>H', data, best)[0]
                if fmt == 4:
                    cov = Coverage(_parse_format4(data, best))
                elif fmt == 6:
                    cov = Coverage(_parse_format6(data, best))
                elif fmt == 12:
                    cov = Coverage(_parse_format12(data, best))
    except Exception:
        cov = _EMPTY_COVERAGE
    _COVERAGE_CACHE[key] = cov
    return cov


def font_has(path, text, threshold=1.0):
    return font_coverage(path).covers(text, threshold)


# --------------------------------------------------------------------------
# FontBook: resolution + per character fallback
# --------------------------------------------------------------------------

class FontError(Exception):
    pass


class FontBook(object):
    """Resolves the fonts used by one render and caches sized instances.

    *title*, *author* and *cjk* are optional paths to user supplied .ttf/.otf
    files.  Whatever is missing is replaced by a sensible system face.
    """

    def __init__(self, title=None, author=None, cjk=None, title_role='serif',
                 author_role='sans'):
        chain = role_chain('cjk')
        if cjk and os.path.isfile(cjk):
            chain = [cjk] + [p for p in chain if p != cjk]
        self.cjk_chain = chain
        self.paths = {
            'title': self._resolve(title, title_role),
            'author': self._resolve(author, author_role),
            'cjk': chain[0] if chain else self._resolve(cjk, 'cjk'),
        }
        self._sized = {}
        self._char_font = {}

    @staticmethod
    def _resolve(path, role):
        if path and os.path.isfile(path):
            return path
        return role_font(role)

    def _load(self, path, size):
        size = max(1, int(round(size)))
        key = (path, size)
        font = self._sized.get(key)
        if font is None:
            if ImageFont is None:
                raise FontError('Pillow is not available')
            try:
                font = ImageFont.truetype(path, size)
            except Exception:
                fallback = role_font('sans')
                if fallback and fallback != path:
                    try:
                        font = ImageFont.truetype(fallback, size)
                    except Exception:
                        font = ImageFont.load_default()
                else:
                    font = ImageFont.load_default()
            self._sized[key] = font
        return font

    def font(self, role, size):
        path = self.paths.get(role) or self.paths.get('author') or self.paths.get('cjk')
        if not path:
            raise FontError(
                'No usable font was found on this system. Pick a .ttf/.otf '
                'file in the plugin settings (Fonts tab).')
        return self._load(path, size)

    def path_for_char(self, char, role):
        """First font in the fallback chain that owns a glyph for *char*."""
        key = (char, role)
        cached = self._char_font.get(key)
        if cached is not None:
            return cached
        primary = self.paths.get(role)
        candidates = [primary] + self.cjk_chain + [self.paths.get('title'),
                                                   self.paths.get('author')]
        chosen = primary
        codepoint = ord(char)
        for path in candidates:
            if path and codepoint in font_coverage(path):
                chosen = path
                break
        self._char_font[key] = chosen
        return chosen

    def font_for_char(self, char, role, size):
        """Font instance able to draw *char*, walking the fallback chain."""
        primary = self.paths.get(role)
        if char.isspace() and primary:
            return self._load(primary, size)
        path = self.path_for_char(char, role)
        if not path:
            return self.font(role, size)
        return self._load(path, size)

    def use_best_cjk_for(self, text):
        """Promote the one chain font that covers every CJK char of *text*.

        Mixing two faces inside a single word looks wrong (different weights
        and side bearings), so a font that can draw the whole string is always
        preferable to per character fallback.  Call this before any measuring:
        it invalidates the per character cache.
        """
        wanted = [c for c in (text or '')
                  if not c.isspace() and ord(c) > 0x2E7F]
        if not wanted:
            return None
        for path in self.cjk_chain:
            coverage = font_coverage(path)
            if all(ord(c) in coverage for c in wanted):
                if self.paths.get('cjk') != path:
                    self.paths['cjk'] = path
                    self._char_font.clear()
                return path
        return None

    def covers(self, text, role):
        """True when every character of *text* has a glyph somewhere."""
        return all(c.isspace() or
                   ord(c) in font_coverage(self.path_for_char(c, role))
                   for c in text or '')

    def best_role_for(self, text, preferred):
        """Return "cjk" when *preferred* cannot render most of *text*."""
        path = self.paths.get(preferred)
        if path and font_has(path, text, threshold=0.9):
            return preferred
        return 'cjk' if self.paths.get('cjk') else preferred

    def describe(self):
        out = dict((k, os.path.basename(v) if v else None)
                   for k, v in self.paths.items())
        out['cjk_chain'] = [os.path.basename(p) for p in self.cjk_chain]
        return out
