# -*- coding: utf-8 -*-
"""
ListItem factories: all Kodi presentation logic, injected with a SettingsProvider.

SettingsProvider wraps plugin_addon so behaviour driven by settings is configured
at construction time rather than scattered across model files.

Usage:
    settings = SettingsProvider(plugin_addon)
    factory  = ListItemFactory(settings)
    li       = factory.build(item)          # any Directory subtype
    factory.add_sort_methods(series)
    factory.apply_default_sorting(series)
"""
import random
import time

from lib.proxy.kodi import kodi_proxy
from lib.proxy.kodi.enums import WatchedStatus
from lib.proxy.kodi.unique_ids import UniqueIds
from lib.proxy.python import proxy as pyproxy
from lib.shoko import File, Episode, Series, SeriesTypeList, Group, Filter, CustomItem
from lib.utils import model_utils
from plugin_routes import PluginRoutes
from script_routes import ScriptRoutes
from lib.utils.globalvars import plugin_router, script_router


# ---------------------------------------------------------------------------
# Settings provider
# ---------------------------------------------------------------------------

class SettingsProvider(object):
    """Thin wrapper around plugin_addon for injection / testability."""

    def __init__(self, addon):
        self._addon = addon

    def get(self, key):
        return self._addon.getSetting(key)

    def localize(self, string_id):
        return self._addon.getLocalizedString(string_id)


# ---------------------------------------------------------------------------
# Per-type factories
# ---------------------------------------------------------------------------

class _BaseFactory(object):
    def __init__(self, settings):
        self._s = settings

    # -- shared helpers -----------------------------------------------------

    def _hide_ratings(self, infolabels, watched_status, rating_type_filter):
        """Remove 'rating' from infolabels according to hide_rating settings.

        rating_type_filter: 'Episodes' or 'Series' — the type that is NOT hidden.
        """
        hide_type = self._s.get('hide_rating_type')
        if hide_type == rating_type_filter:
            return
        hide_mode = self._s.get('hide_rating')
        if hide_mode == 'Always':
            infolabels.pop('rating', None)
        elif hide_mode == 'Unwatched':
            if watched_status != WatchedStatus.WATCHED:
                infolabels.pop('rating', None)
        elif hide_mode == 'All Unwatched':
            if watched_status == WatchedStatus.UNWATCHED:
                infolabels.pop('rating', None)

    def _hide_description(self, infolabels, watched_status):
        if watched_status == WatchedStatus.WATCHED:
            return
        if not kodi_proxy.Util.get_kodi_setting('videolibrary.showunwatchedplots') \
                or self._s.get('hide_plot') == 'true':
            infolabels['plot'] = self._s.localize(30079)


# ---------------------------------------------------------------------------

class FilterListItemFactory(_BaseFactory):
    def build(self, f: Filter):
        url = f.get_plugin_url()
        li = kodi_proxy.ListItem(f.name, path=url)
        li.set_path(url)
        li.set_info(type='video', infoLabels={'Title': f.name, 'Plot': f.name})
        li.set_art(f)
        return li.list_item

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.title.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.date.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.rating.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.year.listitem_id)

    def apply_default_sorting(self):
        kodi_proxy.Sorting.set_sort_method(self._s.get('default_sort_series'))


class CustomItemListItemFactory(_BaseFactory):
    def build(self, item: CustomItem):
        url = item.get_plugin_url()
        li = kodi_proxy.ListItem(item.name, path=url)
        li.set_path(url)
        li.set_info(type='video', infoLabels=item.get_infolabels())
        li.set_art(item)
        context = item.get_context_menu_items()
        if context:
            li.add_context_menu_items(context)
        return li.list_item


class GroupListItemFactory(_BaseFactory):
    def build(self, group: Group):
        url = group.get_plugin_url()
        li = kodi_proxy.ListItem(group.name, path=url)
        infolabels = self._get_infolabels(group)
        li.set_path(url)
        li.set_watched_flags(infolabels, group.is_watched(), 1)

        watched_status = group.is_watched()
        self._hide_ratings(infolabels, watched_status, 'Episodes')
        self._hide_description(infolabels, watched_status)

        li.set_rating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.set_info(type='video', infoLabels=infolabels)
        li.set_cast(group.actors)
        li.set_property('TotalEpisodes', str(group.get_total_episodes()))
        li.set_property('WatchedEpisodes', str(group.get_watched_episodes()))
        li.set_property('UnWatchedEpisodes', str(group.get_total_episodes() - group.get_watched_episodes()))

        context = self._get_context_menu_items(group)
        if context:
            li.add_context_menu_items(context)

        if group.fanart_list:
            group.fanart = random.choice(group.fanart_list)
        if group.banner_list:
            group.banner = random.choice(group.banner_list)
        li.set_art(group)
        return li.list_item

    def _get_infolabels(self, group: Group):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(group.actors)
        return {
            'aired': group.date,
            'date': model_utils.get_date(group.date),
            'genre': group.tags,
            'plot': group.overview,
            'premiered': group.date,
            'rating': group.rating,
            'title': group.name,
            'userrating': group.user_rating,
            'path': group.get_plugin_url(),
            'cast': cast,
            'castandrole': roles,
            'mediatype': 'tvshow',
            'episode': group.get_total_episodes(),
            'watchedepisodes': group.get_watched_episodes(),
        }

    def _get_context_menu_items(self, group: Group):
        context_menu = []
        watched_item = (
            self._s.localize(30126),
            script_router.url_for(ScriptRoutes.set_group_watched_status, group.id, True))
        unwatched_item = (
            self._s.localize(30127),
            script_router.url_for(ScriptRoutes.set_group_watched_status, group.id, False))
        if self._s.get('context_krypton_watched') == 'true':
            watched = group.is_watched()
            if watched == WatchedStatus.WATCHED:
                context_menu.append(unwatched_item)
            elif watched == WatchedStatus.UNWATCHED:
                context_menu.append(watched_item)
            else:
                context_menu.append(watched_item)
                context_menu.append(unwatched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)
        return context_menu

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.title.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.date.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.rating.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.year.listitem_id)

    def apply_default_sorting(self):
        kodi_proxy.Sorting.set_sort_method(self._s.get('default_sort_series'))


class SeriesListItemFactory(_BaseFactory):
    def build(self, series: Series, url=None):
        if url is None:
            url = series.get_plugin_url()

        li = kodi_proxy.ListItem(series.name, path=url)
        infolabels = self._get_infolabels(series, url)
        li.set_path(url)
        li.set_watched_flags(infolabels, series.is_watched(), 1)

        ids = UniqueIds()
        ids.anidb_id = series.anidb_id
        ids.shoko_aid = series.id
        li.set_unique_ids(ids)

        watched_status = series.is_watched()
        self._hide_ratings(infolabels, watched_status, 'Episodes')
        self._hide_description(infolabels, watched_status)
        self._hide_title(infolabels, series, watched_status)

        li.set_rating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.set_info(type='video', infoLabels=infolabels)
        li.set_cast(series.actors)
        li.set_property('TotalEpisodes', str(series.get_total_episodes()))
        li.set_property('WatchedEpisodes', str(series.get_watched_episodes()))
        li.set_property('UnWatchedEpisodes', str(series.get_total_episodes() - series.get_watched_episodes()))
        if series.hash is not None:
            li.set_property('hash', series.hash)

        context = self._get_context_menu_items(series)
        if context:
            li.add_context_menu_items(context)

        if series.fanart_list:
            series.fanart = random.choice(series.fanart_list)
        if series.banner_list:
            series.banner = random.choice(series.banner_list)
        li.set_art(series)
        return li.list_item

    def _get_infolabels(self, series: Series, url):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(series.actors)
        infolabels = {
            'size': series.file_size,
            'date': model_utils.get_date(series.date),
            'genre': series.tags,
            'year': series.year,
            'season': series.season,
            'sortseason': series.season,
            'rating': series.rating,
            'userrating': series.user_rating,
            'cast': cast,
            'castandrole': roles,
            'mpaa': series.mpaa,
            'plot': series.overview,
            'plotoutline': series.outline,
            'title': series.name,
            'originaltitle': series.alternate_name,
            'sorttitle': series.name,
            'tagline': ', '.join(series.tags) if isinstance(series.tags, list) else series.tags,
            'tvshowtitle': series.name,
            'premiered': series.date,
            'tag': ['shokodi', 'series'],
            'aired': series.date,
            'votes': series.votes,
            'path': url,
            'mediatype': series.item_type,
        }

        e = series.items[0] if len(series.items) > 0 else None
        if e is not None:
            f = e.get_file()
            if f is not None:
                infolabels['dateadded'] = f.date_added
                infolabels['studio'] = f.group

        infolabels['episode'] = series.get_total_episodes()
        infolabels['watchedepisodes'] = series.get_watched_episodes()
        return infolabels

    def _hide_title(self, infolabels, series, watched_status):
        pass  # Series titles are never hidden

    def _get_context_menu_items(self, series: Series):
        context_menu = []
        watched_item = (
            self._s.localize(30126),
            script_router.url_for(ScriptRoutes.set_series_watched_status, series.id, True))
        unwatched_item = (
            self._s.localize(30127),
            script_router.url_for(ScriptRoutes.set_series_watched_status, series.id, False))

        if self._s.get('context_krypton_watched') == 'true':
            watched = series.is_watched()
            if watched == WatchedStatus.WATCHED:
                context_menu.append(unwatched_item)
            elif watched == WatchedStatus.UNWATCHED:
                context_menu.append(watched_item)
            else:
                context_menu.append(watched_item)
                context_menu.append(unwatched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        if self._s.get('context_show_vote_Series') == 'true':
            context_menu.append((
                self._s.localize(30124),
                script_router.url_for(ScriptRoutes.vote_for_series, series.id)))

        return context_menu

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.episode_number.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.date.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.title.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.rating.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.year.listitem_id)

    def apply_default_sorting(self):
        kodi_proxy.Sorting.set_sort_method(self._s.get('default_sort_episodes'))


class SeriesTypeListListItemFactory(_BaseFactory):
    def build(self, stl: SeriesTypeList):
        url = stl.get_plugin_url()
        li = kodi_proxy.ListItem(stl.episode_type, path=url)
        infolabels = self._get_infolabels(stl)
        li.set_path(url)
        li.set_watched_flags(infolabels, stl.is_watched(), 1)

        watched_status = stl.is_watched()
        self._hide_ratings(infolabels, watched_status, 'Episodes')
        self._hide_description(infolabels, watched_status)

        li.set_rating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.set_info(type='video', infoLabels=infolabels)
        li.set_cast(stl.series.actors)
        li.set_property('TotalEpisodes', str(stl.get_total_episodes()))
        li.set_property('WatchedEpisodes', str(stl.get_watched_episodes()))
        li.set_property('UnWatchedEpisodes', str(stl.get_total_episodes() - stl.get_watched_episodes()))

        context = self._get_context_menu_items(stl)
        if context:
            li.add_context_menu_items(context)
        li.set_art(stl)
        return li.list_item

    def _get_infolabels(self, stl: SeriesTypeList):
        series = stl.series
        return {
            'aired': series.date,
            'date': model_utils.get_date(series.date),
            'originaltitle': series.alternate_name,
            'genre': series.tags,
            'plot': series.overview,
            'premiered': series.date,
            'rating': series.rating,
            'season': series.season,
            'title': stl.episode_type,
            'userrating': series.user_rating,
            'path': stl.get_plugin_url(),
            'mediatype': 'tvshow',
            'episode': stl.get_total_episodes(),
            'watchedepisodes': stl.get_watched_episodes(),
        }

    def _get_context_menu_items(self, stl: SeriesTypeList):
        context_menu = []
        watched_item = (
            self._s.localize(30126),
            script_router.url_for(ScriptRoutes.set_series_watched_status, stl.series.id, True))
        unwatched_item = (
            self._s.localize(30127),
            script_router.url_for(ScriptRoutes.set_series_watched_status, stl.series.id, False))

        if self._s.get('context_krypton_watched') == 'true':
            watched = stl.is_watched()
            if watched == WatchedStatus.WATCHED:
                context_menu.append(unwatched_item)
            elif watched == WatchedStatus.UNWATCHED:
                context_menu.append(watched_item)
            else:
                context_menu.append(watched_item)
                context_menu.append(unwatched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        if self._s.get('context_show_vote_Series') == 'true':
            context_menu.append((
                self._s.localize(30124),
                script_router.url_for(ScriptRoutes.vote_for_series, stl.series.id)))

        return context_menu

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.episode_number.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.date.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.title.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.rating.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.year.listitem_id)

    def apply_default_sorting(self):
        kodi_proxy.Sorting.set_sort_method(self._s.get('default_sort_episodes'))


class EpisodeListItemFactory(_BaseFactory):
    def build(self, ep: Episode, url=None):
        if url is None:
            url = ep.get_plugin_url()

        li = kodi_proxy.ListItem(ep.name, path=url)
        li.set_path(url)
        infolabels = self._get_infolabels(ep, url)

        f = ep.get_file()
        file_duration = kodi_proxy.duration_to_kodi(f.duration) if f is not None else 0
        if ep.watched:
            li.set_watched_flags(infolabels, WatchedStatus.WATCHED, total_time=file_duration)
        elif f is not None and f.resume_time > 0:
            li.set_watched_flags(infolabels, WatchedStatus.PARTIAL,
                                 resume_time=f.resume_time, total_time=file_duration)
        else:
            li.set_watched_flags(infolabels, WatchedStatus.UNWATCHED, total_time=file_duration)

        watched_status = ep.is_watched()
        self._apply_hide_images(ep, li, watched_status)
        self._hide_title(infolabels, ep, watched_status)
        self._hide_ratings(infolabels, watched_status, 'Series')
        self._hide_description(infolabels, watched_status)

        li.set_rating('anidb', float(infolabels.get('rating', 0.0)), infolabels.get('votes', 0), True)
        li.set_info(type='video', infoLabels=infolabels)
        li.set_art(ep)
        li.set_cast(ep.actors)

        ids = UniqueIds()
        ids.shoko_eid = ep.id
        if ep.series_id != 0:
            ids.shoko_aid = ep.series_id
        li.set_unique_ids(ids)

        if f is not None:
            model_utils.set_stream_info(li, f)

        context = self._get_context_menu_items(ep)
        if context:
            li.add_context_menu_items(context)

        if ep.resume:
            li.resume()

        return li.list_item

    def _get_infolabels(self, ep: Episode, url):
        cast, roles = model_utils.convert_cast_and_role_to_legacy(ep.actors)
        infolabels = {
            'date': model_utils.get_date(ep.date),
            'genre': ep.tags,
            'year': ep.year,
            'episode': ep.episode_number,
            'season': ep.season,
            'rating': ep.rating,
            'userrating': ep.user_rating,
            'cast': cast,
            'castandrole': roles,
            'plot': ep.overview,
            'plotoutline': ep.outline,
            'title': ep.name,
            'originaltitle': ep.alternate_name,
            'sorttitle': model_utils.get_sort_name(ep),
            'tvshowtitle': ep.series_name,
            'premiered': ep.date,
            'aired': ep.date,
            'votes': ep.votes,
            'path': url,
            'mediatype': ep.item_type,
        }

        f = ep.items[0] if len(ep.items) > 0 else None
        if f is not None:
            infolabels['duration'] = kodi_proxy.duration_to_kodi(f.duration)
            infolabels['size'] = f.size
            infolabels['dateadded'] = f.date_added

        return infolabels

    def _apply_hide_images(self, ep: Episode, li, watched_status):
        if self._s.get('hide_images') == 'true' and watched_status != WatchedStatus.WATCHED:
            ep.apply_image_override('hidden.png')

    def _hide_title(self, infolabels, ep: Episode, watched_status):
        hide_setting = self._s.get('hide_title')
        if hide_setting == 'Never' or watched_status == WatchedStatus.WATCHED:
            return
        if ep.episode_type == 'Special':
            if hide_setting == 'Episodes':
                return
            infolabels['title'] = self._s.localize(30076) + ' ' + str(ep.episode_number)
        elif ep.episode_type == 'Episode':
            if hide_setting == 'Specials':
                return
            infolabels['title'] = self._s.localize(30076) + ' ' + str(ep.episode_number)

    def _get_context_menu_items(self, ep: Episode):
        context_menu = []

        f = ep.get_file()
        if self._s.get('context_show_play') == 'true' and f is not None:
            url = 'RunPlugin(%s)' % plugin_router.url_for(PluginRoutes.play_video, ep.id, f.id)
            context_menu.append((self._s.localize(30065), url))

        if f is not None and f.resume_time > 0 and self._s.get('file_resume') == 'true':
            label = self._s.localize(30141) + ' (%s)' % time.strftime('%H:%M:%S', time.gmtime(f.resume_time))
            url = 'RunPlugin(%s)' % plugin_router.url_for(PluginRoutes.resume_video, ep.id, f.id)
            context_menu.append((label, url))

        if self._s.get('context_show_play_no_watch') == 'true' and f is not None:
            context_menu.append((
                self._s.localize(30132),
                'RunPlugin(%s)' % plugin_router.url_for(PluginRoutes.play_video_without_marking, ep.id, f.id)))

        if self._s.get('context_pick_file') == 'true' and len(ep.items) > 1:
            context_menu.append((
                self._s.localize(30133),
                script_router.url_for(ScriptRoutes.file_list, ep.id)))

        watched_item = (
            self._s.localize(30128),
            script_router.url_for(ScriptRoutes.set_episode_watched_status, ep_id=ep.id, watched=True))
        unwatched_item = (
            self._s.localize(30129),
            script_router.url_for(ScriptRoutes.set_episode_watched_status, ep_id=ep.id, watched=False))

        if self._s.get('context_krypton_watched') == 'true':
            if ep.watched:
                context_menu.append(unwatched_item)
            else:
                context_menu.append(watched_item)
        else:
            context_menu.append(watched_item)
            context_menu.append(unwatched_item)

        if self._s.get('context_show_vote_Episode') == 'true':
            context_menu.append((
                self._s.localize(30125),
                script_router.url_for(ScriptRoutes.vote_for_episode, ep.id)))

        if self._s.get('context_show_vote_Series') == 'true' and ep.series_id != 0:
            context_menu.append((
                self._s.localize(30124),
                script_router.url_for(ScriptRoutes.vote_for_series, ep.series_id)))

        return context_menu

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.episode_number.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.date.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.title.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.rating.listitem_id)
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.year.listitem_id)

    def apply_default_sorting(self):
        kodi_proxy.Sorting.set_sort_method(self._s.get('default_sort_episodes'))


class FileListItemFactory(_BaseFactory):
    def build(self, f: File):
        url = f.get_plugin_url()
        li = kodi_proxy.ListItem(f.name, path=url)
        li.set_path(url)
        infolabels = self._get_infolabels(f, url)

        total_time = kodi_proxy.duration_to_kodi(f.duration)
        if f.resume_time > 0:
            li.set_watched_flags(infolabels, WatchedStatus.PARTIAL,
                                 resume_time=f.resume_time, total_time=total_time)
        li.set_info(type='video', infoLabels=infolabels)

        if f.resume:
            li.resume()

        model_utils.set_stream_info(li, f)
        li.set_art(f)

        context = self._get_context_menu_items(f)
        if context:
            li.add_context_menu_items(context)

        return li.list_item

    def _get_infolabels(self, f: File, url):
        return {
            'path': url,
            'mediatype': 'episode',
            'duration': kodi_proxy.duration_to_kodi(f.duration),
            'size': f.size,
            'dateadded': f.date_added,
        }

    def _get_context_menu_items(self, f: File):
        return [
            (self._s.localize(30120), script_router.url_for(ScriptRoutes.rescan_file, f.id)),
            (self._s.localize(30121), script_router.url_for(ScriptRoutes.rehash_file, f.id)),
            ('  ', 'empty'),
            (self._s.localize(30147), 'empty'),
            (self._s.localize(30148), 'empty'),
        ]

    def add_sort_methods(self):
        kodi_proxy.Sorting.add_sort_method(kodi_proxy.Sorting.none.listitem_id)

    def apply_default_sorting(self):
        pass


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class ListItemFactory(object):
    """Builds the right ListItem for any Directory subtype."""

    def __init__(self, settings):
        self._s = settings
        self._filter = FilterListItemFactory(settings)
        self._custom = CustomItemListItemFactory(settings)
        self._group = GroupListItemFactory(settings)
        self._series = SeriesListItemFactory(settings)
        self._stl = SeriesTypeListListItemFactory(settings)
        self._episode = EpisodeListItemFactory(settings)
        self._file = FileListItemFactory(settings)

    def build(self, item):
        # Import here to avoid circular imports at module load time
        from lib.shoko._filter import Filter, CustomItem
        from lib.shoko._group import Group
        from lib.shoko._series import Series, SeriesTypeList
        from lib.shoko._episode import Episode
        from lib.shoko._file import File

        if isinstance(item, CustomItem):
            return self._custom.build(item)
        if isinstance(item, Filter):
            return self._filter.build(item)
        if isinstance(item, Group):
            return self._group.build(item)
        if isinstance(item, SeriesTypeList):
            return self._stl.build(item)
        if isinstance(item, Series):
            return self._series.build(item)
        if isinstance(item, Episode):
            return self._episode.build(item)
        if isinstance(item, File):
            return self._file.build(item)
        # Fallback: generic
        url = item.get_plugin_url()
        li = kodi_proxy.ListItem(item.name, path=url)
        li.set_path(url)
        li.set_info(type='video', infoLabels={'Title': item.name, 'Plot': item.name})
        li.set_art(item)
        return li.list_item

    def build_episode(self, ep, url=None):
        """Build a ListItem for an episode with an optional URL override (used by player)."""
        return self._episode.build(ep, url=url)

    def build_file(self, f):
        """Build a ListItem for a file (used by player)."""
        return self._file.build(f)

    def add_sort_methods(self, item):
        from lib.shoko._filter import Filter, CustomItem
        from lib.shoko._group import Group
        from lib.shoko._series import Series, SeriesTypeList
        from lib.shoko._episode import Episode
        from lib.shoko._file import File

        if isinstance(item, (CustomItem,)):
            pass
        elif isinstance(item, Filter):
            self._filter.add_sort_methods()
        elif isinstance(item, Group):
            self._group.add_sort_methods()
        elif isinstance(item, (SeriesTypeList, Series)):
            self._series.add_sort_methods()
        elif isinstance(item, Episode):
            self._episode.add_sort_methods()
        elif isinstance(item, File):
            self._file.add_sort_methods()

    def apply_default_sorting(self, item):
        from lib.shoko._filter import Filter, CustomItem
        from lib.shoko._group import Group
        from lib.shoko._series import Series, SeriesTypeList
        from lib.shoko._episode import Episode
        from lib.shoko._file import File

        if isinstance(item, CustomItem):
            pass
        elif isinstance(item, Filter):
            self._filter.apply_default_sorting()
        elif isinstance(item, Group):
            self._group.apply_default_sorting()
        elif isinstance(item, (SeriesTypeList, Series)):
            self._series.apply_default_sorting()
        elif isinstance(item, Episode):
            self._episode.apply_default_sorting()
        elif isinstance(item, File):
            self._file.apply_default_sorting()
