"""Solar lists use actual coordinates and count cameras, not topic links."""
from datetime import datetime, timezone

import pytest

from resources.lib.livestreams import webcam_now as current, webcam_topics
from resources.lib.livestreams import webcam_geography


def camera(identifier='one', latitude=0, longitude=0):
    return {'id': identifier, 'name': 'View', 'section': 'webcam', 'country': 'us', 'city': 'Place',
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'genre': ['mountains', 'rockies'], 'sources': [{'url': 'https://operator.test/live.m3u8'}],
            'directory_urls': ['https://worldcam.eu/view/', 'https://worldcam.eu/other/']}


@pytest.mark.parametrize('hour,expected', [(6, 'sunrise'), (12, 'daylight'), (18, 'sunset'), (0, 'night')])
def test_equatorial_solar_conditions(hour, expected):
    now = datetime(2026, 3, 20, hour, tzinfo=timezone.utc)
    assert expected in current.conditions(camera(), now)


def test_longitude_changes_current_daylight():
    now = datetime(2026, 3, 20, 12, tzinfo=timezone.utc)
    assert 'daylight' in current.conditions(camera(longitude=0), now)
    assert 'night' in current.conditions(camera(longitude=180), now)


@pytest.mark.parametrize('latitude', [89, -89, 90, -90])
def test_polar_day_and_night_do_not_require_sunrise_events(latitude):
    now = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    assert ('daylight' if latitude > 0 else 'night') in current.conditions(camera(latitude=latitude), now)


@pytest.mark.parametrize('latitude,longitude', [(None, 0), (91, 0), (0, 181), ('nan', 0), (True, 0), ('inf', 0)])
def test_unknown_or_invalid_positions_are_not_guessed(latitude, longitude):
    assert current.conditions(camera(latitude=latitude, longitude=longitude)) == ('unlocated',)


def test_naive_time_is_rejected():
    with pytest.raises(ValueError):
        current.conditions(camera(), datetime(2026, 3, 20))


def test_duplicate_topic_links_never_inflate_statistics_or_solar_lists():
    item = camera()
    stats = current.statistics([item, item])
    assert stats['cameras'] == stats['sources'] == stats['positioned'] == 1
    assert stats['topics']['mountains'] == stats['topics']['rockies'] == 1
    assert stats['directories']['worldcam.eu'] == 1
    grouped = current.group_channels([item, item], datetime(2026, 3, 20, 6, tzinfo=timezone.utc))
    assert len(grouped['sunrise']) == 1
    assert len(grouped['golden_hour']) == 1


def test_topics_are_nonexclusive_and_snow_is_not_a_current_storm():
    topics = webcam_topics.classify('Canmore Rocky Mountains ski resort in winter')
    assert {'rockies', 'mountains', 'mountain_landscape', 'ski', 'snow_landscape', 'sports_venues'} <= set(topics)
    assert 'storm' not in topics


@pytest.mark.parametrize('name,topic', [('Sahara desert', 'desert'), ('Autobahn A8', 'roads'),
                                     ('Football stadium', 'sports_venues'), ('Forest view', 'forest')])
def test_additional_requested_topics(name, topic):
    assert topic in webcam_topics.classify(name)


def test_partial_words_do_not_create_false_topics():
    assert 'ski' not in webcam_topics.classify('Skyline at dusk')
    assert 'lake' not in webcam_topics.classify('Seaside promenade')


@pytest.mark.parametrize('text', [
    '<script type="application/ld+json">{"@type":"VideoObject","contentLocation":{"geo":{"@type":"GeoCoordinates","latitude":51,"longitude":-2}}}</script>',
    '<meta itemprop="latitude" content="51"><meta itemprop="longitude" content="-2">',
    '<meta name="geo.position" content="51;-2">',
    '{"coordinates":[-2,51]}',
])
def test_coordinates_use_provider_metadata_and_correct_axis_order(text):
    assert webcam_geography.coordinates_from_page(text) == {'latitude': 51, 'longitude': -2}


def test_coordinates_do_not_use_a_recommended_camera_or_guess_from_city():
    text = '<script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"geo":{"@type":"GeoCoordinates","latitude":10,"longitude":20}}]}</script>'
    assert webcam_geography.coordinates_from_page(text) == {}
    assert webcam_geography.coordinates_from_page('<h1>New York webcam</h1>') == {}


def test_world_now_menu_counts_link_to_matching_groups(monkeypatch):
    from resources.lib.livestreams import route
    from resources.lib.handler.ParameterHandler import ParameterHandler
    groups = {key: [] for key, _label in current.GROUPS}
    groups['sunrise'] = [camera()]
    monkeypatch.setattr(current, 'group_channels', lambda *args: groups)
    monkeypatch.setattr(route.catalog, 'channels_by_section', lambda section: [camera()])
    entries = []
    monkeypatch.setattr(route, '_folder', lambda title, level, params, thumb: entries.append((title, level, params)))
    params = ParameterHandler()
    params.setParam('section', 'webcam')
    route._world_now(params)
    sunrise = next(entry for entry in entries if entry[2].get('solar') == 'sunrise')
    assert '(1)' in sunrise[0]
    params.setParam('solar', 'sunrise')
    assert route._filtered_channels(params) == [camera()]


def test_stats_themes_and_catalogue_count_are_clickable_without_double_counting(monkeypatch):
    from resources.lib.livestreams import route
    from resources.lib.handler.ParameterHandler import ParameterHandler
    monkeypatch.setattr(route.catalog, 'load_all', lambda: [camera(), camera()])
    monkeypatch.setattr(route.catalog, 'visible_channels', lambda: [camera()])
    info, entries = [], []
    monkeypatch.setattr(route, '_info_item', lambda gui, title: info.append(title))
    monkeypatch.setattr(route, '_folder', lambda title, level, params, thumb: entries.append(params))
    route._webcam_stats(ParameterHandler())
    assert info[0].endswith(': 1')
    assert {'mountains', 'rockies'} <= {entry['genre'] for entry in entries}


def test_weather_station_has_documented_coordinates_and_snow_landscape():
    from resources.lib.livestreams import catalog
    station = catalog.get_channel('baka:webcam:at:sonnblick-observatorium')
    assert current.coordinates(station) == (47.053979, 12.957484)
    assert station['coordinate_evidence_url'].endswith('/webcam/sonnblick/')
    assert station in catalog.channels_by_section('weather')
    assert 'snow_landscape' in station['genre']


def test_solar_library_does_not_require_zoneinfo_for_utc():
    import subprocess
    import sys
    script = """
import sys
sys.modules['zoneinfo'] = None
sys.modules['backports'] = None
from datetime import datetime, timezone
from resources.lib.vendor.astral import Observer
from resources.lib.vendor.astral.sun import elevation
assert elevation(Observer(0, 0), datetime(2026, 3, 20, 12, tzinfo=timezone.utc)) > 80
"""
    result = subprocess.run([sys.executable, '-c', script], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr