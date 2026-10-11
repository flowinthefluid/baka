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