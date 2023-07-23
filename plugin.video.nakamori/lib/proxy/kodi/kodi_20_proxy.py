import lib.error_handler as eh
from lib.proxy.kodi.kodi_19_proxy import Kodi19Proxy


class Kodi20Proxy(Kodi19Proxy):
    def __init__(self):
        Kodi19Proxy.__init__(self)

    class ListItem(Kodi19Proxy.ListItem):
        def __init__(self, label='', label2='', path='', offscreen=False):
            Kodi19Proxy.ListItem.__init__(self, label, label2, path, offscreen)

        def set_info(self, type, infoLabels):
            video = self.videoTag
            if type != 'video':
                return
            try:
                video.setTitle(self.list_item.getLabel())
                if 'aired' in infoLabels:
                    video.setFirstAired(infoLabels['aired'])
                if 'mediatype' in infoLabels:
                    video.setMediaType(infoLabels['mediatype'])
                if 'path' in infoLabels:
                    video.setPath(infoLabels['path'])
                if 'sorttitle' in infoLabels:
                    video.setSortTitle(infoLabels['sorttitle'])
                if 'originaltitle' in infoLabels:
                    video.setOriginalTitle(infoLabels['originaltitle'])
                if 'plot' in infoLabels:
                    video.setPlot(infoLabels['plot'])
                if 'plotoutline' in infoLabels:
                    video.setPlotOutline(infoLabels['plotoutline'])
                if 'dateadded' in infoLabels:
                    video.setDateAdded(infoLabels['dateadded'])
                if 'year' in infoLabels and infoLabels['year'] is not None and infoLabels['year'] != '':
                    video.setYear(int(infoLabels['year']))
                if 'mpaa' in infoLabels:
                    video.setMpaa(infoLabels['mpaa'])
                if 'duration' in infoLabels:
                    video.setDuration(int(infoLabels['duration']))
                if 'genre' in infoLabels and infoLabels['genre'] is not None and infoLabels['genre'] != '':
                    video.setGenres(infoLabels['genre'])
                if 'tag' in infoLabels:
                    video.setTags(infoLabels['tag'])
                if 'trailer' in infoLabels:
                    video.setTrailer(infoLabels['trailer'])
                if 'tagline' in infoLabels:
                    video.setTagLine(infoLabels['tagline'])
                if 'studio' in infoLabels and infoLabels['studio'] != '':
                    video.setStudios([infoLabels['studio']])
                if 'season' in infoLabels:
                    video.setSeason(infoLabels['season'])
                if 'episode' in infoLabels:
                    video.setEpisode(infoLabels['episode'])
                if 'userrating' in infoLabels:
                    video.setUserRating(int(infoLabels['userrating']))
            except:
                eh.exception(eh.ErrorPriority.HIGHEST)
