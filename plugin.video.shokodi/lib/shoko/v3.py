# -*- coding: utf-8 -*-
# v3.py is a compatibility shim. The implementation now lives in the
# individual _*.py modules within lib/shoko/. Import from lib.shoko directly.
from lib.shoko._api import ShokoApi, get_api
from lib.shoko._listitem import SettingsProvider, ListItemFactory
from lib.shoko._base import Directory
from lib.shoko._filter import CustomItem, Filter
from lib.shoko._group import Group
from lib.shoko._series import Series, SeriesTypeList, get_series_for_episode
from lib.shoko._episode import Episode
from lib.shoko._file import File
from lib.shoko._sizes import Sizes, get_sizes
