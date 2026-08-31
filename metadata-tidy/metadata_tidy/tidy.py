#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Turning library metadata into proposals, and writing accepted proposals back.

This module only needs a calibre database object, never the GUI, so the whole
decision logic can be exercised on a throwaway library from a script.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from calibre.ebooks.metadata import authors_to_string, string_to_authors

from .parser import Proposal, normalise_spaces, parse_title, swap_author


def unify_series_case(proposals, existing_names=()):
    """Make every spelling of the same series agree, as calibre will anyway.

    calibre matches series names case insensitively, so "La guerre du pavot"
    and "La Guerre du pavot" end up as one series whatever the preview says.
    Deciding here keeps the preview honest: an existing library spelling wins,
    otherwise the most frequent one, ties broken by the lowest volume number.
    """
    existing = {}
    for name in existing_names or ():
        existing.setdefault(name.lower(), name)

    votes = {}
    for p in proposals:
        if not p.new_series:
            continue
        key = p.new_series.lower()
        entry = votes.setdefault(key, {})
        index = p.new_index if p.new_index is not None else 1e9
        count, best_index = entry.get(p.new_series, (0, 1e9))
        entry[p.new_series] = (count + 1, min(best_index, index))

    winners = {}
    for key, spellings in votes.items():
        if key in existing:
            winners[key] = existing[key]
        else:
            winners[key] = sorted(
                spellings.items(), key=lambda kv: (-kv[1][0], kv[1][1], kv[0])
            )[0][0]

    for p in proposals:
        if p.new_series:
            p.new_series = winners.get(p.new_series.lower(), p.new_series)
    return proposals


def build_proposals(db, book_ids, settings):
    """Read *book_ids* and return the Proposals that would change something."""
    proposals = []
    for book_id in book_ids:
        try:
            mi = db.get_metadata(book_id)
        except Exception:
            continue
        authors = authors_to_string(list(mi.authors or []))
        proposal = Proposal(book_id, mi.title or '', mi.series or '',
                            mi.series_index, authors)

        parsed = parse_title(
            proposal.old_title,
            allow_bare_number=settings.get('allow_bare_number', False),
            rewrite_title=settings.get('rewrite_title', True))
        if parsed is not None:
            proposal.rule = parsed.rule
            proposal.new_title = parsed.title
            keep = settings.get('fill_empty_series_only', True) and \
                proposal.old_series
            if not keep:
                proposal.new_series = parsed.series
                proposal.new_index = parsed.index

        if settings.get('swap_authors'):
            proposal.new_authors = authors_to_string(
                [swap_author(n) for n in (mi.authors or [])])

        if settings.get('normalise_spaces', True):
            proposal.new_title = normalise_spaces(proposal.new_title)
            proposal.new_series = normalise_spaces(proposal.new_series)

        if proposal.changed:
            proposals.append(proposal)

    try:
        existing = db.all_field_names('series')
    except Exception:
        existing = ()
    unify_series_case(proposals, existing)
    return [p for p in proposals if p.changed]


def split_changes(proposals):
    """Group proposals into the per field maps calibre's set_field expects."""
    titles, series, indices, authors, undo = {}, {}, {}, {}, []
    for p in proposals:
        if p.new_title and p.new_title != p.old_title:
            titles[p.book_id] = p.new_title
        if p.new_series != p.old_series:
            series[p.book_id] = p.new_series
        if p.new_index is not None and p.new_index != p.old_index:
            indices[p.book_id] = p.new_index
        if p.new_authors and p.new_authors != p.old_authors:
            authors[p.book_id] = string_to_authors(p.new_authors)
        undo.append({'book_id': p.book_id, 'title': p.old_title,
                     'series': p.old_series, 'series_index': p.old_index,
                     'authors': p.old_authors})
    return titles, series, indices, authors, undo


def write_changes(db, proposals):
    """Apply the proposals; returns the undo entries."""
    titles, series, indices, authors, undo = split_changes(proposals)
    if titles:
        db.set_field('title', titles)
    if series:
        db.set_field('series', series)
    if indices:
        db.set_field('series_index', indices)
    if authors:
        db.set_field('authors', authors)
    return undo


def restore(db, entries):
    """Put back values saved by a previous run; returns the ids restored."""
    known = db.all_book_ids()
    titles, series, indices, authors, restored = {}, {}, {}, {}, []
    for entry in entries:
        book_id = entry.get('book_id')
        if book_id not in known:
            continue
        titles[book_id] = entry.get('title') or ''
        series[book_id] = entry.get('series') or ''
        index = entry.get('series_index')
        indices[book_id] = 1.0 if index is None else index
        authors[book_id] = string_to_authors(entry.get('authors') or 'Unknown')
        restored.append(book_id)
    if restored:
        db.set_field('title', titles)
        db.set_field('series', series)
        db.set_field('series_index', indices)
        db.set_field('authors', authors)
    return restored
