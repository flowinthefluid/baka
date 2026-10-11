"""Fresh Open-Meteo conditions for cameras with documented coordinates."""
import json
import time
from urllib.parse import urlencode

from resources.lib.livestreams import webcam_now
from resources.lib.livestreams.providers import weather

GROUPS = (('storm', 32960), ('snowfall', 32961), ('rain', 32962),
          ('fog', 32963), ('clear', 32964), ('cloudy', 32965), ('unknown', 32966))
API = 'https://api.open-meteo.com/v1/forecast'


def conditions(current, now=None):
    now = time.time() if now is None else now
    if not isinstance(current, dict):
        return ('unknown',)
    try:
        if not -900 <= now - float(current['time']) <= 3600:
            return ('unknown',)
        code = int(current['weather_code'])
        gust = float(current.get('wind_gusts_10m') or 0)
    except (KeyError, TypeError, ValueError):
        return ('unknown',)
    groups = []
    if code in (95, 96, 99) or gust >= 75:
        groups.append('storm')
    if code in (71, 73, 75, 77, 85, 86):
        groups.append('snowfall')
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        groups.append('rain')
    if code in (45, 48):
        groups.append('fog')
    if code in (0, 1):
        groups.append('clear')
    if code in (2, 3):
        groups.append('cloudy')
    return tuple(groups)


def _fetch(url):
    import requests
    with requests.get(url, timeout=(3, 6), stream=True) as response:
        response.raise_for_status()
        parts, size = [], 0
        deadline = time.monotonic() + 10
        for chunk in response.iter_content(chunk_size=8192):
            size += len(chunk)
            if size > 512 * 1024 or time.monotonic() > deadline:
                raise ValueError('Weather response exceeds its read budget')
            parts.append(chunk)
        return json.loads(b''.join(parts))


def group_channels(channels, fetch=None, now=None, cancelled=None):
    fetch = fetch or _fetch
    now = time.time() if now is None else now
    cancelled = cancelled or (lambda: False)
    unique = {channel['id']: channel for channel in channels}
    positions = {}
    for channel in unique.values():
        position = webcam_now.coordinates(channel)
        if position is not None:
            positions.setdefault(tuple(round(value, 3) for value in position), []).append(channel)
    observations, pending = {}, []
    for position in positions:
        cached = weather._cache_get('webcam_weather_%s_%s' % position)
        if isinstance(cached, dict) and conditions(cached, now) != ('unknown',):
            observations[position] = cached
        else:
            pending.append(position)
    for offset in range(0, len(pending), 50):
        if cancelled():
            break
        batch = pending[offset:offset + 50]
        params = {'latitude': ','.join(str(pos[0]) for pos in batch),
                  'longitude': ','.join(str(pos[1]) for pos in batch),
                  'current': 'weather_code,wind_gusts_10m', 'timeformat': 'unixtime',
                  'timezone': 'GMT', 'wind_speed_unit': 'kmh'}
        try:
            data = fetch(API + '?' + urlencode(params))
            values = data if isinstance(data, list) else [data]
            if len(values) != len(batch):
                continue
            for position, value in zip(batch, values):
                observation = value.get('current') if isinstance(value, dict) else None
                if conditions(observation, now) != ('unknown',):
                    observations[position] = observation
                    weather._cache_set('webcam_weather_%s_%s' % position, observation)
        except (OSError, ValueError, TypeError):
            continue
    result = {key: [] for key, _label in GROUPS}
    for channel in unique.values():
        position = webcam_now.coordinates(channel)
        observation = observations.get(tuple(round(value, 3) for value in position)) if position else None
        for key in conditions(observation, now):
            result[key].append(channel)
    return result