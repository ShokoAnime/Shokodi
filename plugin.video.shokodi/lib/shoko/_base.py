# -*- coding: utf-8 -*-
"""
Directory: abstract base class for all browseable Shoko objects (Filter, Group, Series, Episode, File).
"""
import os
import random
from abc import abstractmethod

from lib import class_dump
from lib.utils.globalvars import *
from lib.utils import model_utils
from lib.proxy.kodi import kodi_proxy
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.python import proxy as pyproxy
from lib.shoko._helpers import _preferred_image, _image_url


# noinspection Duplicates,PyUnusedFunction
class Directory(object):
    """
    A directory object, the base for Groups, Series, Episodes, etc
    """

    def __init__(self, json_node, get_children=False):
        """
        Create a directory object from a json node, containing only what is needed to form a ListItem.
        :param json_node: the json response from things like api/v3/Series
        :type json_node: Union[list,dict]
        """
        self.is_kodi_folder = True
        self.name = None
        self.items = []
        self.fanart = ''
        self.fanart_list = []
        self.poster = ''
        self.banner = ''
        self.banner_list = []
        self.icon = ''
        self.size = -1
        self.get_children = get_children
        self.sort_index = 0
        self.sizes = None
        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            self.id = json_node
            return

        self.id = json_node.get('id', 0)
        self.name = model_utils.get_title(json_node)
        self.size = int(json_node.get('size') or 0)

        self.process_art(json_node)

    def __str__(self):
        result = '<%s> ' % self.__class__.__name__
        if self.name != '':
            result += self.name
        else:
            result += '[%s]' % self.id

        if self.items is not None and len(self.items) > 0:
            if len(self.items) == 1:
                result += ' - %s item' % len(self.items)
            else:
                result += ' - %s items' % len(self.items)
        else:
            result += ' - 0 items'

        return result

    def __repr__(self):
        return class_dump.dump_to_text(self)

    def apply_image_override(self, image):
        self.fanart = os.path.join(plugin_img_path, 'backgrounds', image)
        self.poster = os.path.join(plugin_img_path, 'icons', image)
        self.banner = os.path.join(plugin_img_path, 'banners', image)

    @abstractmethod
    def get_api_url(self):
        pass

    @abstractmethod
    def get_plugin_url(self):
        pass

    @abstractmethod
    def url_prefix(self):
        pass

    def base_url(self):
        return server + '/api/v3/' + self.url_prefix()

    def process_art(self, json_node):
        thumb = ''
        fanart_list = []
        banner_list = []
        try:
            images = json_node.get('images', {}) if isinstance(json_node, dict) else {}

            poster_img = _preferred_image(images.get('posters', []))
            if poster_img:
                thumb = _image_url(server, poster_img)

            fanart_list = [u for u in [_image_url(server, img) for img in images.get('backdrops') or images.get('fanarts') or []] if u]
            banner_list = [u for u in [_image_url(server, img) for img in images.get('banners') or []] if u]
        except:
            pass
        self.fanart_list = fanart_list
        self.fanart = random.choice(fanart_list) if fanart_list else ''
        self.poster = thumb
        self.banner_list = banner_list
        self.banner = random.choice(banner_list) if banner_list else ''
        self.icon = ''

    def process_children(self, json_node):
        pass

    def set_watched_status(self, watched):
        if pyproxy.is_string(watched):
            watched = watched.lower() != 'false'

        watched_str = 'true' if watched else 'false'
        url = self.base_url() + '/' + str(self.id) + '/Watched/' + watched_str
        if plugin_addon.getSetting('syncwatched') == 'true':
            pyproxy.post_data(url, '')
        else:
            kodi_proxy.executebuiltin('Action(ToggleWatched)')

        if plugin_addon.getSetting('watchedbox') == 'true':
            localize = plugin_addon.getLocalizedString
            msg = localize(30201) + ' ' + (localize(30202) if watched else localize(30203))
            kodi_proxy.Dialog.notification(localize(30200), msg)

    def vote(self, value):
        url = self.base_url() + '/' + str(self.id) + '/Vote'
        body = '{"value":%s}' % str(value)
        pyproxy.post_data(url, body)

    def __iter__(self):
        for i in self.items:
            yield i

    def is_watched(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        no_specials = kodi_proxy.Util.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return WatchedStatus.UNWATCHED
        if local_only and no_specials:
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_episodes >= sizes.local_episodes:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if local_only:
            if (sizes.watched_episodes + sizes.watched_specials) == 0:
                return WatchedStatus.UNWATCHED
            if (sizes.watched_episodes + sizes.watched_specials) >= (sizes.local_episodes + sizes.local_specials):
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if no_specials:
            if sizes.watched_episodes == 0:
                return WatchedStatus.UNWATCHED
            if sizes.watched_episodes >= sizes.total_episodes:
                return WatchedStatus.WATCHED
            return WatchedStatus.PARTIAL

        if (sizes.watched_episodes + sizes.watched_specials) == 0:
            return WatchedStatus.UNWATCHED
        if (sizes.watched_episodes + sizes.watched_specials) >= (sizes.total_episodes + sizes.total_specials):
            return WatchedStatus.WATCHED
        return WatchedStatus.PARTIAL

    def get_watched_episodes(self):
        no_specials = kodi_proxy.Util.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return 0
        if no_specials:
            return sizes.watched_episodes
        return sizes.watched_episodes + sizes.watched_specials

    def get_total_episodes(self):
        local_only = plugin_addon.getSetting('local_total') == 'true'
        no_specials = kodi_proxy.Util.get_kodi_setting('ignore_specials_watched')
        sizes = self.sizes
        if sizes is None:
            return 0
        if local_only and no_specials:
            return sizes.local_episodes
        if local_only:
            return sizes.local_episodes + sizes.local_specials
        if no_specials:
            return sizes.total_episodes
        return sizes.total_episodes + sizes.total_specials
