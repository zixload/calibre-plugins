#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build the installable ZIP of one plugin, or of every plugin in this repo.

    python build.py                          # all plugins -> dist/
    python build.py stylish-covers  # just that one

A plugin lives in its own top level directory and contains exactly one python
package holding __init__.py next to a plugin-import-name-<name>.txt marker.
The ZIP holds the CONTENT of that package at its root, which is what calibre
expects from "Load plugin from file".
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
EXCLUDE_DIRS = {'__pycache__', '.git', '.idea', '.vscode', 'samples', 'tools'}
EXCLUDE_EXT = {'.pyc', '.pyo', '.orig', '.rej'}
MARKER_RE = re.compile(r'^plugin-import-name-(.+)\.txt$')


def find_plugins():
    """Yield (plugin directory name, package path) for every plugin found."""
    for name in sorted(os.listdir(ROOT)):
        plugin_dir = os.path.join(ROOT, name)
        if not os.path.isdir(plugin_dir) or name in EXCLUDE_DIRS or \
                name.startswith('.') or name == 'dist':
            continue
        for entry in sorted(os.listdir(plugin_dir)):
            package = os.path.join(plugin_dir, entry)
            if not os.path.isdir(package):
                continue
            names = os.listdir(package)
            if '__init__.py' in names and \
                    any(MARKER_RE.match(n) for n in names):
                yield name, package
                break


def plugin_version(package):
    with open(os.path.join(package, '__init__.py'), encoding='utf-8') as f:
        match = re.search(r'version\s*=\s*\(([^)]*)\)', f.read())
    if not match:
        return '0.0.0'
    return '.'.join(part.strip() for part in match.group(1).split(','))


def collect(package):
    for dirpath, dirnames, filenames in os.walk(package):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
                continue
            full = os.path.join(dirpath, name)
            yield full, os.path.relpath(full, package).replace(os.sep, '/')


def build(plugin_name, package):
    files = list(collect(package))
    names = {arc for _full, arc in files}
    if '__init__.py' not in names:
        print('ERROR: %s has no __init__.py' % plugin_name)
        return None
    if not any(MARKER_RE.match(n) for n in names):
        print('ERROR: %s has no plugin-import-name-*.txt marker' % plugin_name)
        return None

    if not os.path.isdir(DIST):
        os.makedirs(DIST)
    target = os.path.join(DIST, '%s.zip' % plugin_name)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
        for full, arc in files:
            zf.write(full, arc)
    print('%-28s v%-8s %2d files  %6.1f KiB  -> dist/%s.zip'
          % (plugin_name, plugin_version(package), len(files),
             os.path.getsize(target) / 1024.0, plugin_name))
    return target


def main(argv):
    plugins = dict(find_plugins())
    if not plugins:
        print('No plugin found in %s' % ROOT)
        return 1
    wanted = argv[1:] or sorted(plugins)
    unknown = [name for name in wanted if name not in plugins]
    if unknown:
        print('Unknown plugin(s): %s' % ', '.join(unknown))
        print('Available: %s' % ', '.join(sorted(plugins)))
        return 1
    built = [build(name, plugins[name]) for name in wanted]
    if not all(built):
        return 1
    print('\nInstall with: Preferences -> Plugins -> Load plugin from file')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
