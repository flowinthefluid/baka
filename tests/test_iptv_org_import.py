"""Broadcast format selection, blocked hosts and existing-channel merging."""

from tools.build_iptv_org_catalog import entries_for_format, build_channels


def entry(url='https://stream.broadcaster.test/live.m3u8', nsfw=False):
    return {'country': 'de', 'label': 'Example TV (720p)', 'url': url,
            'group': 'news', 'epg_id': 'Example.de', 'logo': '', 'headers': {}, 'nsfw': nsfw}


def test_format_selects_channel_feeds_without_promising_stream_quality():
    channels = [{'id': 'Example.de', 'name': 'Example TV', 'country': 'DE',
                 'categories': ['news'], 'is_nsfw': False}]
    feeds = [{'channel': 'Example.de', 'format': '1080i'}]
    streams = [{'channel': 'Example.de', 'quality': '720p', 'url': entry()['url'],
                'labels': [], 'user_agent': 'Custom Player', 'referrer': 'https://sender.test/'}]
    selected = list(entries_for_format(channels, feeds, streams, [], '1080i'))
    assert len(selected) == 1 and selected[0]['label'].strip() == 'Example TV (720p)'
    assert selected[0]['headers']['User-Agent'] == 'Custom Player'
    assert list(entries_for_format(channels, feeds, streams, [], '2160p')) == []


def test_existing_streams_are_skipped_and_new_variants_merge_with_feed_suffix():
    known = entry('https://stream.broadcaster.test/known.m3u8')
    existing = [{'id': 'gxs:tv:de:example', 'country': 'de', 'epg_id': 'Example.de@HD',
                 'name': 'Example TV', 'section': 'tv', 'publisher': 'example',
                 'sources': [{'url': known['url']}]}]
    checked = []
    def check(candidate):
        checked.append(candidate['url'])
        return True
    result = build_channels([known, entry(), entry()], existing, check=check)
    assert checked == [entry()['url']]
    assert len(result) == 1 and result[0]['id'] != existing[0]['id']
    assert (result[0]['publisher'], result[0]['name']) == ('example', 'Example TV')
    assert len(result[0]['sources']) == 1
    assert result[0]['sources'][0]['quality'] == 'hd'
    assert result[0]['sources'][0]['official'] is False
    assert result[0]['sources'][0]['rights_evidence_url'].endswith('#legal')


def test_import_preserves_adult_flag_and_rejects_unreachable_and_denied_sources():
    adult = entry(nsfw=True)
    dead = entry('https://stream.broadcaster.test/dead.m3u8')
    denied = entry('https://dash4.antik.sk/live/channel.m3u8')
    result = build_channels([adult, dead, denied], [], check=lambda e: e['url'] == adult['url'])
    assert len(result) == 1 and result[0]['nsfw'] is True
