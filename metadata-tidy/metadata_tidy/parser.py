#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Title parsing: pull the series name and the volume number out of a title.

Pure python, no calibre and no Qt, so the rules can be tested from a plain
prompt.  Everything is conservative on purpose: when a title is ambiguous the
parser returns nothing rather than inventing a series.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re

# --------------------------------------------------------------------------
# Volume keywords, french and english
# --------------------------------------------------------------------------

KEYWORDS = [
    'tomes?', 'livres?', 'volumes?', 'vol', 'tome', 't',
    'books?', 'parts?', 'parties?', 'partie', 'pt',
    'episodes?', 'saisons?', 'seasons?', 'integrales?',
]
KEYWORD_RE = r'(?:%s)' % '|'.join(KEYWORDS)

ROMAN_VALUES = (('x', 10), ('ix', 9), ('v', 5), ('iv', 4), ('i', 1))
ROMAN_RE = r'(?=[ivxlc])(?:x{0,3})(?:ix|iv|v?i{0,3})'

SEPARATORS = r'[\s,;:–—\-]'


def roman_to_int(text):
    """Convert a roman numeral (i..xxxix) to an int, or None."""
    text = (text or '').strip().lower()
    if not text or not re.fullmatch(ROMAN_RE, text):
        return None
    total, index = 0, 0
    while index < len(text):
        for numeral, value in ROMAN_VALUES:
            if text.startswith(numeral, index):
                total += value
                index += len(numeral)
                break
        else:
            return None
    return total or None


def parse_number(text):
    """Turn "3", "02", "1.5" or "IV" into a float, or None."""
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return float(text.replace(',', '.'))
    except ValueError:
        pass
    value = roman_to_int(text)
    return float(value) if value else None


def format_index(value):
    """Render a series index the way calibre does: 3, not 3.0."""
    if value is None:
        return ''
    return str(int(value)) if abs(value - int(value)) < 1e-6 else ('%g' % value)


# --------------------------------------------------------------------------
# Patterns, tried in order.  Each one names: series, num and optionally sub.
# --------------------------------------------------------------------------

NUMBER = r'(?P<num>\d+(?:[.,]\d+)?|%s)' % ROMAN_RE

PATTERNS = [
    # The Poppy War (The Poppy War #1) / Vagabond (Vagabond, Book 2)
    ('parenthesis',
     re.compile(r'^(?P<sub>.+?)\s*[\(\[]\s*(?P<series>.+?)'
                r'%s*(?:#|n[o°]\.?\s*|%s\.?\s*)%s\s*[\)\]]\s*$'
                % (SEPARATORS, KEYWORD_RE, NUMBER),
                re.IGNORECASE | re.UNICODE)),

    # La Guerre du pavot, Livre 2 : La Republique du Dragon
    # 86-EIGHTY-SIX: Alter, Vol. 1: The Reaper's Occasional Adolescence
    ('keyword_subtitle',
     re.compile(r'^(?P<series>.+?)%s+%s\.?%s*%s'
                r'%s*[:–—\-]%s*(?P<sub>\S.*)$'
                % (SEPARATORS, KEYWORD_RE, SEPARATORS, NUMBER,
                   SEPARATORS, SEPARATORS),
                re.IGNORECASE | re.UNICODE)),

    # La guerre du pavot T1 / Vagabond part 02 / Dune, Book 3
    ('keyword_trailing',
     re.compile(r'^(?P<series>.+?)%s*\b%s\.?%s*%s\s*$'
                % (SEPARATORS, KEYWORD_RE, SEPARATORS, NUMBER),
                re.IGNORECASE | re.UNICODE)),

    # Mistborn #2 / Mistborn n"o 2
    ('hash_trailing',
     re.compile(r'^(?P<series>.+?)%s*(?:#|n[o°]\.?\s*)%s\s*$'
                % (SEPARATORS, NUMBER),
                re.IGNORECASE | re.UNICODE)),
]

# Only used when the caller opts in: a bare trailing number is far too often
# part of the real title (Fahrenheit 451, Catch 22, 1984).
BARE_TRAILING = ('bare_number',
                 re.compile(r'^(?P<series>.+?)\s+%s\s*$' % NUMBER,
                            re.IGNORECASE | re.UNICODE))

# Titles whose trailing number is part of the work itself.
BARE_BLOCKLIST = re.compile(
    r'^(?:fahrenheit|catch|apollo|route|district|area|blade\s+runner)\b',
    re.IGNORECASE)


def _clean(text):
    if not text:
        return ''
    text = re.sub(r'\s+', ' ', text).strip()
    return text.strip(' ,;:-–—([')


class Parsed(object):
    """What a title yielded: a series, a number, and the remaining title."""

    __slots__ = ('title', 'series', 'index', 'rule')

    def __init__(self, title, series, index, rule):
        self.title = title
        self.series = series
        self.index = index
        self.rule = rule

    def __repr__(self):
        return 'Parsed(title=%r, series=%r, index=%s, rule=%s)' % (
            self.title, self.series, format_index(self.index), self.rule)

    def __eq__(self, other):
        return (isinstance(other, Parsed) and self.title == other.title and
                self.series == other.series and self.index == other.index)


def parse_title(title, allow_bare_number=False, rewrite_title=True):
    """Extract (title, series, index) from *title*, or None if nothing matched.

    *rewrite_title* controls whether the volume marker is stripped from the
    title; when False only the series and the index are reported.
    """
    original = (title or '').strip()
    if not original:
        return None

    patterns = list(PATTERNS)
    if allow_bare_number and not BARE_BLOCKLIST.match(original):
        patterns.append(BARE_TRAILING)

    for rule, pattern in patterns:
        match = pattern.match(original)
        if not match:
            continue
        index = parse_number(match.group('num'))
        series = _clean(match.group('series'))
        if index is None or not series:
            continue
        groups = match.groupdict()
        subtitle = _clean(groups.get('sub') or '')
        if rule == 'parenthesis':
            # the part before the bracket is the real title
            new_title = subtitle or series
        else:
            new_title = subtitle or series
        if not new_title:
            continue
        return Parsed(new_title if rewrite_title else original,
                      series, index, rule)
    return None


# --------------------------------------------------------------------------
# Author helpers
# --------------------------------------------------------------------------

PARTICLES = {'de', 'du', 'des', 'van', 'von', 'der', 'den', 'da', 'di', 'la',
             'le', 'el', 'al', 'bin', 'ibn', "d'", "l'"}


def swap_author(name):
    """"Hugo, Victor" -> "Victor Hugo"; leaves anything else alone."""
    name = (name or '').strip()
    if name.count(',') != 1:
        return name
    last, _sep, first = name.partition(',')
    last, first = last.strip(), first.strip()
    if not last or not first:
        return name
    # "Hugo, Victor Jr." stays sane; a comma followed by a suffix does not
    if first.lower().rstrip('.') in ('jr', 'sr', 'ii', 'iii', 'phd', 'md'):
        return name
    return '%s %s' % (first, last)


def normalise_spaces(text):
    """Collapse runs of whitespace and fix spacing around punctuation."""
    text = re.sub(r'\s+', ' ', (text or '')).strip()
    text = re.sub(r'\s+([,;:!?])', r'\1', text)
    text = re.sub(r'([,;])(?=\S)', r'\1 ', text)
    return text.strip()


# --------------------------------------------------------------------------
# What the plugin proposes for one book
# --------------------------------------------------------------------------

class Proposal(object):
    """One book's before/after, carried from the parser to the GUI."""

    def __init__(self, book_id, old_title='', old_series='', old_index=None,
                 old_authors=''):
        self.book_id = book_id
        self.old_title = old_title or ''
        self.old_series = old_series or ''
        self.old_index = old_index
        self.old_authors = old_authors or ''
        self.new_title = self.old_title
        self.new_series = self.old_series
        self.new_index = old_index
        self.new_authors = self.old_authors
        self.rule = ''
        self.selected = True

    @property
    def changed(self):
        return (self.new_title != self.old_title or
                self.new_series != self.old_series or
                self.new_authors != self.old_authors or
                (self.new_index != self.old_index and
                 (self.new_series or self.old_series)))

    def summary(self):
        bits = []
        if self.new_title != self.old_title:
            bits.append('title')
        if self.new_series != self.old_series:
            bits.append('series')
        if self.new_authors != self.old_authors:
            bits.append('authors')
        return ', '.join(bits) or 'index'

    def __repr__(self):
        return 'Proposal(%r -> %r, %r #%s)' % (
            self.old_title, self.new_title, self.new_series,
            format_index(self.new_index))
