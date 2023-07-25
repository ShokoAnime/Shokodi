# -*- coding: utf-8 -*-
import xbmcgui
from lib.shoko_models import v2 as model
from lib.nakamori_utils.globalvars import *
from lib.proxy.python_version_proxy import python_proxy as pyproxy

ADDON = xbmcaddon.Addon('plugin.video.nakamori')
CWD = pyproxy.decode(ADDON.getAddonInfo('path'))

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

# lists
FIRST_DAY = 55

img = os.path.join(CWD, 'resources', 'media')
font_path = os.path.join(CWD, 'fonts')

# noinspection PyTypeChecker
profileDir = translatePath(ADDON.getAddonInfo('profile'))

color = ADDON.getSetting('ac_color')
font_ttf = ADDON.getSetting('ac_font')
font_size = ADDON.getSetting('ac_size')


class SeriesInfo(xbmcgui.WindowXML):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback, id, aid):
        self.window_type = 'window'
        self.calendar_collection = {}
        self.aid = aid
        self.id = id

    def onInit(self):
        busy = xbmcgui.DialogProgress()
        busy.create(ADDON.getLocalizedString(30017), ADDON.getLocalizedString(30018))
        use_aid = False
        if self.aid > 0:
            use_aid = True
        series = model.Series(self.aid, build_full_object=True, get_children=False, use_aid=use_aid)
        li = series.get_listitem()
        container_id = 450
        self.getControl(container_id).reset()
        self.getControl(container_id).addItem(li)
        self.addItem(li)

        busy.close()

        self.setFocus(self.getControl(901))

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()
        elif action == ACTION_NAV_BACK:
            self.close()
        elif action == xbmcgui.ACTION_MOVE_RIGHT:
            pass
        elif action == xbmcgui.ACTION_MOVE_LEFT:
            pass
        elif action == xbmcgui.ACTION_MOUSE_RIGHT_CLICK:
            pass
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            control_id = self.getFocus().getId()
            con = self.getControl(control_id)
            assert isinstance(con, xbmcgui.ControlList)
            aid = con.getSelectedItem().getProperty('aid')

            pass
        elif action == xbmcgui.ACTION_SELECT_ITEM:
            xbmcgui.Dialog().ok('soon', 'show soon')
        elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
            if self.getFocus().getId() == 1:
                xbmc.executebuiltin('Action(Back)')

    def onControl(self, control):
        pass

    def onFocus(self, control):
        pass


def open_seriesinfo(id=0, aid=0):
    ui = SeriesInfo('series_info.xml', CWD, 'Default', '1080i', id=id, aid=aid)
    ui.doModal()
    del ui
