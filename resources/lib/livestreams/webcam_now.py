"""Current solar conditions and deduplicated webcam catalogue statistics."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import math
from urllib.parse import urlsplit

from resources.lib.livestreams import webcam_geography
from resources.lib.vendor.astral import Observer
from resources.lib.vendor.astral.sun import elevation

GROUPS = (('sunrise', 32941), ('sunset', 32942), ('daylight', 32943),
          ('night', 32944), ('golden_hour', 32945), ('blue_hour', 32946),
          ('twilight', 32947), ('unlocated', 32948))


def coordinates(channel):
    location = channel.get('coordinates')
    if not isinstance(location, dict):
        return None
    values = (location.get('latitude'), location.get('longitude'))
    if any(isinstance(value, bool) for value in values):
        return None
    try:
        latitude, longitude = map(float, values)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def conditions(channel, now=None):
    position = coordinates(channel)
    if position is None:
        return ('unlocated',)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('A timezone-aware timestamp is required')
    observer = Observer(*position)
    altitude = elevation(observer, now, with_refraction=False)
    rising = elevation(observer, now + timedelta(minutes=5), with_refraction=False) > altitude
    groups = []
    if -6 <= altitude <= 6:
        groups.append('sunrise' if rising else 'sunset')
    if altitude >= -0.833:
        groups.append('daylight')
    if altitude < -6:
        groups.append('night')
    if -4 <= altitude <= 6:
        groups.append('golden_hour')
    if -6 <= altitude < -4:
        groups.append('blue_hour')
    if -18 <= altitude < -6:
        groups.append('twilight')
    return tuple(groups)


def group_channels(channels, now=None):
    now = now or datetime.now(timezone.utc)
    result = {key: [] for key, _label in GROUPS}
    unique = {channel['id']: channel for channel in channels}
    for channel in unique.values():
        for key in conditions(channel, now):
            result[key].append(channel)
    return result


def statistics(channels):
    cameras = list({channel['id']: channel for channel in channels
                    if channel['section'] in ('webcam', 'weather')}.values())
    topics, directories, continents = Counter(), Counter(), Counter()
    sources = set()
    for channel in cameras:
        topics.update(set(channel.get('genre') or ()))
        continents.update([webcam_geography.continent(channel)])
        directories.update({urlsplit(url).hostname for url in channel.get('directory_urls', [])
                            if urlsplit(url).hostname})
        sources.update(source['url'] for source in channel.get('sources', []) if source.get('url'))
    return {'cameras': len(cameras), 'sources': len(sources),
            'countries': len({channel['country'] for channel in cameras if channel['country'] != 'int'}),
            'locations': len({(channel['country'], channel['city']) for channel in cameras if channel.get('city')}),
            'positioned': sum(coordinates(channel) is not None for channel in cameras),
            'stations': sum(webcam_geography.is_weather_station(channel) for channel in cameras),
            'topics': topics, 'directories': directories, 'continents': continents}