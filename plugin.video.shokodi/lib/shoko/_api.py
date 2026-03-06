# -*- coding: utf-8 -*-
"""
ShokoApi: injectable HTTP client for all Shoko v3 API calls.
Use get_api() to obtain the module-level singleton.
"""
import json

from lib.utils.globalvars import server, plugin_addon
from lib.proxy.python import proxy as pyproxy
from lib.shoko._helpers import _normalize_keys, _get_json_list


class ShokoApi(object):
    def __init__(self, base_url, apikey):
        self._base = base_url.rstrip('/')
        self._apikey = apikey

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def list_top_filters(self, include_empty=True):
        url = self._base + '/api/v3/Filter'
        url = pyproxy.set_parameter(url, 'pageSize', 0)
        url = pyproxy.set_parameter(url, 'includeEmpty', 'true' if include_empty else 'false')
        return _get_json_list(pyproxy.get_json(url))

    def get_filter(self, filter_id):
        url = self._base + '/api/v3/Filter/' + str(filter_id)
        body = pyproxy.get_json(url)
        if body is None:
            return None
        return _normalize_keys(json.loads(body))

    def list_sub_filters(self, filter_id, page_size=0):
        url = self._base + '/api/v3/Filter/' + str(filter_id) + '/Filter'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        return _get_json_list(pyproxy.get_json(url))

    def list_groups(self, filter_id, page_size=0, random_images=True):
        url = self._base + '/api/v3/Filter/' + str(filter_id) + '/Group'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        if random_images:
            url = pyproxy.set_parameter(url, 'randomImages', 'true')
        return _get_json_list(pyproxy.get_json(url))

    def preview_groups(self, body_str, page_size=0, random_images=True):
        url = self._base + '/api/v3/Filter/Preview/Group'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        if random_images:
            url = pyproxy.set_parameter(url, 'randomImages', 'true')
        response = pyproxy.post_data(url, body_str)
        return _get_json_list(response) if response else []

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    def get_group(self, group_id):
        url = self._base + '/api/v3/Group/' + str(group_id)
        body = pyproxy.get_json(url)
        if body is None:
            return None
        return _normalize_keys(json.loads(body))

    def list_series_in_group(self, group_id, page_size=0, random_images=True):
        url = self._base + '/api/v3/Group/' + str(group_id) + '/Series'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        if random_images:
            url = pyproxy.set_parameter(url, 'randomImages', 'true')
        return _get_json_list(pyproxy.get_json(url))

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    def get_series(self, series_id):
        url = self._base + '/api/v3/Series/' + str(series_id)
        body = pyproxy.get_json(url)
        if body is None:
            return None
        return _normalize_keys(json.loads(body))

    def list_series_in_filter(self, filter_id, page_size=0, random_images=True):
        url = self._base + '/api/v3/Filter/' + str(filter_id) + '/Series'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        if random_images:
            url = pyproxy.set_parameter(url, 'randomImages', 'true')
        return _get_json_list(pyproxy.get_json(url))

    def get_series_for_episode(self, ep_id):
        url = self._base + '/api/v3/Episode/' + str(ep_id) + '/Series'
        body = pyproxy.get_json(url)
        if body is None:
            return None
        data = _normalize_keys(json.loads(body))
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        if isinstance(data, dict) and 'list' in data:
            items = data.get('list', [])
            return items[0] if items else None
        return data

    # ------------------------------------------------------------------
    # Episodes
    # ------------------------------------------------------------------

    def get_episode(self, ep_id):
        url = self._base + '/api/v3/Episode/' + str(ep_id)
        body = pyproxy.get_json(url)
        if body is None:
            return None
        return _normalize_keys(json.loads(body))

    def list_episodes(self, series_id, page_size=0, include_files=True,
                      include_media_info=True, include_absolute_paths=True):
        url = self._base + '/api/v3/Series/' + str(series_id) + '/Episode'
        url = pyproxy.set_parameter(url, 'pageSize', page_size)
        if include_files:
            url = pyproxy.set_parameter(url, 'includeFiles', 'true')
        if include_media_info:
            url = pyproxy.set_parameter(url, 'includeMediaInfo', 'true')
        if include_absolute_paths:
            url = pyproxy.set_parameter(url, 'includeAbsolutePaths', 'true')
        return _get_json_list(pyproxy.get_json(url))

    def list_files(self, ep_id):
        url = self._base + '/api/v3/Episode/' + str(ep_id) + '/File'
        return _get_json_list(pyproxy.get_json(url))

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def get_file(self, file_id):
        url = self._base + '/api/v3/File/' + str(file_id)
        body = pyproxy.get_json(url)
        if body is None:
            return None
        return _normalize_keys(json.loads(body))


_default_api = None


def get_api():
    global _default_api
    if _default_api is None:
        _default_api = ShokoApi(server, plugin_addon.getSetting('apikey'))
    return _default_api
