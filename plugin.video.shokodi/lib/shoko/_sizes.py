# -*- coding: utf-8 -*-
"""
Episode count / watched-state size data for groups and series.
"""
from lib.proxy.python import proxy as pyproxy


class Sizes(object):
    def __init__(self):
        self.local_episodes = 0
        self.local_specials = 0
        self.local_total = 0
        self.watched_episodes = 0
        self.watched_specials = 0
        self.watched_total = 0
        self.total_episodes = 0
        self.total_specials = 0
        self.total = 0


def get_sizes(json_node):
    result = Sizes()
    sizes = json_node.get('sizes', {})

    local = sizes.get('local', {})
    result.local_episodes = pyproxy.safe_int(local.get('episodes', 0))
    result.local_specials = pyproxy.safe_int(local.get('specials', 0))
    result.local_total = result.local_episodes + result.local_specials

    watched = sizes.get('watched', {})
    result.watched_episodes = pyproxy.safe_int(watched.get('episodes', 0))
    result.watched_specials = pyproxy.safe_int(watched.get('specials', 0))
    result.watched_total = result.watched_episodes + result.watched_specials

    total = sizes.get('total', {})
    result.total_episodes = pyproxy.safe_int(total.get('episodes', 0))
    result.total_specials = pyproxy.safe_int(total.get('specials', 0))
    result.total = pyproxy.safe_int(json_node.get('size', 0))

    return result
