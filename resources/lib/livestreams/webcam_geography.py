"""World-wide webcam locations and explicitly documented weather stations."""
import json
import os
import re
from functools import lru_cache
from urllib.parse import urlsplit

CONTINENTS = (('africa', 32910), ('asia', 32911), ('europe', 32912),
              ('north_america', 32913), ('south_america', 32914),
              ('oceania', 32915), ('antarctica', 32916), ('other', 32917))


@lru_cache(maxsize=1)
def country_continents():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        'data', 'film_countries.json')
    with open(path, encoding='utf-8') as handle:
        rows = json.load(handle)['countries']
    result = {row['code'].lower(): row['region'] for row in rows}
    result.update({code: 'north_america' for code, region in result.copy().items()
                   if region in ('central_america', 'caribbean')})
    result['aq'] = 'antarctica'
    result.update({code:'north_america' for code in ('bl','bq','cw','sx')})
    result.update({'je':'europe','gg':'europe','im':'europe'})
    return result


def continent(channel):
    explicit = channel.get('continent')
    known = dict(CONTINENTS)
    return explicit if explicit in known else country_continents().get(channel.get('country'), 'other')


def is_weather_station(channel):
    station = channel.get('weather_station') or {}
    return bool(station.get('official') is True and station.get('name') and station.get('operator')
                and urlsplit(station.get('evidence_url', '')).scheme in ('http', 'https'))


def coordinates_from_page(text):
    from resources.lib.livestreams.webcam_extract import Page
    from resources.lib.livestreams.webcam_now import coordinates

    def validated(latitude, longitude):
        location = {'latitude': latitude, 'longitude': longitude}
        position = coordinates({'coordinates': location})
        return dict(zip(('latitude', 'longitude'), position)) if position else {}

    def find_geo(value):
        if isinstance(value, dict):
            if value.get('@type') == 'GeoCoordinates':
                return validated(value.get('latitude'), value.get('longitude'))
            for key in ('geo', 'location', 'contentLocation', '@graph'):
                result = find_geo(value.get(key))
                if result:
                    return result
        elif isinstance(value, list):
            for item in value:
                result = find_geo(item)
                if result:
                    return result
        return {}

    for script in re.findall(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            result = find_geo(json.loads(script))
            if result:
                return result
        except (TypeError, ValueError):
            pass
    tags = Page(text).tags
    values = {attrs.get('itemprop'): attrs.get('content') for tag, attrs in tags if tag == 'meta'}
    if 'latitude' in values and 'longitude' in values:
        return validated(values['latitude'], values['longitude'])
    for tag, attrs in tags:
        if tag == 'meta' and attrs.get('name') == 'geo.position':
            values = (attrs.get('content') or '').split(';')
            if len(values) == 2:
                return validated(*values)
    match = re.search(r'"coordinates"\s*:\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]', text)
    return validated(match.group(2), match.group(1)) if match else {}
