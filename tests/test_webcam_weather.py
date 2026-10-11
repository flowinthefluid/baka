"""Weather lists never infer live storms from labels or stale data."""
import pytest
from resources.lib.livestreams import webcam_weather as weather


@pytest.mark.parametrize('code,gust,expected', [(95, 0, 'storm'), (0, 80, 'storm'), (75, 0, 'snowfall'),
                                             (61, 0, 'rain'), (45, 0, 'fog'), (0, 0, 'clear'),
                                             (2, 0, 'cloudy'), (3, 0, 'cloudy')])
def test_wmo_codes_and_kmh_gusts(code, gust, expected):
    assert expected in weather.conditions({'time': 10000, 'weather_code': code, 'wind_gusts_10m': gust}, now=10000)


@pytest.mark.parametrize('observation', [None, {}, {'time': 0, 'weather_code': 95},
                                      {'time': 20000, 'weather_code': 95}, {'time': 10000, 'weather_code': 'bad'}])
def test_stale_or_missing_data_is_unknown(observation):
    assert weather.conditions(observation, now=10000) == ('unknown',)


def test_weather_batches_duplicate_locations_and_never_geocodes_names(monkeypatch):
    monkeypatch.setattr(weather.weather, '_cache_get', lambda key: None)
    monkeypatch.setattr(weather.weather, '_cache_set', lambda *args: None)
    cameras = [{'id': 'one', 'coordinates': {'latitude': 47, 'longitude': 12}},
               {'id': 'two', 'coordinates': {'latitude': 47, 'longitude': 12}},
               {'id': 'three', 'name': 'Storm mountain', 'coordinates': {}}]
    calls = []
    def fetch(url):
        calls.append(url)
        return {'current': {'time': 10000, 'weather_code': 95}}
    groups = weather.group_channels(cameras, fetch=fetch, now=10000)
    assert len(calls) == 1
    assert len(groups['storm']) == 2
    assert [item['id'] for item in groups['unknown']] == ['three']


def test_network_failure_and_cancellation_leave_cameras_unknown(monkeypatch):
    monkeypatch.setattr(weather.weather, '_cache_get', lambda key: None)
    camera = {'id': 'one', 'coordinates': {'latitude': 47, 'longitude': 12}}
    def fetch(url):
        raise OSError('Offline')
    assert weather.group_channels([camera], fetch=fetch)['unknown'] == [camera]
    assert weather.group_channels([camera], fetch=lambda url: pytest.fail('Cancelled'), cancelled=lambda: True)['unknown'] == [camera]


@pytest.mark.parametrize('has_station', [False, True])
def test_weather_menu_opens_world_weather_instead_of_station_only(monkeypatch, has_station):
    from resources.lib.handler.ParameterHandler import ParameterHandler
    from resources.lib.livestreams import route
    camera = {'id': 'camera', 'country': 'ca', 'coordinates': {'latitude': 51, 'longitude': -115}}
    station = {'id': 'station', 'country': 'at'}
    monkeypatch.setattr(weather.weather, 'city_lines', lambda: [])
    monkeypatch.setattr(route.catalog, 'channels_by_section',
                        lambda section: [camera] if section == 'webcam' else ([station] if has_station else []))
    entries = []
    monkeypatch.setattr(route, '_folder', lambda title, level, params, *args: entries.append((level, params)))
    monkeypatch.setattr(route, '_empty_state', lambda gui: pytest.fail('World weather is available'))
    route.weather(ParameterHandler())
    assert ('weather_world', {'section': 'webcam'}) in entries
    assert ('continents', {'section': 'webcam'}) in entries
    assert ('continents', {'section': 'weather'}) not in entries
    assert not any(level == 'weather_kinds' for level, params in entries)
    if has_station:
        assert ('channels', {'section': 'weather'}) in entries