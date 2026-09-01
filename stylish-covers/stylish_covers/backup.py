#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cover backups, so a generated cover is never a one way trip.

The previous cover is written next to the calibre configuration, keyed by
library id and book id, which means "Restore previous cover" keeps working
after calibre has been restarted - not only during the session.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import time

from calibre.constants import config_dir

BACKUP_DIRNAME = 'stylish_covers_backups'
# the plugin was called Stylish Cover Generator until 2.0.0; covers backed up
# back then must stay restorable
LEGACY_DIRNAME = 'stylish_cover_generator_backups'
MAX_BACKUPS = 800


def backup_dir():
    path = os.path.join(config_dir, 'plugins', BACKUP_DIRNAME)
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            pass
    return path


def _safe(part):
    return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(part))[:64]


# "prev" is the cover replaced by the last generation, "orig" is the very
# first cover this plugin ever replaced for that book and is never overwritten.
# 'art' is the illustration a cover was composed from, when the user
# supplied one: the only source that is guaranteed to carry no title
KINDS = {'prev': '.bak', 'orig': '.orig', 'art': '.art'}


def backup_path(library_id, book_id, kind='prev'):
    return os.path.join(backup_dir(), '%s__%s%s'
                        % (_safe(library_id), _safe(book_id),
                           KINDS.get(kind, '.bak')))


def store(library_id, book_id, data, kind='prev'):
    """Save the current cover bytes. A None or empty cover stores a tombstone."""
    path = backup_path(library_id, book_id, kind)
    try:
        with open(path, 'wb') as f:
            f.write(data or b'')
        prune()
        return True
    except OSError:
        return False


def legacy_path(library_id, book_id, kind='prev'):
    return os.path.join(config_dir, 'plugins', LEGACY_DIRNAME,
                        '%s__%s%s' % (_safe(library_id), _safe(book_id),
                                      KINDS.get(kind, '.bak')))


def has_backup(library_id, book_id, kind='prev'):
    return (os.path.isfile(backup_path(library_id, book_id, kind)) or
            os.path.isfile(legacy_path(library_id, book_id, kind)))


def load(library_id, book_id, kind='prev'):
    """Return the saved cover bytes, b'' if the book had no cover, else None."""
    path = backup_path(library_id, book_id, kind)
    if not os.path.isfile(path):
        path = legacy_path(library_id, book_id, kind)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError:
        return None


def discard(library_id, book_id, kind='prev'):
    for path in (backup_path(library_id, book_id, kind),
                 legacy_path(library_id, book_id, kind)):
        try:
            os.remove(path)
        except OSError:
            pass


def prune(max_files=MAX_BACKUPS):
    """Keep the backup folder bounded, dropping the oldest entries first."""
    try:
        entries = [os.path.join(backup_dir(), n) for n in os.listdir(backup_dir())
                   if n.endswith('.bak')]  # originals and artwork are kept
    except OSError:
        return
    if len(entries) <= max_files:
        return
    entries.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
    for path in entries[:len(entries) - max_files]:
        try:
            os.remove(path)
        except OSError:
            pass


def count():
    try:
        return len([n for n in os.listdir(backup_dir()) if n.endswith('.bak')])
    except OSError:
        return 0


def age_of(library_id, book_id, kind='prev'):
    """Seconds since the backup was taken, or None."""
    path = backup_path(library_id, book_id, kind)
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return None
