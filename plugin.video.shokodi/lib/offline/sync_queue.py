# -*- coding: utf-8 -*-
"""
Watched-state changes made while the server is unreachable. Only the latest state of each
episode/series/group is kept, and the queue is sent to the server the next time the main menu loads online.
"""
import io
import json
import os
import time

from lib import error_handler as eh
from lib.error_handler import ErrorPriority
from lib.offline import state
from lib.proxy.kodi import kodi_proxy
from lib.proxy.python import proxy as pyproxy
from lib.utils.globalvars import plugin_addon, server

localize = plugin_addon.getLocalizedString


def _path():
    return os.path.join(state.data_dir(), 'watched_queue.json')


def _load():
    path = _path()
    if not os.path.isfile(path):
        return {}
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    except:
        eh.exception(ErrorPriority.NORMAL)
        return {}


def _save(queue):
    path = _path()
    if len(queue) == 0:
        if os.path.isfile(path):
            os.remove(path)
        return
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        f.write(pyproxy.decode(json.dumps(queue)))
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


def enqueue(prefix, obj_id, watched):
    """
    :param prefix: the api path of the object type, such as 'ep', 'serie', or 'group'
    :param obj_id: the object's id
    :param watched: the state to set. Overwrites anything queued for the same object
    """
    queue = _load()
    queue['%s:%s' % (prefix, obj_id)] = {'prefix': prefix, 'id': obj_id, 'watched': bool(watched), 'time': time.time()}
    _save(queue)
    eh.log('Queued watched state for later', prefix, obj_id, watched)


def pending_count():
    return len(_load())


def sync():
    """
    Sends the queue to the server, with a progress dialog. Stops at the first connection error, keeping what's left.
    :return: True if the queue is empty afterwards
    """
    queue = _load()
    if len(queue) == 0:
        return True

    entries = sorted(queue.items(), key=lambda kv: kv[1].get('time', 0))
    progress = kodi_proxy.Dialog.Progress(localize(30360), '')
    done = 0
    try:
        for key, entry in entries:
            if progress.is_cancelled():
                break
            progress.update(int(done * 100.0 / len(entries)), '%i / %i' % (done + 1, len(entries)))
            url = '%s/api/%s/%s' % (server, entry['prefix'], 'watch' if entry['watched'] else 'unwatch')
            url = pyproxy.set_parameter(url, 'id', entry['id'])
            try:
                pyproxy.get_data(url, None, plugin_addon.getSetting('timeout'), plugin_addon.getSetting('apikey'))
            except pyproxy.HTTPError as ex:
                # the server heard us and said no (the object is gone, etc). Retrying won't change that
                eh.log('Dropping queued watched state', key, ex.code)
            except (IOError, OSError):
                eh.exception(ErrorPriority.NORMAL)
                break
            # only remove it if nobody queued a newer state for it while we were sending
            current = _load()
            if current.get(key, {}).get('time') == entry.get('time'):
                del current[key]
                _save(current)
            done += 1
    finally:
        progress.close()
    return pending_count() == 0


_offline_view = None


def queued_state(prefix, obj_id):
    """
    :return: the queued entry for an object, or None. Only meaningful offline, and read once per process
    """
    global _offline_view
    if _offline_view is None:
        _offline_view = _load()
    return _offline_view.get('%s:%s' % (prefix, obj_id))


def apply_to_sizes(prefix, obj_id, sizes):
    """Makes a series' or group's counts reflect a watched state that is waiting to be sent"""
    if not state.is_offline() or sizes is None:
        return
    entry = queued_state(prefix, obj_id)
    if entry is None:
        return
    if entry['watched']:
        sizes.watched_episodes = sizes.total_episodes
        sizes.watched_specials = sizes.total_specials
    else:
        sizes.watched_episodes = 0
        sizes.watched_specials = 0


def apply_to_episode(ep):
    """Makes an episode reflect its own queued state, or its series' if that was queued more recently"""
    if not state.is_offline():
        return
    entries = [queued_state('ep', ep.id)]
    if ep.series_id:
        entries.append(queued_state('serie', ep.series_id))
    entries = [e for e in entries if e is not None]
    if len(entries) == 0:
        return
    latest = max(entries, key=lambda e: e.get('time', 0))
    ep.watched = latest['watched']
    if not ep.watched:
        for f in ep.items:
            f.resume_time = 0
