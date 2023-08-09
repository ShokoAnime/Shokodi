import json


def get_installed_version():
    # retrieve current installed version
    import xbmc
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    json_query = json.loads(json_query)
    version_installed = []
    if 'result' in json_query and 'version' in json_query['result']:
        version_installed = json_query['result']['version']['major']
    return float(str(version_installed))


kodi_version = get_installed_version()

if kodi_version < 17:
    from lib.proxy.kodi.kodi_16_proxy import Kodi16Proxy
    kodi_proxy = Kodi16Proxy()
elif kodi_version < 18:
    from lib.proxy.kodi.kodi_17_proxy import Kodi17Proxy
    kodi_proxy = Kodi17Proxy()
elif kodi_version < 19:
    from lib.proxy.kodi.kodi_18_proxy import Kodi18Proxy
    kodi_proxy = Kodi18Proxy()
elif kodi_version < 20:
    from lib.proxy.kodi.kodi_19_proxy import Kodi19Proxy
    kodi_proxy = Kodi19Proxy()
else:
    from lib.proxy.kodi.kodi_20_proxy import Kodi20Proxy
    kodi_proxy = Kodi20Proxy()

ListItem = kodi_proxy.ListItem
