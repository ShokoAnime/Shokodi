# -*- coding: utf-8 -*-
"""
File: represents a single media file tracked by Shoko.
"""
import os

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.utils import model_utils
from lib.proxy.kodi import kodi_proxy
from lib.proxy.python import proxy as pyproxy
from lib.shoko._base import Directory
from lib.shoko._helpers import _parse_timespan_ms, _ms_to_timespan


# noinspection Duplicates
class File(Directory):
    """
    A file object using the v3 API.
    """

    def __init__(self, json_node):
        Directory.__init__(self, json_node)
        self.server_path = ''
        self.file_url = ''

        if pyproxy.is_string(json_node) or pyproxy.isnumeric(json_node):
            eh.spam(self)
            return

        self.name = self._get_filename(json_node)
        self.file_name, self.file_extension = os.path.splitext(self.name)
        self.isVideo = False if self.file_extension in ['.srt', '.sub', '.sbv', '.vtt', '.idx', '.ssa', '.ass',
                                                        '.smi', '.psb', '.usf', '.ssf', '.ttml', '.dfxp', '.xml',
                                                        '.smil'] else True

        # v3 resumePosition is a .NET TimeSpan string ("HH:MM:SS.fffffff"); convert to seconds
        resume_raw = json_node.get('resumePosition', None)
        if resume_raw and isinstance(resume_raw, str):
            self.resume_time = _parse_timespan_ms(resume_raw) // 1000
        else:
            self.resume_time = 0

        # v3 duration is a .NET TimeSpan string ("HH:MM:SS.fffffff"); convert to ms
        duration_raw = json_node.get('duration', 0)
        if isinstance(duration_raw, str):
            self.duration = _parse_timespan_ms(duration_raw)
        else:
            self.duration = int(duration_raw or 0)

        self.size = pyproxy.safe_int(json_node.get('size', 0))

        # Build stream URL using v3 File Stream endpoint (includes apikey for direct media player access)
        apikey = plugin_addon.getSetting('apikey')
        self.file_url = server + '/api/v3/File/' + str(self.id) + '/Stream?apikey=' + apikey

        # Server path from locations array (first accessible location)
        self.server_path = self._get_server_path(json_node)

        self.date_added = pyproxy.decode(json_node.get('created', '')).replace('T', ' ')
        self.group = self._get_release_group(json_node)

        media = json_node.get('mediaInfo', json_node.get('media', {}))
        if media and len(media) > 0:
            try:
                self.video_streams = model_utils.get_video_streams(media)
            except:
                self.video_streams = {}
            try:
                self.audio_streams = model_utils.get_audio_streams(media)
            except:
                self.audio_streams = {}
            try:
                self.sub_streams = model_utils.get_sub_streams(media)
            except:
                self.sub_streams = {}
        else:
            self.video_streams = {}
            self.audio_streams = {}
            self.sub_streams = {}

        self.resume = False

        eh.spam(self)

    @classmethod
    def build(cls, file_id, api=None):
        from lib.shoko._api import get_api
        _api = api or get_api()
        data = _api.get_file(file_id)
        if data is None:
            raise RuntimeError('File not found: %s' % file_id)
        return cls(data)

    @staticmethod
    def _get_filename(json_node):
        # v3: fileName is in aniDB.fileName or locations[0].relativePath basename
        anidb_node = json_node.get('aniDB', {})
        if anidb_node:
            name = anidb_node.get('fileName', '')
            if name:
                return pyproxy.decode(name)
        locations = json_node.get('locations', [])
        if locations:
            path = locations[0].get('relativePath', '')
            if path:
                return os.path.split(pyproxy.decode(path))[-1]
        return pyproxy.decode(json_node.get('filename', 'None'))

    @staticmethod
    def _get_server_path(json_node):
        locations = json_node.get('locations', [])
        for loc in locations:
            if loc.get('accessible', False):
                return pyproxy.decode(loc.get('absolutePath', loc.get('relativePath', '')))
        return json_node.get('server_path', '')

    @staticmethod
    def _get_release_group(json_node):
        anidb_node = json_node.get('aniDB', {})
        if anidb_node:
            rg = anidb_node.get('releaseGroup', {})
            if rg:
                return rg.get('name', rg.get('shortName', ''))
        return json_node.get('group_full', '')

    def get_api_url(self):
        return server + '/api/v3/File/' + str(self.id)

    def url_prefix(self):
        return 'File'

    def get_plugin_url(self):
        from plugin_routes import PluginRoutes
        return plugin_router.url_for(PluginRoutes.play_video_without_marking, file_id=self.id)

    @property
    def url_for_player(self):
        if self.server_path and os.path.isfile(pyproxy.encode(self.server_path)):
            if self.server_path.startswith(u'\\\\'):
                return u'smb:' + self.server_path.replace('\\', '/')
            return self.server_path
        return self.file_url

    def set_watched_status(self, watched):
        if watched:
            return
        self.set_resume_time(0)

    def set_resume_time(self, current_time):
        """
        Sync offset of played file.
        :param current_time: current time in milliseconds
        """
        ticks = int(current_time) * 10000  # ms → ticks (100ns units)
        url = server + '/api/v3/File/' + str(self.id) + '/Scrobble?event=scrobble&resumePosition=' + str(ticks)
        pyproxy.patch_data(url, '', suppress=True)

    def rehash(self):
        url = server + '/api/v3/File/' + str(self.id) + '/Rehash'
        pyproxy.post_data(url, '')
        kodi_proxy.Dialog.notification(plugin_addon.getLocalizedString(30189), plugin_addon.getLocalizedString(30191))

    def rescan(self):
        url = server + '/api/v3/File/' + str(self.id) + '/Rescan'
        pyproxy.post_data(url, '')
        kodi_proxy.Dialog.notification(plugin_addon.getLocalizedString(30190), plugin_addon.getLocalizedString(30191))
