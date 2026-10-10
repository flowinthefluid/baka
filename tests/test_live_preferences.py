"""Regional approval, broadcaster identity and filtered Live-TV navigation."""

import json
from pathlib import Path

from conftest import set_setting
from resources.lib import contentgate
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.livestreams import catalog, curation, model, route, selector, sports
from tools import build_requested_live_catalog as importer

ROOT = Path(__file__).resolve().parents[1]


def channel(cid, name, epg='', url=None, country='de', section='tv'):
    return model.normalize_channel({'id': cid, 'name': name, 'epg_id': epg,
        'country': country, 'section': section, 'language': ['de'], 'nsfw': False,
        'publisher': 'test', 'sources': [{'url': url or 'https://fixture-stream.org/' + cid,
                                       'official': True, 'source_id': cid}]})


def test_epg_and_url_bridges_merge_all_aliases_without_modifying_input(monkeypatch):
    a = channel('a', 'A', 'Sender.de@SD')
    b = channel('b', 'B', 'Other.de', url='https://fixture-stream.org/shared')
    bridge = channel('c', 'C', 'Sender.de@HD', url='https://fixture-stream.org/shared')
    later = channel('d', 'D', 'Other.de')
    result = curation.collapse([a, b, bridge, later], rules=[])
    assert len(result) == 1
    assert set(result[0]['alias_ids']) == {'a', 'b', 'c', 'd'}
    assert len(result[0]['sources']) == 3
    assert len(a['sources']) == 1 and a['name'] == 'A'
    monkeypatch.setattr(catalog, 'load_all', lambda: result)
    assert catalog.get_channel('c') is result[0]  # saved favourite survives


def test_approved_regions_have_bare_names_and_mdr_sachsen_anhalt_primary():
    raw = json.loads((ROOT / 'resources/livestreams/sources/tv_dach.json').read_text(encoding='utf-8'))
    result = curation.collapse([model.normalize_channel(c) for c in raw['channels']])
    for rule in curation.regional_rules():
        members = [c for c in result if c['id'] in rule['members']]
        assert len(members) == 1, rule['name']
        chosen = members[0]
        assert chosen['name'] == rule['name']
        assert chosen['id'] == rule['primary']
        assert rule['primary_label'] in selector.describe(selector.order_sources(chosen)[0])
        for source in chosen['sources']:
            if source['source_id'] not in {s['source_id'] for c in raw['channels']
                                          if c['id'] == rule['primary'] for s in c['sources']}:
                assert source['priority'] >= 1
        assert selector.order_sources(chosen)[0]['priority'] == 0
    assert next(c for c in result if c['name'] == 'MDR')['id'].endswith('sachsen-anhalt')


def test_zdf_neo_info_are_separate_but_quality_and_country_aliases_merge():
    raw = [channel('zdf', 'ZDF', 'ZDF.de@SD'), channel('hd', 'ZDF HD', 'ZDF.de@HD', country='at'),
           channel('neo', 'ZDFneo', 'ZDFneo.de'), channel('info', 'ZDFinfo', 'ZDFinfo.de')]
    result = curation.collapse(raw, rules=[])
    assert [c['name'] for c in result] == ['ZDF', 'ZDFneo', 'ZDFinfo']
    assert result[0]['countries'] == ['de', 'at']
    set_setting('regionCountries', 'at')
    assert contentgate.is_channel_visible(result[0])


def test_tv_has_dach_entry_and_no_nitro_pin(monkeypatch):
    rows = []
    monkeypatch.setattr(route, '_folder', lambda title, level, params, *args: rows.append((level, params)))
    monkeypatch.setattr(catalog, 'channels_by_section', lambda section: [channel('nitro', 'NITRO')])
    params = ParameterHandler()
    params.setParam('section', 'tv')
    route._section(params)
    assert [level for level, values in rows] == ['countries', 'genres']
    rows.clear()
    monkeypatch.setattr(catalog, 'countries_in_section', lambda section: ['de', 'at', 'ch', 'gb'])
    route._countries(params)
    assert [values['country'] for level, values in rows] == ['dach', 'gb']


def test_epg_link_first_and_exactly_same_filtered_channels(monkeypatch):
    rows = []

    class Gui:
        def addFolder(self, element, params, *args, **kwargs):
            rows.append(('epg_row', params.getValue('channel'), element.getTitle()))

        def setEndOfDirectory(self):
            pass

    channels = [channel('nitro', 'NITRO'), channel('orf', 'ORF', country='at'),
                channel('foreign', 'Outside', country='us')]
    monkeypatch.setattr(catalog, 'channels_by_section', lambda section: channels)
    monkeypatch.setattr(route, 'cGui', Gui)
    monkeypatch.setattr(route, '_folder', lambda title, level, params, *args: rows.append((level, params)))
    monkeypatch.setattr(route, '_channel_item', lambda gui, c: rows.append(('channel', c['id'])))
    monkeypatch.setattr(route, '_epg_line', lambda c: 'Sendung' if c['id'] == 'nitro' else '')
    params = ParameterHandler()
    params.addParams({'section': 'tv', 'country': 'dach'})
    route._channels_filtered(params)
    assert rows == [('epg', {'section': 'tv', 'country': 'dach'}), ('channel', 'nitro'), ('channel', 'orf')]
    rows.clear()
    route._show_epg(params)
    assert [row[1] for row in rows] == ['nitro', 'orf']
    assert 'Sendung' in rows[0][2] and 'Keine Programmdaten' in rows[1][2]


def test_epg_reads_alias_ids_when_primary_has_no_epg(monkeypatch):
    monkeypatch.setattr(route, '_guide_path', lambda: 'guide.xml')
    monkeypatch.setattr(route.epg, 'now_next_line', lambda path, cid: 'Programme' if cid == 'valid' else '')
    assert route._epg_line({'epg_id': '', 'epg_ids': ['', 'valid']}) == 'Programme'


def test_sports_import_uses_feed_language_not_country_and_rejects_multicast():
    channels = [{'id': cid, 'name': cid, 'country': country, 'categories': ['sports'], 'is_nsfw': False}
                for cid, country in [('IndianFootball.in', 'IN'), ('Spanish.us', 'US'), ('Mixed.uk', 'UK')]]
    feeds = [{'channel': cid, 'id': 'main', 'languages': [language], 'is_main': True}
             for cid, language in [('IndianFootball.in', 'eng'), ('Spanish.us', 'spa'), ('Mixed.uk', 'eng')]]
    streams = [{'channel': c['id'], 'feed': 'main', 'url': 'https://example.com/' + c['id']} for c in channels]
    streams += [{'channel': channels[0]['id'], 'feed': 'main', 'url': 'udp://239.35.10.4:10000'},
                {'channel': channels[0]['id'], 'feed': 'main', 'url': 'http://192.168.1.1/live.m3u8'}]
    entries = list(importer.entries(channels, feeds, streams, []))
    assert [e['channel_id'] for e in entries] == ['IndianFootball.in', 'Mixed.uk']
    assert entries[1]['country'] == 'gb'
    built = importer.build(entries, check=lambda e: True, workers=1)
    assert all(c['language'] == ['en'] and c['section'] == 'sports' for c in built)
    assert all(s['official'] is False for c in built for s in c['sources'])
    assert sports.classify('American Football NFL') == ['american_football']
    assert sports.classify('FIFA Football') == ['football']
    assert sports.classify('DAZN Darts') == ['darts']
    assert sports.classify('MLB Baseball') == ['baseball']
    assert sports.classify('SportMix TV') == ['other']
    assert sports.classify('World of Freesports') == ['other']
    assert sports.classify('ESports TV') == ['esports']
    assert sports.classify('TVS Bowling Network') == ['bowling']
    assert sports.classify('Lacrosse TV') == ['lacrosse']
    assert sports.classify('Strongman') == ['strength']


def test_only_dach_channels_from_1080i_filter_and_manifest_headers(monkeypatch):
    channels = [{'id': cid, 'name': cid, 'country': country, 'categories': ['news'], 'is_nsfw': False}
                for cid, country in [('DACH.de', 'DE'), ('French.fr', 'FR'), ('Low.at', 'AT')]]
    feeds = [{'channel': cid, 'id': 'SD', 'is_main': True, 'languages': ['deu'], 'format': quality}
             for cid, quality in [('DACH.de', '1080i'), ('French.fr', '1080i'), ('Low.at', '720p')]]
    streams = [{'channel': c['id'], 'feed': 'SD', 'url': 'https://example.com/' + c['id'],
                'quality': '576p', 'user_agent': 'Player/1', 'referrer': 'https://example.com/'} for c in channels]
    entries = list(importer.entries(channels, feeds, streams, []))
    assert len(entries) == 1 and entries[0]['channel_id'] == 'DACH.de'
    called = []
    monkeypatch.setattr(importer, '_fetch', lambda url, timeout, headers: (
        called.append(headers) or 200, b'#EXTM3U\n#EXTINF:4\nsegment.ts'))
    assert importer.verify(entries[0])
    assert called == [{'User-Agent': 'Player/1', 'Referer': 'https://example.com/'}]
