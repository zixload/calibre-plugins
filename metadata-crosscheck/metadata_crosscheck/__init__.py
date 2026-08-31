#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cross-Check - a calibre metadata source.

Queries several free, keyless APIs at once, cross-checks what they say, and
hands the result to calibre's usual "Download metadata" dialog, where you
compare and pick as always.

It exists because the sources calibre ships answer well for published books
and badly for manga, light novels and web novels: asked about "Lord of the
Mysteries", Amazon offers a diet cookbook.  AniList, MangaDex and Kitsu know
those works, and their native titles.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from threading import Thread
from urllib.request import Request, urlopen

from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.sources.base import Option, Source

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) calibre '
              'Cross-Check metadata source')


def make_fetch(timeout):
    """A plain urllib fetcher, identical in calibre and in the tests."""
    def fetch(url, data=None, headers=None):
        merged = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
        merged.update(headers or {})
        request = Request(url, data=data, headers=merged)
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    return fetch


class CrossCheck(Source):

    name = 'Cross-Check'
    description = ('Cross-checks several free APIs at once: AniList, MangaDex '
                   'and Kitsu for manga, manhwa, light novels and web novels, '
                   'Open Library and the BnF for books. No API key needed.')
    author = 'huosh1'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    capabilities = frozenset({'identify', 'cover'})
    touched_fields = frozenset({
        'title', 'authors', 'tags', 'comments', 'publisher', 'pubdate',
        'series', 'languages', 'identifier:anilist', 'identifier:mangadex',
        'identifier:kitsu', 'identifier:mal', 'identifier:openlibrary',
        'identifier:isbn'})
    supports_gzip_transfer_encoding = False
    can_get_multiple_covers = False
    prefer_results_with_isbn = False

    options = (
        Option('use_anilist', 'bool', True, 'AniList',
               'Manga, manhwa, manhua, light novels and web novels, with '
               'native titles. The best source for asian works.'),
        Option('use_mangadex', 'bool', True, 'MangaDex',
               'Manga and manhwa, many alternative titles per language.'),
        Option('use_kitsu', 'bool', True, 'Kitsu',
               'Manga and light novels; useful as a second opinion.'),
        Option('use_jikan', 'bool', False, 'MyAnimeList (Jikan)',
               'Often unavailable: it proxies MyAnimeList, which frequently '
               'answers HTTP 504. Off by default.'),
        Option('use_openlibrary', 'bool', True, 'Open Library',
               'Published books: authors, year, publisher, subjects, ISBN.'),
        Option('use_bnf', 'bool', True, 'BnF',
               'The French national library. Strong on french editions, and '
               'the only source here that knows small french publishers.'),
        Option('max_tags', 'number', 12, 'Maximum number of tags',
               'Tags from every source are merged; this caps the total.'),
        Option('match_threshold', 'number', 60,
               'Title similarity to consider two answers the same work (%)',
               'Lower groups more aggressively, higher keeps answers apart.'),
    )

    # -- helpers -----------------------------------------------------------
    def enabled_providers(self):
        from calibre_plugins.metadata_crosscheck.providers import PROVIDERS
        keys = []
        for key, _label, _function, _kind, default in PROVIDERS:
            if self.prefs.get('use_%s' % key, default):
                keys.append(key)
        return keys

    def get_book_url(self, identifiers):
        for key, template in (
                ('anilist', 'https://anilist.co/manga/%s'),
                ('mangadex', 'https://mangadex.org/title/%s'),
                ('mal', 'https://myanimelist.net/manga/%s'),
                ('openlibrary', 'https://openlibrary.org/works/%s')):
            value = identifiers.get(key)
            if value:
                return (key, value, template % value)
        return None

    # -- identify ----------------------------------------------------------
    def identify(self, log, result_queue, abort, title=None, authors=None,
                 identifiers={}, timeout=30):
        if not title:
            log.error('Cross-Check needs a title to search for')
            return
        from calibre_plugins.metadata_crosscheck import providers
        from calibre_plugins.metadata_crosscheck.candidates import (
            confidence_note, cross_check)

        fetch = make_fetch(max(5, int(timeout) // 2))
        keys = self.enabled_providers()
        log.info('Cross-Check: querying %s' % ', '.join(keys))

        # one thread per API, but results are re-ordered by provider
        # afterwards: thread completion order would make runs differ
        per_provider, threads = {}, []

        def worker(key):
            per_provider[key] = providers.run([key], fetch, title, authors, log)

        for key in keys:
            thread = Thread(target=worker, args=(key,), daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join(timeout)
        if abort.is_set():
            return
        collected = []
        for key in keys:
            collected.extend(per_provider.get(key) or [])

        threshold = max(0.2, min(0.95,
                                 float(self.prefs.get('match_threshold', 60))
                                 / 100.0))
        merged = cross_check(collected, threshold, searched=title)
        log.info('Cross-Check: %d candidate(s) -> %d work(s)'
                 % (len(collected), len(merged)))

        max_tags = int(self.prefs.get('max_tags', 12) or 12)
        for position, record in enumerate(merged):
            if abort.is_set():
                return
            mi = self.to_metadata(record, confidence_note(record), max_tags)
            mi.source_relevance = position
            if record.cover_url:
                for key, value in record.identifiers.items():
                    self.cache_identifier_to_cover_url('%s:%s' % (key, value),
                                                       record.cover_url)
                mi.has_cover = True
            result_queue.put(mi)

    def to_metadata(self, record, note, max_tags):
        mi = Metadata(record.title, record.authors or ['Unknown'])
        for key, value in record.identifiers.items():
            if value:
                mi.set_identifier(key, str(value))
        if record.tags:
            mi.tags = record.tags[:max_tags]
        if record.publisher:
            mi.publisher = record.publisher
        if record.series:
            mi.series = record.series
            if record.series_index is not None:
                mi.series_index = float(record.series_index)
        if record.languages:
            mi.languages = record.languages
        if record.year:
            try:
                from calibre.utils.date import utc_tz
                from datetime import datetime
                mi.pubdate = datetime(int(record.year), 1, 1, tzinfo=utc_tz)
            except Exception:
                pass

        header = []
        if record.native_title:
            header.append('Original title: %s' % record.native_title)
        header.append(note)
        for url in record.urls[:3]:
            header.append(url)
        body = record.comments or ''
        mi.comments = '\n\n'.join([x for x in ['\n'.join(header), body] if x])
        return mi

    # -- cover -------------------------------------------------------------
    def download_cover(self, log, result_queue, abort, title=None, authors=None,
                       identifiers={}, timeout=30, get_best_cover=False):
        url = None
        for key, value in (identifiers or {}).items():
            url = self.cached_identifier_to_cover_url('%s:%s' % (key, value))
            if url:
                break
        if not url:
            log.info('Cross-Check: no cached cover, running identify first')
            from queue import Queue
            results = Queue()
            self.identify(log, results, abort, title=title, authors=authors,
                          identifiers=identifiers, timeout=timeout)
            while not results.empty():
                mi = results.get()
                for key, value in mi.identifiers.items():
                    url = self.cached_identifier_to_cover_url('%s:%s'
                                                              % (key, value))
                    if url:
                        break
                if url:
                    break
        if not url or abort.is_set():
            return
        try:
            data = make_fetch(timeout)(url, headers={'Accept': 'image/*'})
        except Exception as err:
            log.error('Cross-Check: cover download failed: %s' % err)
            return
        if data:
            result_queue.put((self, data))
