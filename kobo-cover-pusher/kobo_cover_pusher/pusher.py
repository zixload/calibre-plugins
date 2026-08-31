#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Talking to the connected Kobo.

Nothing here reimplements the Kobo cover format: the thumbnails, their sizes
per model and the ImageId lookup are all done by calibre's own KOBOTOUCH
driver.  This module only finds the device, resolves the file paths, and calls
the driver for one book at a time.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import tempfile


class DeviceError(Exception):
    pass


def connected_kobo(gui):
    """The connected KOBOTOUCH driver, or raise DeviceError."""
    manager = getattr(gui, 'device_manager', None)
    device = getattr(manager, 'connected_device', None) if manager else None
    if device is None:
        raise DeviceError(
            'No device is connected. Plug the Kobo in, wait for calibre to '
            'show it in the toolbar, then try again.')
    if not is_kobo(device):
        raise DeviceError(
            'The connected device is not driven by the Kobo driver '
            '(calibre reports %s). This plugin only knows how to write Kobo '
            'cover thumbnails.' % device.__class__.__name__)
    return device


def is_kobo(device):
    """True for KOBOTOUCH and its subclasses, KoboTouchExtended included."""
    try:
        from calibre.devices.kobo.driver import KOBOTOUCH
    except ImportError:
        return False
    return isinstance(device, KOBOTOUCH)


def device_books(gui):
    """Every book calibre currently lists on the device's main memory."""
    for view_name in ('memory_view', 'card_a_view', 'card_b_view'):
        view = getattr(gui, view_name, None)
        model = view.model() if view is not None else None
        books = getattr(model, 'db', None) if model is not None else None
        if books:
            return list(books)
    return []


def book_file_path(device, book):
    """Absolute path of a device book's file, or None when it cannot be built."""
    path = getattr(book, 'path', None)
    if path and os.path.isabs(path) and os.path.exists(path):
        return path
    lpath = getattr(book, 'lpath', None)
    if not lpath:
        return None
    for prefix in (getattr(device, '_main_prefix', None),
                   getattr(device, '_card_a_prefix', None),
                   getattr(device, '_card_b_prefix', None)):
        if not prefix:
            continue
        candidate = os.path.join(prefix, lpath.replace('/', os.sep))
        if os.path.exists(candidate):
            return candidate
    return None


def driver_options(device, settings):
    """Cover options: the driver's own, unless the user overrode them."""
    if settings.get('use_driver_settings', True):
        return {
            'uploadgrayscale': bool(getattr(device, 'upload_grayscale', False)),
            'dithered_covers': bool(getattr(device, 'dithered_covers', False)),
            'keep_cover_aspect': bool(getattr(device, 'keep_cover_aspect', False)),
            'letterbox_fs_covers': bool(getattr(device, 'letterbox_fs_covers',
                                                False)),
            'png_covers': bool(getattr(device, 'png_covers', False)),
            'letterbox_color': getattr(device, 'letterbox_fs_covers_color',
                                       '#000000') or '#000000',
        }
    return {
        'uploadgrayscale': bool(settings.get('grayscale', False)),
        'dithered_covers': bool(settings.get('dithered', False)),
        'keep_cover_aspect': bool(settings.get('keep_aspect', True)),
        'letterbox_fs_covers': bool(settings.get('letterbox', False)),
        'png_covers': bool(settings.get('png', False)),
        'letterbox_color': settings.get('letterbox_color') or '#000000',
    }


def push_cover(device, device_book, cover_data, metadata, options):
    """Write one book's cover thumbnails on the device.

    *cover_data* is the raw image from the calibre library. Returns the path
    of the book on the device, and raises on failure.
    """
    filepath = book_file_path(device, device_book)
    if not filepath:
        raise DeviceError('the file for this book cannot be found on the device')
    if not cover_data:
        raise DeviceError('this book has no cover in the calibre library')
    if not hasattr(device, '_upload_cover'):
        raise DeviceError(
            'this calibre version no longer exposes the Kobo driver method '
            'this plugin builds on (_upload_cover); the plugin needs updating')

    handle, temp_cover = tempfile.mkstemp(prefix='kcp_', suffix='.jpg')
    try:
        with os.fdopen(handle, 'wb') as f:
            f.write(cover_data)
        metadata.cover = temp_cover
        # _upload_cover, not upload_cover: the public one returns early when
        # the driver's "Upload covers" option is off, and pushing covers on
        # demand is the entire point of this plugin.
        device._upload_cover(
            os.path.dirname(filepath),
            os.path.splitext(os.path.basename(filepath))[0],
            metadata, filepath,
            options['uploadgrayscale'],
            dithered_covers=options['dithered_covers'],
            keep_cover_aspect=options['keep_cover_aspect'],
            letterbox_fs_covers=options['letterbox_fs_covers'],
            png_covers=options['png_covers'],
            letterbox_color=options['letterbox_color'])
    finally:
        metadata.cover = None
        try:
            os.remove(temp_cover)
        except OSError:
            pass
    return filepath


def device_summary(device):
    """What the info dialog shows: model, paths and thumbnail sizes."""
    info = {
        'driver': device.__class__.__name__,
        'name': getattr(device, 'gui_name', None) or
                getattr(device, 'name', 'Kobo'),
        'main_prefix': getattr(device, '_main_prefix', None),
        'upload_covers': bool(getattr(device, 'upload_covers', False)),
        'keep_cover_aspect': bool(getattr(device, 'keep_cover_aspect', False)),
        'png_covers': bool(getattr(device, 'png_covers', False)),
        'sizes': [],
    }
    try:
        endings = device.cover_file_endings()
        for ending, spec in sorted(endings.items()):
            size = spec[0] if spec else None
            info['sizes'].append((ending.strip() or '(no suffix)', size))
    except Exception:
        pass
    try:
        version = getattr(device, 'device_version_info', None)
        info['firmware'] = version() if callable(version) else version
    except Exception:
        info['firmware'] = None
    return info
