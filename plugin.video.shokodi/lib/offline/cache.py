# -*- coding: utf-8 -*-
"""
A disk cache of the server's read-only API responses, keyed by URL.
Every successful response is stored, so that the menus that were visited can be shown again when the server is gone.
"""
import hashlib
import io
import os

from lib.offline import state

# the only parts of the API that describe browsable content
_CACHED_ENDPOINTS = ('filter', 'group', 'serie', 'ep', 'file')
# endpoints that change something, even though they are GETs
_ACTION_ENDPOINTS = ('watch', 'unwatch', 'vote', 'offset', 'rescan', 'rehash')


def is_cacheable(url):
    marker = '/api/'
    if marker not in url:
        return False
    parts = url.split(marker, 1)[1].split('?')[0].strip('/').split('/')
    if parts[0] not in _CACHED_ENDPOINTS:
        return False
    return not any(p in _ACTION_ENDPOINTS for p in parts)


def _path(url):
    name = hashlib.sha1(url.encode('utf-8')).hexdigest() + '.json'
    return os.path.join(state.data_dir('cache'), name)


def put(url, body):
    if body is None or not is_cacheable(url):
        return
    path = _path(url)
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        f.write(body)
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


def get(url):
    if not is_cacheable(url):
        return None
    path = _path(url)
    if not os.path.isfile(path):
        return None
    with io.open(path, 'r', encoding='utf-8') as f:
        return f.read()


def has_any():
    return any(n.endswith('.json') for n in os.listdir(state.data_dir('cache')))


def clear():
    folder = state.data_dir('cache')
    for n in os.listdir(folder):
        os.remove(os.path.join(folder, n))
