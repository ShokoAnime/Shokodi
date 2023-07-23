import xbmcgui

from lib.nakamori_utils.globalvars import *
from lib.proxy.kodi.enums import *


class Kodi16Proxy:
    def __init__(self):
        plugin_addon.setSetting('kodi18', 'false')

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
            :param infolabels
            :param flag:
            :type flag: WatchedStatus
            :param resume_time: int s
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
