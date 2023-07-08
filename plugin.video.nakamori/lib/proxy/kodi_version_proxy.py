from distutils.version import LooseVersion

import xbmc
from lib.nakamori_utils.globalvars import plugin_addon


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
        :rtype Union[str, int]
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
        :rtype Union[str, int]
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
        :return: string or list
        """
        temp_genre = ' | '.join(tag_obj_string)
        return temp_genre


class Kodi17Proxy(Kodi16Proxy):
    def __init__(self):
        Kodi16Proxy.__init__(self)

    def user_agent(self):
        return xbmc.getUserAgent()


class Kodi18Proxy(Kodi17Proxy):
    def __init__(self):
        Kodi17Proxy.__init__(self)
        plugin_addon.setSetting('kodi18', 'true')

    def external_player(self, player_obj):
        return player_obj.isExternalPlayer()

    def parse_tags(self, tag_obj_list):
        return tag_obj_list


def get_kodi_version():
    """
    This returns a LooseVersion instance containing the kodi version (16.0, 16.1, 17.0, etc)
    """
    version_string = xbmc.getInfoLabel('System.BuildVersion')
    # Version string is verbose, looking something like "17.6 Krypton Build 123456..."
    # use only the first part
    version_string = version_string.split(' ')[0]
    return LooseVersion(version_string)


kodi_version = get_kodi_version()

if kodi_version < LooseVersion('17.0'):
    kodi_proxy = Kodi16Proxy()
elif kodi_version < LooseVersion('17.9'):
    kodi_proxy = Kodi17Proxy()
else:
    kodi_proxy = Kodi18Proxy()
