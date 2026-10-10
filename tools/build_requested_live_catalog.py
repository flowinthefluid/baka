#!/usr/bin/env python3
"""User-selected DACH 1080i channels and German/English sports, without multicast."""

import concurrent.futures
import hashlib
import ipaddress
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_tv_catalog import _fetch, to_channel
from resources.lib.livestreams.sports import classify


def entries(channels, feeds, streams, logos):
    meta = {c['id']: c for c in channels}
    feed_map = {(f['channel'], f['id']): f for f in feeds}
    main = {f['channel']: f for f in feeds if f.get('is_main')}
    hd_channels = {f['channel'] for f in feeds if f.get('format') == '1080i'}
    images = {logo['channel']: logo['url'] for logo in logos if logo.get('in_use')}
    for stream in streams:
        channel = meta.get(stream.get('channel'))
        if not channel:
            continue
        feed = feed_map.get((channel['id'], stream.get('feed')))
        if feed is None and not stream.get('feed'):
            feed = main.get(channel['id'], {})
        feed = feed or {}
        languages = [code for raw, code in (('deu', 'de'), ('eng', 'en'))
                     if raw in feed.get('languages', [])]
        is_sport = 'sports' in channel.get('categories', []) and bool(languages)
        is_tv = channel['country'] in ('DE', 'AT', 'CH') and channel['id'] in hd_channels
        if not is_sport and not is_tv:
            continue
        url = stream['url']
        host = urlparse(url).hostname
        if urlparse(url).scheme not in ('https', 'http') or not host:
            continue
        try:
            if not ipaddress.ip_address(host).is_global:
                continue
        except ValueError:
            pass
        country = channel['country'].lower().replace('uk', 'gb')
        quality = stream.get('quality') or ''
        # Feed language, not broadcaster country, decides sports eligibility.
        labels = ' '.join('[%s]' % label for label in stream.get('labels', []))
        yield {'country': country, 'label': channel['name'] + (' (%s)' % quality if quality else '') + ' ' + labels,
               'url': url, 'group': ';'.join(channel.get('categories', [])),
               'epg_id': channel['id'] + ('@' + stream['feed'] if stream.get('feed') else ''),
               'logo': images.get(channel['id'], ''), 'languages': languages,
               'nsfw': channel.get('is_nsfw') is not False,
               'channel_id': channel['id'], 'name': channel['name'],
               'section': 'sports' if is_sport else 'tv',
               'headers': {key: stream[field] for key, field in
                           (('User-Agent', 'user_agent'), ('Referer', 'referrer')) if stream.get(field)}}


def verify(entry):
    status, raw = _fetch(entry['url'], timeout=8, headers=entry['headers'])
    text = raw.decode('utf-8', 'replace')
    return status == 200 and ('#EXTM3U' in text[:2048] or '<MPD' in text[:4096])


def build(candidates, check=verify, workers=32):
    result = {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for entry, good in zip(candidates, pool.map(check, candidates)):
            if not good:
                continue
            channel = to_channel(entry, 'ok', date.today().isoformat())
            channel.update(name=entry['name'], section=entry['section'], language=entry['languages'],
                           nsfw=entry['nsfw'], publisher='iptv-org:' + entry['channel_id'])
            language_key = '-'.join(entry['languages']) if entry['section'] == 'sports' else ''
            channel['id'] = 'gxs:%s:%s:iptv-org-%s%s' % (
                entry['section'], entry['country'], entry['channel_id'].lower(),
                '-' + language_key if language_key else '')
            if entry['section'] == 'sports':
                channel['sport'] = classify(entry['name'])
            source = channel['sources'][0]
            source.update(source_id='iptv-org-' + hashlib.sha256(entry['url'].encode()).hexdigest()[:16],
                          official=False, rights_evidence_url='https://github.com/iptv-org/iptv#legal',
                          verification_method='http_manifest_only', language=entry['languages'])
            target = result.setdefault(channel['id'], dict(channel, sources=[]))
            if source['url'] not in {s['url'] for s in target['sources']}:
                target['sources'].append(source)
    return sorted(result.values(), key=lambda c: (c['country'], c['name'].lower()))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT / '.cache/iptv-org')
    args = parser.parse_args()
    data = {key: json.loads((args.input_dir / (key + '.json')).read_bytes())
            for key in ('channels', 'feeds', 'streams', 'logos')}
    selected = list(entries(**data))
    print('Checking %d candidate URLs' % len(selected), flush=True)
    channels = build(selected)
    for section, filename in (('tv', 'tv_iptv_org_1080i.json'), ('sports', 'sports_iptv_org_de_en.json')):
        subset = [c for c in channels if c['section'] == section]
        path = ROOT / 'resources/livestreams/sources' / filename
        payload = {'version': 1, 'retrieved_at': date.today().isoformat(),
                   'source_url': 'https://iptv-org.github.io/?q=format%3A1080i' if section == 'tv'
                   else 'https://iptv-org.github.io/?q=category%3Asports',
                   'note': 'User-selected Internet streams only; no MagentaTV multicast. '
                           'HTTP manifests verified; Kodi playback and geoblocking not verified.',
                   'channels': subset}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(section, len(subset), 'channels,', sum(len(c['sources']) for c in subset), 'variants', flush=True)


if __name__ == '__main__':
    main()
