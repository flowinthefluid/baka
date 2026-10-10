#!/usr/bin/env python3
"""Import the user's iptv-org format search using the existing TV import rules.

The format filter selects broadcast feeds, not the resolution of stream URLs.
Only reachable manifests enter the bundle; Kodi playback is a separate check.
"""

import argparse
import concurrent.futures
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.build_tv_catalog import allowed, to_channel, _fetch

API = 'https://iptv-org.github.io/api/'


def entries_for_format(channels, feeds, streams, logos, selected_format):
    metadata = {channel['id']: channel for channel in channels}
    selected = {feed['channel'] for feed in feeds if feed.get('format') == selected_format}
    images = {logo['channel']: logo['url'] for logo in logos if logo.get('in_use')}
    for stream in streams:
        channel_id = stream.get('channel')
        if channel_id not in selected or channel_id not in metadata:
            continue
        channel = metadata[channel_id]
        labels = ' '.join('[%s]' % label for label in stream.get('labels', []))
        quality = stream.get('quality')
        headers = {key: stream[field] for key, field in
                   (('User-Agent', 'user_agent'), ('Referer', 'referrer')) if stream.get(field)}
        yield {
            'country': channel['country'].lower(),
            'label': '%s%s %s' % (channel['name'], ' (%s)' % quality if quality else '', labels),
            'url': stream['url'], 'group': ';'.join(channel.get('categories', [])),
            'logo': images.get(channel_id, ''), 'epg_id': channel_id, 'headers': headers,
            'nsfw': channel.get('is_nsfw') is not False,
        }


def reachable(entry):
    status, body = _fetch(entry['url'], timeout=8)
    text = body.decode('utf-8', 'replace')
    return status == 200 and ('#EXTM3U' in text[:2048] or '<MPD' in text[:4096])


def build_channels(entries, existing, check=reachable, workers=24):
    by_epg = {(channel['country'], channel['epg_id'].split('@')[0]): channel
              for channel in existing if channel.get('epg_id')}
    known_urls = {source['url'] for channel in existing for source in channel.get('sources', [])}
    candidates = []
    seen = set(known_urls)
    for entry in entries:
        if entry['url'] in seen or not allowed(entry):
            continue
        seen.add(entry['url'])
        candidates.append(entry)
    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for entry, ok in zip(candidates, pool.map(check, candidates)):
            if not ok:
                continue
            channel = to_channel(entry, 'ok', date.today().isoformat())
            channel['nsfw'] = entry['nsfw']
            previous = by_epg.get((entry['country'], entry['epg_id']))
            if previous:
                # Preserve the publisher+name identity used by catalog._merge;
                # bundled files themselves must still have unique channel IDs.
                for field in ('name', 'section', 'publisher'):
                    channel[field] = previous[field]
            else:
                # Same display name can belong to different channels/countries.
                channel['publisher'] = 'iptv-org:' + entry['epg_id']
            channel['id'] = 'gxs:%s:%s:iptv-org-%s' % (
                channel['section'], channel['country'], entry['epg_id'].lower())
            source = channel['sources'][0]
            source['source_id'] = 'iptv-org-' + hashlib.sha256(entry['url'].encode()).hexdigest()[:16]
            source['verification_method'] = 'http_manifest_only'
            # A user-edited directory is evidence of upstream publication, not
            # evidence that a destination is the broadcaster's own server.
            source['official'] = False
            source['rights_evidence_url'] = 'https://github.com/iptv-org/iptv#legal'
            source['catalogue_url'] = 'https://iptv-org.github.io/'
            target = result.setdefault(channel['id'], dict(channel, sources=[]))
            target['sources'].append(source)
    return sorted(result.values(), key=lambda channel: (channel['country'], channel['name'].casefold()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', default='1080i')
    parser.add_argument('--input-dir', type=Path)
    parser.add_argument('--workers', type=int, default=24)
    parser.add_argument('--out', type=Path,
                        default=ROOT / 'resources/livestreams/sources/tv_iptv_org_1080i.json')
    args = parser.parse_args()
    data = {}
    for name in ('channels', 'feeds', 'streams', 'logos'):
        if args.input_dir:
            data[name] = json.loads((args.input_dir / (name + '.json')).read_bytes())
        else:
            status, body = _fetch(API + name + '.json', limit=32 * 1024 * 1024, timeout=30)
            if status != 200:
                raise RuntimeError('Cannot load ' + name)
            data[name] = json.loads(body)
    existing = []
    for path in (ROOT / 'resources/livestreams/sources').glob('*.json'):
        if path.resolve() != args.out.resolve():
            existing.extend(json.loads(path.read_text(encoding='utf-8')).get('channels', []))
    channels = build_channels(entries_for_format(**data, selected_format=args.format), existing,
                              workers=args.workers)
    result = {'version': 1, 'source_url': 'https://iptv-org.github.io/?q=format%3A' + args.format,
              'retrieved_at': date.today().isoformat(),
              'note': 'Broadcast format filter, not guaranteed stream resolution. '
                      'Existing TV import rules; reachable HTTP manifests checked. '
                      'Kodi playback and geoblocking not verified.', 'channels': channels}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('%d channels, %d additional variants -> %s' % (
        len(channels), sum(len(channel['sources']) for channel in channels), args.out))


if __name__ == '__main__':
    # Support both `python -m tools.build_iptv_org_catalog` and direct execution.
    main()
