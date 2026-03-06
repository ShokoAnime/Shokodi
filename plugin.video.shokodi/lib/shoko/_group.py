# -*- coding: utf-8 -*-
"""
Group: represents an anime group (collection of related series) in Shoko.
"""
import random
from concurrent.futures import ThreadPoolExecutor

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.utils import model_utils
from lib.proxy.python import proxy as pyproxy
from plugin_routes import PluginRoutes
from lib.shoko._base import Directory
from lib.shoko._helpers import (
    _get_json_list, _get_airdate, _get_rating, _get_user_rating,
    _get_votes, _LISTING_MAX_WORKERS,
)
from lib.shoko._sizes import get_sizes
from lib.shoko._series import Series


# noinspection Duplicates
class Group(Directory):
    """
    A group object using the v3 API.
    """

    def __init__(self, json_node, filter_id=0, get_children=False):
        self.filter_id = 0
        if filter_id != 0 and filter_id != '0':
            self.filter_id = filter_id
        Directory.__init__(self, json_node, get_children)

        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            eh.spam(self)
            return

        self.date = _get_airdate(json_node)
        self.rating = _get_rating(json_node)
        self.user_rating = _get_user_rating(json_node)
        self.votes = _get_votes(json_node)
        self.actors = model_utils.get_cast_info(json_node)
        self.sizes = get_sizes(json_node)
        self.tags = model_utils.get_tags(json_node.get('tags', {}))
        self.overview = model_utils.make_text_nice(pyproxy.decode(json_node.get('description', '')))

        self.process_children(json_node)

        eh.spam(self)

    @classmethod
    def build(cls, group_id, filter_id=0, api=None, get_children=False):
        from lib.shoko._api import get_api
        _api = api or get_api()
        data = _api.get_group(group_id)
        if data is None:
            raise RuntimeError('Group not found: %s' % group_id)
        return cls(data, filter_id=filter_id, get_children=get_children)

    @classmethod
    def make_item(cls, json_node, filter_id=0, api=None):
        """Collapse a single-series group to show the Series directly."""
        from lib.shoko._api import get_api
        _api = api or get_api()
        group = cls(json_node, filter_id=filter_id)
        if group.size == 1:
            series_list = _api.list_series_in_group(group.id, page_size=1)
            if series_list:
                return Series(series_list[0])
        return group

    def process_art(self, json_node):
        Directory.process_art(self, json_node)
        # If the group has no images (common), fetch one from a member series.
        # randomImages=true on the group list call normally covers this, but
        # handle the fallback for direct Group construction too.
        if self.id and not self.poster:
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

    def get_api_url(self):
        return self.base_url() + '/' + str(self.id)

    def url_prefix(self):
        return 'Group'

    def get_plugin_url(self):
        return plugin_router.url_for(PluginRoutes.show_group_menu, self.id, self.filter_id)

    def process_children(self, json_node):
        if not self.get_children:
            return
        url = self.base_url() + '/' + str(self.id) + '/Series'
        url = pyproxy.set_parameter(url, 'pageSize', 0)
        url = pyproxy.set_parameter(url, 'randomImages', 'true')
        json_body = pyproxy.get_json(url)
        items = _get_json_list(json_body)
        with ThreadPoolExecutor(max_workers=_LISTING_MAX_WORKERS) as executor:
            futures = [executor.submit(Series, i) for i in items]
            for future in futures:
                try:
                    self.items.append(future.result())
                except:
                    pass
