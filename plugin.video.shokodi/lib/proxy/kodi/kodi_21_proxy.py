from lib.proxy.kodi.kodi_20_proxy import Kodi20Proxy
from lib.utils.globalvars import plugin_addon
from lib.proxy.kodi.enums import WatchedStatus


class Kodi21Proxy(Kodi20Proxy):
    def __init__(self):
        Kodi20Proxy.__init__(self)

    class ListItem(Kodi20Proxy.ListItem):
        def __init__(self, label='', label2='', path='', offscreen=False):
            Kodi20Proxy.ListItem.__init__(self, label, label2, path, offscreen)

        def set_watched_flags(self, infolabels, flag, resume_time=0, total_time=0):
            if flag == WatchedStatus.UNWATCHED:
                self.videoTag.setPlaycount(0)
            elif flag == WatchedStatus.WATCHED:
                self.videoTag.setPlaycount(1)
            elif flag == WatchedStatus.PARTIAL:
                self.videoTag.setPlaycount(0)
                if plugin_addon.getSetting('file_resume') == 'true' and resume_time > 0:
                    self.videoTag.setResumePoint(float(resume_time), float(total_time))


        def resume(self):
            try:
                resume_time = self.videoTag.getResumeTime()
                if resume_time and float(resume_time) > 0:
                    self.list_item.setProperty('StartOffset', str(int(float(resume_time))))
            except:
                pass
