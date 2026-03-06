# -*- coding: utf-8 -*-
"""
Episode: represents a single anime episode tracked by Shoko.
"""
import random

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.utils import model_utils
from lib.proxy.kodi import kodi_proxy
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.python import proxy as pyproxy
from lib.shoko._base import Directory
from lib.shoko._helpers import (
    _normalize_episode_type, _get_airdate, _get_rating, _get_user_rating,
    _get_votes, _image_url, _preferred_image, _get_json_list,
)
from lib.shoko._file import File


# noinspection Duplicates
class Episode(Directory):
    """
    An episode object using the v3 API.
    """

    def __init__(self, json_node, series=None):
        self.series_id = 0
        self.series_name = None
        self.series_anidb_id = 0
        self.series_fanart_list = []
        self.series_banner_list = []
        self.actors = []
        self.url = None
        self.item_type = 'episode'
        if series is not None:
            self.series_id = series.id
            self.series_name = series.name
            self.actors = series.actors
            self.series_anidb_id = series.anidb_id
            self.series_fanart_list = getattr(series, 'fanart_list', [series.fanart] if series.fanart else [])
            self.series_banner_list = getattr(series, 'banner_list', [series.banner] if series.banner else [])
            if series.is_movie:
                self.item_type = 'movie'

        Directory.__init__(self, json_node, True)
        # Apply a random fanart and banner from the parent series
        if self.series_fanart_list:
            self.fanart = random.choice(self.series_fanart_list)
        if self.series_banner_list:
            self.banner = random.choice(self.series_banner_list)
        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            eh.spam(self)
            return

        self.episode_number = self._get_episode_number(json_node)
        # Normalize v3 'Normal' type to 'Episode' for internal compatibility
        raw_type = json_node.get('type', json_node.get('episodeType', 'Other'))
        self.episode_type = _normalize_episode_type(raw_type)
        self.date = _get_airdate(json_node)
        self.tvdb_episode = json_node.get('season', '0x0')
        self.update_date = None
        self.hash_content = None

        self.process_children(json_node)

        if self.name is None:
            self.name = 'Episode ' + str(self.episode_number)
        self.alternate_name = model_utils.get_title(json_node, 'x-jat', 'main')

        self.watched = json_node.get('watched', False)
        if isinstance(self.watched, int):
            self.watched = self.watched != 0

        self.year = self._get_episode_year(json_node)

        self.rating = _get_rating(json_node)
        self.user_rating = _get_user_rating(json_node)
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('description', '')))
        self.votes = _get_votes(json_node)
        self.outline = " ".join(self.overview.split(".", 3)[:2])
        self.tags = model_utils.get_tags(json_node.get('tags', {}))

        if self.episode_type != 'Special':
            season = str(json_node.get('season', '1'))
            if 'x' in season:
                season = season.split('x')[0]
        else:
            season = '0'
        self.season = pyproxy.safe_int(season)

        self.resume = False

        eh.spam(self)

    @classmethod
    def build(cls, ep_id, series=None, api=None):
        from lib.shoko._api import get_api
        _api = api or get_api()
        data = _api.get_episode(ep_id)
        if data is None:
            raise RuntimeError('Episode not found: %s' % ep_id)
        return cls(data, series)

    def process_art(self, json_node):
        # Episodes use thumbnails (stills), not posters
        thumb = ''
        try:
            images = json_node.get('images', {})
            thumb_img = _preferred_image(images.get('thumbnails', []))
            if thumb_img:
                thumb = _image_url(server, thumb_img)
        except:
            pass
        self.poster = thumb
        self.icon = ''
        # fanart will be set from series after __init__ completes

    @staticmethod
    def _get_episode_number(json_node):
        # v3 uses 'number' or 'episodeNumber'; fall back to v2-style 'epnumber'
        num = json_node.get('number', json_node.get('episodeNumber', json_node.get('epnumber', '')))
        return pyproxy.safe_int(num)

    @staticmethod
    def _get_episode_year(json_node):
        air_date = json_node.get('airDate', '')
        if air_date and len(air_date) >= 4:
            try:
                return int(air_date[:4])
            except ValueError:
                pass
        return pyproxy.safe_int(json_node.get('year', ''))

    def get_file(self) -> File:
        if len(self.items) > 0 and self.items[0] is not None:
            return self.items[0]
        return None

    def get_file_with_id(self, file_id) -> File:
        for f in self.items:
            if f is None:
                continue
            if f.id == int(file_id):
                return f
        return None

    def get_api_url(self):
        return server + '/api/v3/Episode/' + str(self.id)

    def url_prefix(self):
        return 'Episode'

    def get_plugin_url(self):
        from plugin_routes import PluginRoutes
        return plugin_router.url_for(PluginRoutes.play_video, ep_id=self.id)

    def is_watched(self):
        if self.watched:
            return WatchedStatus.WATCHED
        f = self.get_file()
        if f is not None and f.resume_time > 0:
            return WatchedStatus.PARTIAL
        return WatchedStatus.UNWATCHED

    def process_children(self, json_node):
        # When called from Series.process_children() with includeFiles=true, files are already
        # embedded in the episode JSON — no extra HTTP call needed.
        embedded = json_node.get('files', []) if isinstance(json_node, dict) else []
        if embedded:
            items = embedded
        else:
            url = server + '/api/v3/Episode/' + str(self.id) + '/File'
            json_body = pyproxy.get_json(url)
            if json_body is None:
                return
            items = _get_json_list(json_body)
        for _file in items:
            try:
                f = File(_file)

                if f.isVideo:
                    self.items.append(f)

                if self.update_date is None:
                    self.update_date = f.date_added
                if self.hash_content is None:
                    self.hash_content = str(self.get_plugin_url()).encode('utf-8')
                    if f.size is not None:
                        self.hash_content += str(f.size).encode('utf-8')
                    if f.date_added is not None and len(f.date_added) >= 10:
                        x = str(f.date_added)[8:10] + '.' + str(f.date_added)[5:7] + '.' + str(f.date_added)[0:4]
                        self.hash_content += str(x).encode('utf-8')
            except Exception as ex:
                eh.exception(eh.ErrorPriority.HIGHEST, ex)

    def vote(self, value):
        Directory.vote(self, value)
        kodi_proxy.Dialog.notification(plugin_addon.getLocalizedString(30323),
                                       plugin_addon.getLocalizedString(30322) + " " + value)
