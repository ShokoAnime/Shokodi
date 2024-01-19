from lib.proxy.kodi.kodi_17_proxy import Kodi17Proxy


class Kodi18Proxy(Kodi17Proxy):
    def __init__(self):
        Kodi17Proxy.__init__(self)

    def external_player(self, player_obj):
        return player_obj.isExternalPlayer()

    def parse_tags(self, tag_obj_list):
        return tag_obj_list
