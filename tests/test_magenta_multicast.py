"""MagentaTV addresses survive validation, source selection and playback."""

import json
from pathlib import Path

import pytest

from resources.lib.livestreams import catalog, model, m3u, route, selector
from tools.build_magenta_catalog import build_channels


@pytest.fixture
def nitro():
    path = Path(__file__).resolve().parents[1] / 'resources/livestreams/sources/tv_magenta_multicast.json'
    raw = next(channel for channel in json.loads(path.read_text(encoding='utf-8'))['channels']
               if channel['name'] == 'NITRO (MagentaTV)')
    # Protocol tests simulate an explicitly enabled compatible connection.
    for source in raw['sources']:
        source['active'] = True
    return model.normalize_channel(raw)


def test_nitro_multicast_source_is_visible_and_preserves_source_membership(nitro):
    assert nitro is not None
    source = catalog.approved_sources(nitro)[0]
    assert source['url'] == 'udp://@232.0.10.143:10000?sources=87.141.215.251'
    assert source['protocol'] == 'udp'
    assert source['quality'] == 'sd'
    assert source['network_required'] == 'magentatv'
    assert 'MagentaTV' in selector.describe(source)
    assert m3u._direct_url(nitro) == source['url']


@pytest.mark.parametrize('scheme', ['udp', 'rtp'])
def test_multicast_list_item_uses_kodi_mpegts_without_adaptive_inputstream(nitro, monkeypatch, scheme):
    source = dict(nitro['sources'][0], protocol=scheme)
    source['url'] = source['url'].replace('udp://', scheme + '://')
    mime = []
    lookup = []
    monkeypatch.setattr(route.xbmcgui.ListItem, 'setMimeType', lambda self, value: mime.append(value))
    monkeypatch.setattr(route.xbmcgui.ListItem, 'setContentLookup', lambda self, value: lookup.append(value))
    item = route._list_item_for(nitro, source)
    assert item.getPath() == source['url']
    assert mime == ['video/mp2t'] and lookup == [False]
    assert 'inputstream' not in item._props


@pytest.mark.parametrize('url, valid', [
    ('udp://@232.0.10.143:10000?sources=87.141.215.251', True),
    ('rtp://@232.0.10.143:10000?sources=87.141.215.251', True),
    ('udp://192.168.1.1:10000', False),
    ('udp://@232.0.10.143', False),
    ('rtp://@232.0.10.143:99999', False),
    ('udp://example.test:10000', False),
])
def test_multicast_urls_require_a_multicast_group_and_valid_port(url, valid):
    assert model.is_valid_stream_url(url) is valid
    if valid:
        assert model.normalize_source({'url': url})['protocol'] == url.split(':')[0]


def test_import_groups_hd_sd_variants_and_can_select_only_nitro():
    def entry(identifier, name, position, quality, group):
        return {'id': identifier, 'channel_name': name, 'channel_pos': position,
                'media_definition': quality, 'media_multicast_ip': group,
                'media_multicast_sourceip': '87.141.215.251', 'media_multicast_port': 10000}

    data = {'channellist': [entry(1, 'Das Erste', 1, 'HD', '232.0.20.35'),
                           entry(2, 'Das Erste', 1, 'SD', '232.0.10.35'),
                           entry(78, 'NITRO', 70, 'SD', '232.0.10.143')]}
    channels = build_channels(data)
    assert len(channels) == 2 and len(channels[1]['sources']) == 2
    assert channels[0]['name'] == 'NITRO (MagentaTV)'
    assert build_channels(data, nitro_only=True) == channels[:1]


def test_multicast_route_resolves_once_and_stops_after_success(nitro, monkeypatch):
    from resources.lib import player

    resolved = []
    failed = []
    monkeypatch.setattr(route, 'cGui', lambda: type('Gui', (), {'pluginHandle': 1})())
    monkeypatch.setattr(route.xbmcplugin, 'setResolvedUrl',
                        lambda handle, success, item: resolved.append((handle, success, item.getPath())))
    monkeypatch.setattr(player.cPlayer, 'startPlayer', lambda self: True)
    monkeypatch.setattr(selector, 'mark_ok', lambda *args: None)
    monkeypatch.setattr(selector, 'mark_failed', lambda *args: failed.append(args))
    assert route._play_channel(nitro) is True
    assert resolved == [(1, True, nitro['sources'][0]['url'])]
    assert failed == []
