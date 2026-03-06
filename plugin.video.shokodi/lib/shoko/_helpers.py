# -*- coding: utf-8 -*-
"""
Low-level helper functions for the Shoko v3 API.

All functions here are pure utilities with minimal dependencies.
Nothing in this module depends on other lib.shoko sub-modules.
"""
import json

from lib.proxy.python import proxy as pyproxy

_LISTING_MAX_WORKERS = 16

# Episode type name used internally - v3 API uses 'Normal' where v2 used 'Episode'
_EPISODE_TYPE_MAP = {
    'Normal': 'Episode',
    'Episode': 'Episode',
    'Special': 'Special',
    'Credits': 'Credits',
    'Trailer': 'Trailer',
    'Parody': 'Parody',
    'Other': 'Other',
}

_SPECIAL_KEY_MAP = {'IDs': 'ids'}


def _normalize_episode_type(ep_type):
    """Normalize v3 episode type names to internal names used by the codebase."""
    return _EPISODE_TYPE_MAP.get(ep_type, ep_type)


def _image_url(server_base, image_node):
    """Build the v3 image URL from an image object."""
    if not image_node:
        return ''
    source = image_node.get('source', '')
    img_type = image_node.get('type', '')
    img_id = image_node.get('id', '')
    if not source or not img_type or img_id == '':
        return ''
    return server_base + '/api/v3/Image/' + source + '/' + img_type + '/' + str(img_id)


def _get_airdate(json_node):
    """Extract and normalize air date from v3 API response."""
    air = json_node.get('airDate') or json_node.get('air') or ''
    if air in ('0001-01-01', '01-01-0001'):
        air = ''
    return air


def _get_rating(json_node):
    """Extract community rating from v3 API response."""
    rating_node = json_node.get('rating') or {}
    if isinstance(rating_node, dict):
        try:
            return float(str(rating_node.get('value') or 0).replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0
    try:
        return float(str(rating_node).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def _get_user_rating(json_node):
    """Extract user rating from v3 API response."""
    rating_node = json_node.get('userRating') or {}
    if isinstance(rating_node, dict):
        try:
            return float(str(rating_node.get('value') or 0).replace(',', '.'))
        except (ValueError, TypeError):
            return 0.0
    try:
        return float(str(rating_node).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


def _get_votes(json_node):
    """Extract vote count from v3 API response."""
    rating_node = json_node.get('rating') or {}
    if isinstance(rating_node, dict):
        return pyproxy.safe_int(rating_node.get('votes') or 0)
    return 0


def _preferred_image(image_list):
    """Return the preferred image from a list, or the first one if none is marked preferred."""
    if not image_list:
        return None
    preferred = next((x for x in image_list if x.get('preferred', False)), None)
    return preferred if preferred is not None else image_list[0]


def _ms_to_timespan(ms):
    """Convert milliseconds to .NET TimeSpan string (HH:MM:SS.fffffff)."""
    ms = int(ms)
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, ticks_ms = divmod(rem, 1000)
    return '%02d:%02d:%02d.%07d' % (hours, minutes, seconds, ticks_ms * 10000)


def _parse_timespan_ms(timespan):
    """Convert a .NET TimeSpan string (HH:MM:SS.fffffff or D.HH:MM:SS.fffffff) to milliseconds."""
    try:
        if not timespan or not isinstance(timespan, str):
            return 0
        # Strip days component if present (D.HH:MM:SS...)
        days = 0
        if timespan.count(':') >= 2 and '.' in timespan.split(':')[0]:
            day_str, timespan = timespan.split('.', 1)
            days = int(day_str)
        parts = timespan.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        sec_frac = parts[2].split('.')
        seconds = int(sec_frac[0])
        ms = int(sec_frac[1][:3].ljust(3, '0')) if len(sec_frac) > 1 else 0
        return ((days * 24 + hours) * 3600 + minutes * 60 + seconds) * 1000 + ms
    except (ValueError, IndexError, AttributeError):
        return 0


def _normalize_keys(obj):
    """Normalize v3 API response keys from PascalCase to camelCase.
    Handles all-uppercase keys (ID→id, URL→url) and special cases (IDs→ids).
    Also promotes ids.id to top-level id for convenience.
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in _SPECIAL_KEY_MAP:
                new_k = _SPECIAL_KEY_MAP[k]
            elif k and k == k.upper():
                new_k = k.lower()
            elif k:
                new_k = k[0].lower() + k[1:]
            else:
                new_k = k
            result[new_k] = _normalize_keys(v)
        ids = result.get('ids', {})
        if isinstance(ids, dict) and 'id' in ids and 'id' not in result:
            result['id'] = ids['id']
        return result
    elif isinstance(obj, list):
        return [_normalize_keys(i) for i in obj]
    return obj


def _get_json_list(json_body):
    """Parse a v3 API list response which may be a ListResult or a plain list."""
    if json_body is None:
        return []
    data = _normalize_keys(json.loads(json_body))
    if isinstance(data, list):
        return data
    # ListResult has a 'list' key
    return data.get('list', [])
