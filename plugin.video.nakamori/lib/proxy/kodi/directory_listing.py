import sys

import xbmcgui
import xbmcplugin

from lib.proxy.kodi import ListItem


class DirectoryListing(object):
    """
    An optimized list to add directory items.
    There may be a speedup by calling `del dir_list`, but Kodi's GC is pretty aggressive
    """

    def __init__(self, content_type='', cache=False):
        self.pending = []
        self.handle = int(sys.argv[1])
        self._cache = cache
        self.success = True
        self._content_type = content_type
        if self._content_type != '':
            xbmcplugin.setContent(self.handle, content_type)
        self._immediate = False
        self._finished = False

    def set_immediate(self, immediate):
        self._immediate = immediate

    def set_cached(self):
        self._cache = True

    def set_content(self, content_type):
        self._content_type = content_type

        if self._content_type != '':
            xbmcplugin.setContent(self.handle, content_type)

    def extend(self, iterable):
        result_list = []
        for item in iterable:
            result = self.get_tuple(item)
            if result is not None:
                result_list.append(result)
        return self.pending.extend(result_list)

    def append(self, item, folder=True, total_items=0):
        result = self.get_tuple(item, folder)
        if result is not None:
            if self._immediate:
                if total_items != 0:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2], total_items)
                else:
                    return xbmcplugin.addDirectoryItem(self.handle, result[0], result[1], result[2])
            else:
                self.pending.append(result)
                return True
        else:
            raise RuntimeError('Attempting to Add Not a ListItem to the List')

    def insert(self, index, obj, folder=True):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = self.get_tuple(obj, folder)
        return self.pending.insert(index, item)

    def __getitem__(self, item):
        if self._immediate:
            raise RuntimeError('Cannot get items after adding. Immediate mode is enabled')
        return self.pending.__getitem__(item)

    def __setitem__(self, key, value):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        item = self.get_tuple(value, True)
        return self.pending.__setitem__(key, item)

    def __delitem__(self, key):
        if self._immediate:
            raise RuntimeError('Cannot change order of items after adding. Immediate mode is enabled')
        return self.pending.__delitem__(key)

    def finish(self):
        if self._finished:
            return
        if not self._immediate and len(self.pending) > 0:
            xbmcplugin.addDirectoryItems(self.handle, self.pending, self.pending.__len__())
        if xbmcplugin is not None:
            xbmcplugin.endOfDirectory(self.handle, succeeded=self.success, cacheToDisc=self._cache)
        self._finished = True

    def __del__(self):
        self.finish()

    @staticmethod
    def get_tuple(item, folder=True):
        if DirectoryListing.is_listitem(item):
            return item.getPath(), item, folder
        if isinstance(item, tuple):
            if len(item) == 2:
                if not DirectoryListing.is_listitem(item[0]):
                    return None
                return item[0].getPath(), item[0], item[1]
            if len(item) == 3:
                if not DirectoryListing.is_listitem(item[1]):
                    return None
                return item[0], item[1], item[2]
        return None

    @staticmethod
    def is_listitem(item):
        return isinstance(item, xbmcgui.ListItem) or isinstance(item, ListItem)
