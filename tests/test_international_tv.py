"""Country scope, sports exclusion, real media checks and independent TV filters."""
import json
from pathlib import Path

import pytest

from conftest import set_setting
from resources.lib import contentgate, languages
from resources.lib.livestreams import selector, taxonomy, model, curation
from tools import build_international_tv as importer

ROOT = Path(__file__).resolve().parents[1]


def sample(name='Example', country='JP', categories=None):
    meta = {'id': 'Example.' + country, 'name': name, 'country': country,
            'categories': categories or ['news'], 'is_nsfw': False}
    feeds = [{'channel': meta['id'], 'id': 'main', 'name': 'Main HD',
              'is_main': True, 'languages': ['jpn']}]
    streams = [{'channel': meta['id'], 'feed': 'main',
                'url': 'https://fixture-stream.org/main.m3u8', 'quality': '1080p'}]
    return list(importer.entries([meta], feeds, streams, [],
                                [{'code': 'EUR', 'countries': ['FR', 'LT']}], []))


def test_requested_scope_and_europe():
    chosen = importer.selected_countries([{'code': 'EUR', 'countries': ['FR', 'LT']}])
    assert importer.REQUESTED | importer.EUROPE_TERRITORIES | {'LT'} <= chosen
    assert sample(country='UK')[0]['country'] == 'gb'
    assert sample(country='LT')
    assert not sample(country='AU')


@pytest.mark.parametrize('name,categories', [
    ('Ordinary name', ['sports']), ('ESPN 2', ['general']),
    ('Fox Deportes', ['general']), ('Матч Спорт', ['general']),
    ('CCTV 体育', ['general']), ('UFC TV', ['general']), ('Racing TV', ['general']),
])
def test_no_sports_even_when_upstream_category_missing(name, categories):
    assert not sample(name, categories=categories)


def test_variants_merge_into_one_sender_not_regional_labels():
    hd = sample()[0]
    sd = dict(hd, url='https://fixture-stream.org/sd.m3u8', feed_name='South SD',
              label='Example (480p)', languages=['en'])
    channels, report = importer.build([hd, sd], [], check=lambda e: {
        'url': e['url'], 'height': 1080 if e is hd else 480, 'method': 'http_media_segment'}, workers=1)
    assert report['accepted_sources'] == 2 and len(channels) == 1
    assert channels[0]['name'] == 'Example'
    assert channels[0]['epg_id'] == 'Example.JP'
    assert channels[0]['language'] == ['en', 'ja']
    assert [s['quality'] for s in channels[0]['sources']] == ['hd', 'sd']
    assert {s['display_name'] for s in channels[0]['sources']} == {'Main HD', 'South SD'}


def test_existing_stream_skipped_and_sender_identity_preserved():
    entry = sample()[0]
    old = {'epg_id': entry['channel_id'] + '@SD', 'section': 'tv',
           'name': 'Existing Example', 'publisher': 'original', 'sources': []}
    result, _ = importer.build([entry], [old], check=lambda e: {
        'url': e['url'], 'height': 720, 'method': 'http_media_segment'}, workers=1)
    assert result[0]['name'] == old['name'] and result[0]['publisher'] == 'original'
    old['sources'] = result[0]['sources']
    result, report = importer.build([entry], [old], check=lambda e: pytest.fail('duplicate checked'), workers=1)
    assert not result and report['checked'] == 0


@pytest.mark.parametrize('hd_ok', [True, False])
def test_hls_checks_media_segment_and_falls_back_to_sd(hd_ok):
    entry = sample()[0]
    entry['headers'] = {'Referer': 'https://fixture-stream.org/'}
    master = b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=1920x1080\nhd.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=300000,RESOLUTION=720x480\nsd.m3u8\n'
    calls = []

    def fetch(url, headers, **kwargs):
        calls.append(url)
        assert headers['Referer'] == entry['headers']['Referer']
        if url.endswith('main.m3u8'):
            return 200, master, url
        if url.endswith('.m3u8'):
            return 200, ('#EXTM3U\n#EXTINF:6,\n' + ('hd.ts' if url.endswith('hd.m3u8') else 'sd.ts')).encode(), url
        assert headers['Range'] == 'bytes=0-4095'
        return (206, b'G' * 4096, url) if hd_ok or url.endswith('sd.ts') else (403, b'', url)

    good = importer.verify(entry, fetch)
    assert good['height'] == (1080 if hd_ok else 480)
    assert good['url'] == (entry['url'] if hd_ok else 'https://fixture-stream.org/sd.m3u8')
    assert any(url.endswith('.ts') for url in calls)


@pytest.mark.parametrize('body', [b'<html>Error</html>', b'',
    b'#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI="key"\n#EXTINF:6,\npart.ts'])
def test_empty_html_or_drm_is_not_a_working_stream(body):
    assert importer.verify(sample()[0], lambda url, headers, **kw: (200, body, url)) is None


def test_tv_countries_independent_and_cache_tracks_both_choices(monkeypatch):
    set_setting('regionCountries', 'de,at,ch')
    channel = {'name': 'Example', 'section': 'tv', 'country': 'jp', 'nsfw': False}
    assert not contentgate.is_channel_visible(channel)
    before = contentgate.visibility_fingerprint()
    set_setting('lsTvUseRegionCountries', 'false')
    assert contentgate.is_channel_visible(channel)
    assert not languages.countryVisible('jp')
    assert contentgate.visibility_fingerprint() != before
    before = contentgate.visibility_fingerprint()
    set_setting('regionCountries', 'de')
    assert contentgate.visibility_fingerprint() != before
    set_setting('lsCountryMode', 'whitelist')
    set_setting('lsCountries', 'fr')
    assert not contentgate.is_channel_visible(channel)
    set_setting('lsCountries', 'jp')
    assert contentgate.is_channel_visible(channel)
    monkeypatch.setattr(languages, 'kodiLanguage', lambda: 'de')
    assert taxonomy.country_label('ua') == 'Ukraine'
    assert taxonomy.country_label('lt') == 'Litauen'


def test_tv_hd_preference_sd_failover_and_sports_order_unchanged(monkeypatch):
    channel = {'id': 'test', 'section': 'tv', 'sources': [
        {'source_id': 'sd', 'official': True, 'quality': 'sd'},
        {'source_id': 'hd', 'official': False, 'quality': 'hd'}]}
    monkeypatch.setattr(selector, '_load_state', lambda: {})
    assert selector.order_sources(channel)[0]['source_id'] == 'hd'
    channel['section'] = 'sports'
    assert selector.order_sources(channel)[0]['source_id'] == 'sd'
    channel['section'] = 'tv'
    monkeypatch.setattr(selector, '_load_state', lambda: {'test': {'hd': {'failed': selector.time.time()}}})
    assert selector.order_sources(channel)[0]['source_id'] == 'sd'


def test_bundled_international_catalog_no_sports_and_unique_broadcasters():
    data = json.loads((ROOT / 'resources/livestreams/sources/tv_international.json').read_text(encoding='utf-8'))
    channels = data['channels']
    assert len({c['id'] for c in channels}) == len(channels)
    assert {c['country'] for c in channels} >= {'jp', 'cn', 'ru', 'ua', 'us', 'gb', 'fr', 'mx', 'ca'}
    assert all(c['section'] == 'tv' and 'sports' not in c['genre'] for c in channels)
    normalized = [model.normalize_channel(c) for c in channels]
    assert all(normalized)
    merged = curation.collapse(normalized, rules=[])
    assert len({c['id'] for c in merged}) == len(merged)
    assert all(s.get('verification_method') in ('http_media_segment', 'http_manifest_only')
               for c in channels for s in c['sources'])
