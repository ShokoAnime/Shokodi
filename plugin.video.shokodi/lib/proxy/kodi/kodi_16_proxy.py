import json

import xbmc
import xbmcgui
import xbmcplugin

from lib import error_handler as eh
from lib.utils.globalvars import *
from lib.proxy.kodi.enums import *


class Kodi16Proxy:
    def __init__(self):
        plugin_addon.setSetting('kodi18', 'false')
        self.Dialog = self.Dialog(self)
        self.Sorting = self.Sorting(self)
        self.Util = self.Util(self)

    def user_agent(self):
        """
        This is the useragent that kodi uses when making requests to various services, such as TvDB
        It used to act like Firefox, but in newer versions it has its own
        :return:
        :rtype: basestring
        """
        return 'Mozilla/6.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.5) Gecko/2008092417 Firefox/3.0.3'

    @staticmethod
    def duration_to_kodi(time_s):
        """
        In shoko we use ms, but in various versions of Kodi, there may be a different type
        This takes the duration in seconds and returns the proper converted version
        :param time_s: time in milliseconds
        :type time_s: int
        :return:
        :rtype: Union[str, int]
        """
        return time_s / 1000

    @staticmethod
    def duration_from_kodi(kodi_time):
        """
        In shoko we use ms, but in various versions of Kodi, there may be a different type
        This takes the duration in seconds and returns the proper converted version
        :param kodi_time: Kodi's value
        :type kodi_time: Any
        :return:
        :rtype: Union[str, int]
        """
        return kodi_time * 1000

    def external_player(self, player_obj):
        """
        In Kodi 18+, xbmc.Player has a isExternalPlayer() method. In earlier versions, the user must specify
        :param player_obj: the player object to check
        :return: true or false
        :rtype: bool
        """
        return plugin_addon.getSetting('external_player').lower() == 'true'

    def parse_tags(self, tag_obj_string):
        """
        In Kodi 18+, tags are expected to be list, before it was long string;
        :param tag_obj_string: long string
        :return: Union[string, list]
        """
        temp_genre = ' | '.join(tag_obj_string)
        return temp_genre

    @staticmethod
    def executebuiltin(command):
        xbmc.executebuiltin(command)

    @staticmethod
    def sleep(timemillis):
        xbmc.sleep(timemillis)

    class Dialog:
        parent = None  # type: type[Kodi16Proxy]

        @classmethod
        def __init__(cls, proxy):
            # type: (object, Kodi16Proxy) -> None
            cls.parent = proxy.__class__

        @classmethod
        def notification(cls, header, message):
            cls.parent.executebuiltin('Notification(%s, %s, 2000, %s)' % (header, message, plugin_addon.getAddonInfo('icon')))

        @staticmethod
        def ok(header, message):
            text = message.splitlines()
            # noinspection PyArgumentList
            return xbmcgui.Dialog().ok(header, text[0], text[1] if len(text) > 1 else '',
                                       text[2] if len(text) > 2 else '')

        @staticmethod
        def yes_no(header, message, no_label='', yes_label='', auto_close=0):
            text = message.splitlines()
            # noinspection PyArgumentList
            return xbmcgui.Dialog().yesno(header, text[0], text[1] if len(text) > 1 else '',
                                          text[2] if len(text) > 2 else '')

        @staticmethod
        def context(items):
            return xbmcgui.Dialog().contextmenu(items)

        @staticmethod
        def select(header, items):
            return xbmcgui.Dialog().select(header, items)

        @staticmethod
        def text_input(heading):
            """
            Shows a keyboard, and returns the text entered
            :return: the text that was entered
            """
            keyb = xbmc.Keyboard('', heading)
            keyb.doModal()
            search_text = ''

            if keyb.isConfirmed():
                search_text = keyb.getText()
            return search_text

        @classmethod
        def refresh(cls):
            """
            Refresh and re-request data from server
            refresh watch status as we now mark episode and refresh list so it show real status not kodi_cached
            Allow time for the ui to reload
            """
            cls.parent.executebuiltin('Container.Refresh')
            cls.parent.sleep(1000)

        class Progress:
            def __init__(self, heading, message=''):
                text = message.splitlines()
                self.dialog = xbmcgui.DialogProgress()
                # noinspection PyArgumentList
                self.dialog.create(heading, text[0], text[1] if len(text) > 1 else '', text[2] if len(text) > 2 else '')

            def update(self, percent, message=''):
                text = message.splitlines()
                # noinspection PyArgumentList
                self.dialog.update(percent, text[0], text[1] if len(text) > 1 else '', text[2] if len(text) > 2 else '')

            def close(self):
                self.dialog.close()

            def is_cancelled(self):
                return self.dialog.iscanceled()

    class ListItem:
        def __init__(self, label='', label2='', path='', offscreen=False):
            self.list_item = xbmcgui.ListItem(label, label2, path=path)

        def set_info(self, type, infoLabels):
            self.list_item.setInfo(type=type, infoLabels=infoLabels)

        def set_path(self, path):
            self.list_item.setPath(path)

        def getPath(self):
            return self.list_item.getPath()

        def set_property(self, property, value):
            self.list_item.setProperty(property, value)

        def add_stream_info(self, type, info):
            self.list_item.addStreamInfo(type, info)

        def set_cast(self, cast):
            if len(cast) <= 0:
                return
            self.list_item.setCast(cast)

        def set_rating(self, type, rating, votes=0, default=True):
            self.list_item.setRating(type=type, rating=rating, votes=votes, defaultt=default)

        def set_unique_ids(self, unique_ids):
            self.list_item.setUniqueIDs(unique_ids.get_dict())

        def add_context_menu_items(self, items):
            self.list_item.addContextMenuItems(items=items)

        def set_art(self, dir_obj):
            """
            Set Art from a Directory object
            :param dir_obj:
            :type dir_obj: Directory
            :return:
            """
            if dir_obj.fanart is not None:
                self.set_fanart(dir_obj.fanart)
            if dir_obj.poster is not None:
                self.set_thumb(dir_obj.poster)
            if dir_obj.banner is not None:
                self.set_banner(dir_obj.banner)
            if dir_obj.icon is not None:
                self.set_icon(dir_obj.icon)
            else:
                if dir_obj.poster is not None:
                    self.set_icon(dir_obj.poster)

        def set_icon(self, icon):
            self.list_item.setArt({'icon': icon})

        def set_thumb(self, thumb):
            self.list_item.setArt({'thumb': thumb})
            self.list_item.setArt({'poster': thumb})

        def set_fanart(self, fanart):
            self.list_item.setArt({'fanart': fanart})
            self.list_item.setArt({'clearart': fanart})

        def set_banner(self, banner):
            self.list_item.setArt({'banner': banner})

        def set_watched_flags(self, infolabels, flag, resume_time=0, total_time=0):
            """
            set the needed flags on a listitem for watched or resume icons
            :param self:
            :param infolabels:
            :type infolabels: dict
            :param flag:
            :type flag: WatchedStatus
            :param resume_time:
            :type resume_time: int
            :param total_time:
            :type total_time: int
            :return:
            """
            if flag == WatchedStatus.UNWATCHED:
                infolabels['playcount'] = 0
                infolabels['overlay'] = 4
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))
            elif flag == WatchedStatus.WATCHED:
                infolabels['playcount'] = 1
                infolabels['overlay'] = 5
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))
            elif flag == WatchedStatus.PARTIAL and plugin_addon.getSetting('file_resume') == 'true':
                self.list_item.setProperty('ResumeTime', str(resume_time))
                if total_time > 0:
                    self.list_item.setProperty('TotalTime', str(total_time))

        def resume(self):
            resume = self.list_item.getProperty('ResumeTime')
            if resume is None or resume == '':
                return
            self.list_item.setProperty('StartOffset', resume)

    class Sorting(object):
        _parent = None  # type: type[Kodi16Proxy]
        _sorting_types = []

        @classmethod
        def __init__(cls, proxy):
            # type: (object, Kodi16Proxy) -> None
            cls._parent = proxy.__class__

        class SortingMethod(object):
            def __init__(self, types, container_id, name, listitem_id):
                self.container_id = container_id
                self.name = name
                self.listitem_id = listitem_id
                types.append(self)

        # There are apparently two lists. SetSortMethod uses a container sorting list, and ListItem uses the one from stubs
        import xbmcplugin
        none = SortingMethod(_sorting_types, 45, "Server", xbmcplugin.SORT_METHOD_UNSORTED)
        label = SortingMethod(_sorting_types, 1, "Label", xbmcplugin.SORT_METHOD_LABEL)
        date = SortingMethod(_sorting_types, 2, "Date", xbmcplugin.SORT_METHOD_DATE)
        title = SortingMethod(_sorting_types, 7, "Title", xbmcplugin.SORT_METHOD_TITLE)
        time = SortingMethod(_sorting_types, 9, "Duration", xbmcplugin.SORT_METHOD_DURATION)
        year = SortingMethod(_sorting_types, 16, "Year", xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        rating = SortingMethod(_sorting_types, 17, "Rating", xbmcplugin.SORT_METHOD_VIDEO_RATING)
        user_rating = SortingMethod(_sorting_types, 18, "User Rating", xbmcplugin.SORT_METHOD_VIDEO_USER_RATING)
        episode_number = SortingMethod(_sorting_types, 23, "Episode", xbmcplugin.SORT_METHOD_EPISODE)
        sort_title = SortingMethod(_sorting_types, 29, "Sort Title", xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)

        string2id = dict((k.name, k.container_id) for k in _sorting_types)
        # inverse dict
        id2string = dict((v, k) for k, v in string2id.items())

        @classmethod
        def set_sort_method(cls, content):
            method_for_sorting = cls.string2id.get(content, cls.none.container_id)
            if method_for_sorting == cls.none.container_id:
                return
            cls._parent.executebuiltin('Container.SetSortMethod(' + str(method_for_sorting) + ')')

        @classmethod
        def add_sort_method(cls, method):
            xbmcplugin.addSortMethod(plugin_router.handle, method)

    class Util(object):
        try:
            from sqlite3 import dbapi2 as _database
        except:
            # noinspection PyUnresolvedReferences
            from pysqlite2 import dbapi2 as _database

        _parent = None  # type: type[Kodi16Proxy]
        _localize = None
        _kodi_settings_cache = {}

        @classmethod
        def __init__(cls, proxy):
            # type: (object, Kodi16Proxy) -> None
            cls._parent = proxy.__class__
            cls._localize = plugin_addon.getLocalizedString

        # noinspection SqlNoDataSourceInspection,SqlDialectInspection
        @classmethod
        def clear_listitem_cache(cls):
            """
            Clear mark for shokodi files in kodi db
            :return:
            """
            ret = cls._parent.Dialog.yes_no(cls._localize(30104), "\n".join([cls._localize(30081), cls._localize(30112)]))
            if ret:
                db_files = []
                db_path = os.path.join(translatePath('special://home'), 'userdata')
                db_path = os.path.join(db_path, 'Database')
                for r, d, f in os.walk(db_path):
                    for files in f:
                        if 'MyVideos' in files:
                            db_files.append(files)
                for db_file in db_files:
                    db_connection = cls._database.connect(os.path.join(db_path, db_file))
                    db_cursor = db_connection.cursor()
                    db_cursor.execute('DELETE FROM files WHERE strFilename like "%plugin.video.shokodi%"')
                    db_connection.commit()
                    db_connection.close()
                if len(db_files) > 0:
                    cls._parent.Dialog.ok('', cls._localize(30138))

        # noinspection SqlDialectInspection,SqlNoDataSourceInspection
        @classmethod
        def clear_image_cache(cls):
            """
            Clear image cache in kodi db
            :return:
            """
            ret = cls._parent.Dialog.yes_no(cls._localize(30104), cls._localize(30081), cls._localize(30112))
            if not ret:
                return

            db_files = cls._get_databases()
            for db_file in db_files:
                db_connection = cls._database.connect(db_file)
                db_cursor = db_connection.cursor()
                db_cursor.execute('DELETE FROM texture WHERE url LIKE "%%%s/api/%%"' % plugin_addon.getSetting('port'))
                db_connection.commit()
                db_cursor.execute('DELETE FROM texture WHERE url LIKE "%shokodi%"')
                db_connection.commit()
                db_connection.close()
            if len(db_files) > 0:
                cls._parent.Dialog.ok('', cls._localize(30138))

        @classmethod
        def _get_databases(cls):
            db_files = []
            db_path = os.path.join(translatePath('special://home'), 'userdata')
            db_path = os.path.join(db_path, 'Database')
            for basepath, dirs, files in os.walk(db_path):
                for file in files:
                    if 'Textures' not in file:
                        continue
                    db_files.append(os.path.join(db_path, file))
            return db_files

        @classmethod
        def move_to_index(cls, index, absolute=False):
            try:
                interval = 250
                wait_time = 4000
                elapsed = 0
                while elapsed < wait_time:
                    wind, control_list = cls._get_control_list()
                    if control_list is not None:
                        cls.move_position_on_list(control_list, index, absolute)
                        return
                    cls._parent.sleep(interval)
                    elapsed += interval
            except:
                eh.exception(eh.ErrorPriority.HIGH, cls._localize(30243))

        @classmethod
        def _get_control_list(cls):
            try:
                # because of how Window works, we need to keep it loaded for as long as we use control_list
                wind = xbmcgui.Window(xbmcgui.getCurrentWindowId())
                control_list = wind.getControl(wind.getFocusId())
                if not isinstance(control_list, xbmcgui.ControlList):
                    return None, None

                return wind, control_list
            except:
                pass

        @classmethod
        def move_position_on_list(cls, control_list, position=0, absolute=False):
            # type: (xbmcgui.ControlList, int, bool) -> None
            """
            Move to the position in a list - use episode number for position
            Args:
                control_list: the list control
                position: the move_position_on_listindex of the item not including settings
                absolute: bypass setting and set position directly
            """
            if not absolute:
                if position < 0:
                    position = 0
                if plugin_addon.getSetting('show_continue') == 'true':
                    position = int(position + 1)
                if cls.get_kodi_setting('filelists.showparentdiritems'):
                    position = int(position + 1)
            try:
                size = control_list.size()
                if position == size:
                    position = size - 1

                control_list.selectItem(position)
            except:
                eh.exception(eh.ErrorPriority.HIGH, cls._localize(30243))

        @staticmethod
        def jsonrpc(method, params):
            try:
                values = (method, json.dumps(params))
                request = '{"jsonrpc":"2.0","method":"%s","params":%s, "id": 1}' % values
                return_data = xbmc.executeJSONRPC(request)
                result = json.loads(return_data)
                return result
            except:
                eh.exception(eh.ErrorPriority.HIGH, 'JSONRPC failed')
                return None

        @classmethod
        def get_kodi_setting(cls, setting):
            try:
                if setting in cls._kodi_settings_cache:
                    return cls._kodi_settings_cache[setting]

                method = 'Settings.GetSettingValue'
                params = {'setting': setting}
                result = cls.jsonrpc(method, params)
                if result is not None and 'result' in result and 'value' in result['result']:
                    result = result['result']['value']
                    cls._kodi_settings_cache[setting] = result
                    return result
            except:
                eh.exception(eh.ErrorPriority.HIGH)
            return None

        @staticmethod
        def is_dialog_active():
            x = -1
            try:
                x = xbmcgui.getCurrentWindowDialogId()
                x = int(x)
            except:
                pass
            # https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/WindowIDs.h
            if 10099 <= x <= 10160:
                return True

            return False
