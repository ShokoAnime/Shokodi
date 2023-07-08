# -*- coding: utf-8 -*-
from collections import defaultdict
from distutils.version import LooseVersion

import xbmcgui
from lib import error_handler
from lib.nakamori_utils.globalvars import *
from lib.proxy.python_version_proxy import python_proxy as pyproxy

ADDON = xbmcaddon.Addon(id='plugin.video.nakamori')
CWD = ADDON.getAddonInfo('path')
if isinstance(CWD, bytes):
    CWD = CWD.decode('utf-8')

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92

CLOSE_BUTTON = 202
CONTENT_TEXTBOX = 303


class Information(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFile, resourcePath, skin, skinRes):
        self.window_type = 'window'

    def onInit(self):
        _title = self.getControl(1)
        assert isinstance(_title, xbmcgui.ControlLabel)
        _title.setLabel('What\'s New')

        changelog_text = get_changelog_text()

        _textbox = self.getControl(5)
        assert isinstance(_textbox, xbmcgui.ControlTextBox)
        _textbox.setText(changelog_text)

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_NAV_BACK:
            self.close()

    def onControl(self, control):
        pass

    def onFocus(self, control):
        pass

    def onClick(self, control):
        pass


def get_changelog_text():
    # Populate the changelog internally
    changelog_path = os.path.join(pyproxy.decode(xbmcaddon.Addon(id='plugin.video.nakamori').getAddonInfo('path')),
                                  'changelog.txt')
    fstream = open(changelog_path, 'r')
    changelog = defaultdict(list)
    current_version = None
    for line in fstream.readlines():
        try:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('#'):
                continue
            if line.startswith('!--'):
                try:
                    current_version = LooseVersion(line.replace('!--', '').strip())
                    # current line is version so go to next line
                    continue
                except:
                    pass
            if current_version is None:
                continue
            changelog[current_version.vstring].append(line)
        except Exception as e:
            pass
    changelog.default_factory = None

    # build the text based on previous version.
    # This is important, as someone might open kodi for the first time in a while and skip several versions
    previous_version = LooseVersion(plugin_addon.getSetting('version'))
    versions = []
    for k, v in changelog.items():
        if LooseVersion(k) > previous_version:
            versions.append((k, v))
    versions.sort(reverse=True)

    changelog_text = ''
    for k, v in versions:
        changelog_text += 'Version ' + k
        for line in v:
            changelog_text += '\n- ' + line
        changelog_text += '\n'

    return changelog_text


def open_information():
    try:
        ui = Information('DialogTextViewer.xml', os.getcwd(), 'Default', '1080i')
        ui.doModal()
        del ui
    except:
        error_handler.exception(error_handler.ErrorPriority.HIGHEST)
    plugin_addon.setSetting('version', plugin_addon.getAddonInfo('version'))

