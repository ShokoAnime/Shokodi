# -*- coding: utf-8 -*-
"""
Files downloaded from the server, for playing without it. An index of what was downloaded is kept beside the files.
"""
import io
import json
import os
import re
import ssl
import time

import xbmcgui

from lib import error_handler as eh
from lib.error_handler import ErrorPriority
from lib.offline import state
from lib.proxy.kodi import kodi_proxy
from lib.proxy.python import proxy as pyproxy
from lib.proxy.python.python_proxy import Request, urlopen
from lib.utils.globalvars import plugin_addon, translatePath

localize = plugin_addon.getLocalizedString

_CHUNK = 256 * 1024


def downloads_dir():
    custom = plugin_addon.getSetting('download_path')
    if custom:
        path = translatePath(custom)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path
    return state.data_dir('downloads')


def _index_path():
    return os.path.join(state.data_dir(), 'downloads.json')


def _load_index():
    path = _index_path()
    if not os.path.isfile(path):
        return {}
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except:
        eh.exception(ErrorPriority.NORMAL)
        return {}


def _save_index(index):
    path = _index_path()
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        f.write(pyproxy.decode(json.dumps(index)))
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


def get_path(file_id):
    """:return: the local path of a downloaded file, or None"""
    entry = _load_index().get(str(file_id))
    if entry is not None and os.path.isfile(entry['path']):
        return entry['path']
    return None


def list_downloads():
    """:return: [(file_id, entry)] of the files that still exist, by title"""
    result = [(k, v) for k, v in _load_index().items() if os.path.isfile(v['path'])]
    result.sort(key=lambda kv: (kv[1].get('series', ''), kv[1].get('title', '')))
    return result


def delete(file_ids):
    index = _load_index()
    for file_id in file_ids:
        entry = index.pop(str(file_id), None)
        if entry is not None and os.path.isfile(entry['path']):
            os.remove(entry['path'])
    _save_index(index)


def _safe_name(name):
    return re.sub(r'[\/:*?"<>|]', '_', name)


def _format_size(size):
    size = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return '%.1f %s' % (size, unit)
        size /= 1024


def _fetch(f, path, progress, label):
    """
    Streams one file to disk.
    :return: True if it finished, False if the user cancelled
    """
    headers = {'apikey': plugin_addon.getSetting('apikey')}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = Request(pyproxy.decode(f.file_url), headers=headers)
    response = urlopen(req, timeout=int(plugin_addon.getSetting('timeout') or 60), context=ctx)
    try:
        total = pyproxy.safe_int(response.info().get('Content-Length')) or f.size
        received = 0
        last_update = 0
        part = path + '.part'
        with io.open(part, 'wb') as out:
            while True:
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                received += len(chunk)
                if progress.is_cancelled():
                    break
                if time.time() - last_update > 0.5:
                    last_update = time.time()
                    percent = int(received * 100.0 / total) if total else 0
                    progress.update(min(percent, 100), '%s\n%s / %s' % (label, _format_size(received),
                                                                         _format_size(total)))
    finally:
        response.close()

    if progress.is_cancelled():
        os.remove(part)
        return False
    if os.path.exists(path):
        os.remove(path)
    os.rename(part, path)
    return True


def download(items):
    """
    Downloads files one by one, in a modal progress dialog. Files that were downloaded already are skipped.
    :param items: [(File, title, series_name)]
    """
    index = _load_index()
    todo = [i for i in items if get_path(i[0].id) is None]
    if len(todo) == 0:
        kodi_proxy.Dialog.ok(localize(30362), localize(30373))
        return

    progress = kodi_proxy.Dialog.Progress(localize(30363), '')
    finished = 0
    cancelled = False
    try:
        for n, (f, title, series) in enumerate(todo):
            label = '[%i/%i] %s' % (n + 1, len(todo), title)
            progress.update(0, label)
            path = os.path.join(downloads_dir(), '%s_%s' % (f.id, _safe_name(f.name)))
            try:
                if not _fetch(f, path, progress, label):
                    cancelled = True
                    break
            except:
                eh.exception(ErrorPriority.HIGHEST, localize(30377) % title)
                break
            index[str(f.id)] = {'path': path, 'title': title, 'series': series, 'size': os.path.getsize(path)}
            # save as we go, so that a cancel or crash keeps what was finished
            _save_index(index)
            finished += 1
    finally:
        progress.close()

    kodi_proxy.Dialog.notification(localize(30364 if not cancelled else 30372), '%i / %i' % (finished, len(todo)))


def manage():
    """Lets the user pick downloaded files to delete"""
    entries = list_downloads()
    if len(entries) == 0:
        kodi_proxy.Dialog.ok(localize(30365), localize(30366))
        return
    labels = ['%s - %s (%s)' % (e.get('series') or '?', e.get('title') or '?', _format_size(e.get('size', 0)))
              for _, e in entries]
    selected = xbmcgui.Dialog().multiselect(localize(30367), labels)
    if not selected:
        return
    if not kodi_proxy.Dialog.yes_no(localize(30365), localize(30368) % len(selected)):
        return
    delete([entries[i][0] for i in selected])
    kodi_proxy.Dialog.notification(localize(30365), localize(30375))
