#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kobo Cover Pusher - a calibre interface plugin.

Writes the covers from your calibre library straight into the thumbnail cache
of a connected Kobo, without resending the book files, so reading positions,
bookmarks and annotations survive a cover change.

Only this file is loaded when calibre scans the plugins, so it stays free of
Qt imports; the real work is loaded lazily from action.py.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from calibre.customize import InterfaceActionBase


class KoboCoverPusher(InterfaceActionBase):

    name = 'Kobo Cover Pusher'
    description = ('Refresh the cover thumbnails on a connected Kobo without '
                   'resending the books, so reading positions and annotations '
                   'are preserved.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'huosh1'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.kobo_cover_pusher.action:KoboCoverPusherAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.kobo_cover_pusher.config import ConfigWidget
            return ConfigWidget()
        return None

    def save_settings(self, config_widget):
        config_widget.save_settings()
