# -*- coding: utf-8 -*-
"""
Series and SeriesTypeList: anime series and per-episode-type list views.
Also provides get_series_for_episode().
"""
import json
import random
from concurrent.futures import ThreadPoolExecutor

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.utils import model_utils
from lib.proxy.kodi import kodi_proxy
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.python import proxy as pyproxy
from plugin_routes import PluginRoutes
from lib.shoko._base import Directory
from lib.shoko._helpers import (
    _normalize_keys, _get_json_list, _get_airdate, _get_rating,
    _get_user_rating, _get_votes, _LISTING_MAX_WORKERS,
)
from lib.shoko._sizes import Sizes, get_sizes
from lib.shoko._episode import Episode


# noinspection Duplicates
class Series(Directory):
    """
    A series object using the v3 API.
    """

    def __init__(self, json_node, get_children=False):
        Directory.__init__(self, json_node, get_children)
        self.url = None
        self.item_type = 'tvshow'

        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            eh.spam(self)
            return

        self.alternate_name = model_utils.get_title(json_node, 'en', 'official')
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('description', '')))

        self.anidb_id = self._get_anidb_id(json_node)
        self.season = pyproxy.safe_int(json_node.get('season', '1'))
        self.date = _get_airdate(json_node)
        self.rating = _get_rating(json_node)
        self.user_rating = _get_user_rating(json_node)
        self.votes = _get_votes(json_node)
        fix_seiyuu_pic = plugin_addon.getSetting('fix_seiyuu_pic') == 'true'
        self.actors = model_utils.get_cast_info(json_node, fix_seiyuu_pic)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        series_type = json_node.get('type', '')
        self.is_movie = series_type == 'Movie'
        if self.is_movie:
            self.item_type = 'movie'
        self.file_size = json_node.get('fileSize', 0)
        self.year = self._get_year(json_node)
        self.mpaa = self.get_mpaa_rating()
        self.studio = ''
        self.outline = " ".join(self.overview.split(".", 3)[:2])
        self.hash = None
        self.episode_types = []

        self.process_children(json_node)

        eh.spam(self)

    @classmethod
    def build(cls, series_id, api=None, get_children=False):
        from lib.shoko._api import get_api
        _api = api or get_api()
        data = _api.get_series(series_id)
        if data is None:
            raise RuntimeError('Series not found: %s' % series_id)
        return cls(data, get_children=get_children)

    @staticmethod
    def _get_anidb_id(json_node):
        # v3: after normalization, IDs.AniDB → ids.aniDB (a numeric id)
        ids = json_node.get('ids', {})
        if isinstance(ids, dict):
            anidb_id = ids.get('aniDB', 0)
            if anidb_id:
                return pyproxy.safe_int(anidb_id)
        # Fallbacks for other response shapes
        links = json_node.get('links', {})
        if links:
            anidb = links.get('aniDB', {})
            if anidb:
                return pyproxy.safe_int(anidb.get('id', 0))
        anidb_node = json_node.get('aniDB', {})
        if anidb_node:
            return pyproxy.safe_int(anidb_node.get('id', 0))
        return pyproxy.safe_int(json_node.get('aid', 0))

    @staticmethod
    def _get_year(json_node):
        air_date = json_node.get('airDate', '')
        if air_date and len(air_date) >= 4:
            try:
                return int(air_date[:4])
            except ValueError:
                pass
        return json_node.get('year', 0)

    def get_api_url(self):
        return self.base_url() + '/' + str(self.id)

    def url_prefix(self):
        return 'Series'

    def get_plugin_url(self):
        try:
            return plugin_router.url_for(PluginRoutes.show_series_menu, self.id)
        except:
            return str(self.id)

    def process_children(self, json_node):
        if not self.get_children:
            return
        url = self.base_url() + '/' + str(self.id) + '/Episode'
        url = pyproxy.set_parameter(url, 'pageSize', 0)
        # Embed file data so each Episode avoids a separate /Episode/{id}/File call.
        url = pyproxy.set_parameter(url, 'includeFiles', 'true')
        url = pyproxy.set_parameter(url, 'includeMediaInfo', 'true')
        url = pyproxy.set_parameter(url, 'includeAbsolutePaths', 'true')
        json_body = pyproxy.get_json(url)
        items = _get_json_list(json_body)
        episode_types = []
        with ThreadPoolExecutor(max_workers=_LISTING_MAX_WORKERS) as executor:
            futures = [executor.submit(Episode, i, self) for i in items]
            for future in futures:
                try:
                    episode = future.result()
                    self.items.append(episode)
                    if episode.episode_type not in episode_types:
                        episode_types.append(episode.episode_type)
                except:
                    pass
        for ep_type in episode_types:
            self.episode_types.append(SeriesTypeList(self, ep_type))

    def vote(self, value):
        Directory.vote(self, value)
        kodi_proxy.Dialog.notification(plugin_addon.getLocalizedString(30321),
                                       plugin_addon.getLocalizedString(30322) + " " + str(value))

    def get_mpaa_rating(self):
        if 'Kodomo' in self.tags:
            return 'TV-Y'
        if 'Mina' in self.tags:
            return 'TV-G'
        if 'Shoujo' in self.tags:
            return 'TV-14'
        if 'Shounen' in self.tags:
            return 'TV-14'
        if 'Josei' in self.tags:
            return 'TV-14'
        if 'Seinen' in self.tags:
            return 'TV-MA'
        if 'Mature' in self.tags:
            return 'TV-MA'
        if '18 Restricted' in self.tags:
            return 'TV-R'
        return ''

    def suggest_rating_based_on_episode_rating(self):
        rating_sum = 0.0
        items_count = 0
        for ep in self.items:
            if ep.episode_type == 'Episode':
                rating_sum += ep.user_rating
                items_count += 1
        if items_count > 0:
            return rating_sum / items_count
        return 0

    def all_episodes_voted(self):
        for ep in self.items:
            if ep.user_rating == 0 and ep.episode_type == 'Episode':
                return False
        return True


# noinspection Duplicates
class SeriesTypeList(object):
    """
    Filtered episode-type view of a Series (composition, not inheritance).
    Shows only episodes matching a given episode_type (e.g. 'Episode', 'Special').
    """

    def __init__(self, series, episode_type, items=None):
        self.series = series
        self.episode_type = episode_type
        self.items = items if items is not None else []
        # Delegate commonly-accessed fields
        self.id = series.id
        self.name = series.name
        self.sizes = series.sizes
        self.is_kodi_folder = True
        self.sort_index = 0
        # Art delegates to the parent series
        self.fanart = series.fanart
        self.fanart_list = series.fanart_list
        self.poster = series.poster
        self.banner = series.banner
        self.banner_list = series.banner_list
        self.icon = series.icon

    @classmethod
    def build(cls, series_id, episode_type, api=None, get_children=False):
        from lib.shoko._api import get_api
        _api = api or get_api()
        series = Series.build(series_id, api=_api)
        items = []
        if get_children:
            raw_eps = _api.list_episodes(series_id)
            items = [ep for ep in [Episode(e, series) for e in raw_eps]
                     if ep.episode_type == episode_type]
        return cls(series, episode_type, items)

    def __iter__(self):
        return iter(self.items)

    def get_plugin_url(self):
        return plugin_router.url_for(PluginRoutes.show_series_episode_types_menu, self.id, self.episode_type)

    def set_watched_status(self, watched):
        self.series.set_watched_status(watched)

    def is_watched(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        sizes = self.sizes
        if sizes is None:
            return WatchedStatus.UNWATCHED

        if local_only and self.episode_type == 'Episode':
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_episodes >= sizes.local_episodes:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if local_only and self.episode_type == 'Special':
            if sizes.watched_specials == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_specials >= sizes.local_specials:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if self.episode_type == 'Episode':
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_episodes >= sizes.total_episodes:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if self.episode_type == 'Special':
            if sizes.watched_specials == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_specials >= sizes.total_specials:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        return WatchedStatus.UNWATCHED

    def get_watched_episodes(self):
        sizes = self.sizes
        if sizes is None:
            return 0
        if self.episode_type == 'Episode':
            return sizes.watched_episodes
        if self.episode_type == 'Special':
            return sizes.watched_specials
        return 0

    def get_total_episodes(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        sizes = self.sizes
        if sizes is None:
            return 0
        if self.episode_type == 'Episode':
            return sizes.local_episodes if local_only else sizes.total_episodes
        if self.episode_type == 'Special':
            return sizes.local_specials if local_only else sizes.total_specials
        return 0


def get_series_for_episode(ep_id):
    url = server + '/api/v3/Episode/' + str(ep_id) + '/Series'
    json_body = pyproxy.get_json(url)
    json_node = _normalize_keys(json.loads(json_body))
    # The endpoint may return a list or a single series
    if isinstance(json_node, list) and len(json_node) > 0:
        json_node = json_node[0]
    elif isinstance(json_node, dict) and 'list' in json_node:
        items = json_node.get('list', [])
        json_node = items[0] if items else {}
    return Series(json_node)
