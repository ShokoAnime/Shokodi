import xbmc

from lib.proxy.kodi.kodi_16_proxy import Kodi16Proxy


class Kodi17Proxy(Kodi16Proxy):
    def __init__(self):
        Kodi16Proxy.__init__(self)

    def user_agent(self):
        return xbmc.getUserAgent()
