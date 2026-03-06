# -*- coding: utf-8 -*-
"""
Filter: top-level browseable filter (tag, season, year, etc.) in Shoko.
CustomItem: a manually-constructed directory entry with an arbitrary URL.
"""
import random
from concurrent.futures import ThreadPoolExecutor

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.proxy.python import proxy as pyproxy
from plugin_routes import PluginRoutes
from lib.shoko._base import Directory
from lib.shoko._helpers import _get_json_list, _LISTING_MAX_WORKERS
from lib.shoko._group import Group


class CustomItem(Directory):
    def __init__(self, name, image, plugin_url, sort_index=0, is_folder=True):
        Directory.__init__(self, 0, False)
        self._context_menu = []
        self.name = name
        self.plugin_url = plugin_url
        self.image = image
        self.is_kodi_folder = is_folder
        self.apply_image_override(image)

        self.infolabels = {'Title': self.name, 'Plot': self.name}

        self.size = 0
        self.sort_index = sort_index
        self.directory_filter = False

    def get_api_url(self):
        return None

    def url_prefix(self):
        return None

    def get_plugin_url(self):
        return self.plugin_url

    def get_infolabels(self):
        return self.infolabels

    def set_context_menu_items(self, context_menu):
        self._context_menu = context_menu

    def get_context_menu_items(self):
        return self._context_menu

    def set_watched_status(self, watched):
        pass


# noinspection Duplicates
class Filter(Directory):
    """
    A filter object using the v3 API.
    """

    def __init__(self, json_node, get_children=False):
        Directory.__init__(self, json_node, get_children)
        self.plugin_url = plugin_router.url_for(PluginRoutes.show_filter_menu, self.id)
        self.directory_filter = False

        if isinstance(json_node, dict):
            self.directory_filter = json_node.get('applyAtSeriesLevel', False) is False \
                                    and json_node.get('isDirectory', False)

        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            eh.spam(self)
            return

        self.apply_built_in_overrides()
        self.process_children(json_node)

        eh.spam(self)

    @classmethod
    def build(cls, filter_id, api=None, get_children=False):
        from lib.shoko._api import get_api
        _api = api or get_api()
        if filter_id == 0:
            # Root filter: wrap the list in a pseudo-node
            items = _api.list_top_filters()
            data = {'id': 0, 'name': 'Root', 'size': len(items), '_filters': items}
        else:
            data = _api.get_filter(filter_id)
            if data is None:
                raise RuntimeError('Filter not found: %s' % filter_id)
        return cls(data, get_children=get_children)

    def get_api_url(self):
        if self.id == 0:
            url = self.base_url()
            url = pyproxy.set_parameter(url, 'pageSize', 0)
            url = pyproxy.set_parameter(url, 'includeEmpty', 'true')
            return url
        return self.base_url() + '/' + str(self.id)

    def url_prefix(self):
        return 'Filter'

    def get_plugin_url(self):
        return self.plugin_url

    def process_art(self, json_node):
        Directory.process_art(self, json_node)
        # Filters have no images; derive from a random member series.
        if not self.poster and self.id != 0:
            try:
                url = self.base_url() + '/' + str(self.id) + '/Series'
                url = pyproxy.set_parameter(url, 'pageSize', 10)
                url = pyproxy.set_parameter(url, 'randomImages', 'true')
                series_body = pyproxy.get_json(url)
                series_list = _get_json_list(series_body)
                if series_list:
                    Directory.process_art(self, random.choice(series_list))
            except:
                pass

    def apply_built_in_overrides(self):
        if self.name == 'Continue Watching (SYSTEM)':
            self.name = 'Continue Watching'
        elif self.name == 'Seasons':
            self.sort_index = 3
            self.apply_image_override('seasons.png')
        elif self.name == 'Years':
            self.sort_index = 4
            self.apply_image_override('years.png')
        elif self.name == 'Tags':
            self.sort_index = 5
            self.apply_image_override('tags.png')
        elif self.name == 'Unsort':
            self.name = 'Unsorted Files'
            self.sort_index = 6
            self.apply_image_override('unsort.png')
            self.plugin_url = plugin_router.url_for(PluginRoutes.show_unsorted_menu)

    def process_children(self, json_node):
        if not isinstance(json_node, dict):
            return

        # Root filter uses the pre-fetched list stored in '_filters'
        if self.id == 0:
            items = json_node.get('_filters', [])
            with ThreadPoolExecutor(max_workers=_LISTING_MAX_WORKERS) as executor:
                futures = [executor.submit(Filter, i) for i in items]
                for future in futures:
                    try:
                        self.items.append(future.result())
                    except:
                        pass
            return

        if not self.get_children:
            return

        # Try sub-filters first
        sub_url = self.base_url() + '/' + str(self.id) + '/Filter'
        sub_url = pyproxy.set_parameter(sub_url, 'pageSize', 0)
        try:
            sub_body = pyproxy.get_json(sub_url)
        except pyproxy.HTTPError:
            sub_body = None
        sub_filters = _get_json_list(sub_body)

        if sub_filters:
            self.directory_filter = True
            with ThreadPoolExecutor(max_workers=_LISTING_MAX_WORKERS) as executor:
                futures = [executor.submit(Filter, i) for i in sub_filters]
                for future in futures:
                    try:
                        self.items.append(future.result())
                    except:
                        pass
        else:
            # Fetch groups within this filter
            groups_url = self.base_url() + '/' + str(self.id) + '/Group'
            groups_url = pyproxy.set_parameter(groups_url, 'pageSize', 0)
            groups_url = pyproxy.set_parameter(groups_url, 'randomImages', 'true')
            groups_body = pyproxy.get_json(groups_url)
            groups = _get_json_list(groups_body)
            _filter_id = self.id
            with ThreadPoolExecutor(max_workers=_LISTING_MAX_WORKERS) as executor:
                futures = [executor.submit(Group.make_item, g, _filter_id) for g in groups]
                for future in futures:
                    try:
                        self.items.append(future.result())
                    except:
                        pass

    def get_context_menu_items(self):
        pass

    def set_watched_status(self, watched):
        pass
