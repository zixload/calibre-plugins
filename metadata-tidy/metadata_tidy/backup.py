#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Undo store: remembers the values replaced by the last tidy, per library.

One file, rewritten at every run, holding only the previous operation. That
is enough for "I did not want that" and keeps the store from growing without
bound.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import time

from calibre.constants import config_dir

STORE = os.path.join(config_dir, 'plugins', 'metadata_tidy_undo.json')


def _read():
    try:
        with open(STORE, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data):
    try:
        folder = os.path.dirname(STORE)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(STORE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def store(library_id, entries):
    """Save the previous values. *entries* is a list of dicts."""
    data = _read()
    data[str(library_id)] = {'when': time.time(), 'entries': entries}
    return _write(data)


def load(library_id):
    """Return (entries, timestamp) for the last tidy, or ([], None)."""
    record = _read().get(str(library_id))
    if not record:
        return [], None
    return record.get('entries') or [], record.get('when')


def clear(library_id):
    data = _read()
    if str(library_id) in data:
        data.pop(str(library_id))
        _write(data)


def describe_age(when):
    """"3 minutes ago" style label for the undo menu entry."""
    if not when:
        return ''
    seconds = max(0, int(time.time() - when))
    if seconds < 90:
        return '%d seconds ago' % seconds
    if seconds < 5400:
        return '%d minutes ago' % (seconds // 60)
    if seconds < 172800:
        return '%d hours ago' % (seconds // 3600)
    return '%d days ago' % (seconds // 86400)
