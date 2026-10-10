#!/usr/bin/env python3
"""Build the user-requested unencrypted MagentaTV multicast catalogue.

These addresses require a compatible MagentaTV multicast connection.
The catalogue is a local snapshot; menus never fetch the upstream database.
"""

import argparse
import ipaddress
import json
from datetime import date
from pathlib import Path
from urllib.request import urlopen


SOURCE = 'https://db.iptv.blog/multicastadressliste'
ROOT = Path(__file__).resolve().parents[1]


def build_channels(data, nitro_only=False, enabled=False):
    channels = {}
    for entry in data['channellist']:
        name = str(entry['channel_name']).strip()
        if nitro_only and name != 'NITRO':
            continue
        group = ipaddress.ip_address(entry['media_multicast_ip'])
        origin = ipaddress.ip_address(entry['media_multicast_sourceip'])
        port = int(entry['media_multicast_port'])
        if group.version != 4 or not group.is_multicast or origin.is_multicast or not 1 <= port <= 65535:
            raise ValueError('Invalid multicast address for ' + name)
        position = int(entry['channel_pos'])
        if position not in channels:
            epg = entry.get('epg_channels') or {}
            channels[position] = {
                'id': 'gxs:tv:de:magentatv-%d' % position,
                'name': name + ' (MagentaTV)', 'section': 'tv', 'country': 'de',
                'language': ['de'], 'genre': ['sports', 'series', 'movies'] if name == 'NITRO' else [],
                'nsfw': False, 'publisher': 'MagentaTV Multicast',
                'canonical_url': SOURCE + '#channel-%d' % position,
                'logo': entry.get('channel_logo_inverted') or entry.get('channel_logo') or '',
                'epg_id': epg.get('rytecDE_Basic') or epg.get('xmltvse') or '',
                'sources': [],
            }
        quality = str(entry['media_definition']).lower()
        if quality not in ('sd', 'hd', 'uhd'):
            quality = 'unknown'
        channels[position]['sources'].append({
            'source_id': 'magentatv-%s' % entry['id'],
            'display_name': 'MagentaTV Multicast ' + quality.upper(),
            # The upstream FFmpeg playlist uses UDP + source-specific membership.
            'url': 'udp://@%s:%d?sources=%s' % (group, port, origin),
            'protocol': 'udp', 'quality': quality, 'official': True,
            'rights_evidence_url': SOURCE, 'login_required': False, 'drm': False,
            'network_required': 'magentatv', 'active': enabled,
            'last_verified_at': date.today().isoformat(),
            'verification_method': 'upstream_catalogue_only',
        })
    if nitro_only and not channels:
        raise ValueError('NITRO is missing from the source catalogue')
    # NITRO first so the requested quick-start entry is easy to find.
    return sorted(channels.values(), key=lambda channel: (
        channel['name'] != 'NITRO (MagentaTV)', channel['name'].casefold()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Use a saved upstream JSON snapshot')
    parser.add_argument('--nitro-only', action='store_true')
    parser.add_argument('--enable', action='store_true',
                        help='Enable only with a compatible MagentaTV multicast connection')
    parser.add_argument('--out', type=Path,
                        default=ROOT / 'resources/livestreams/sources/tv_magenta_multicast.json')
    args = parser.parse_args()
    if args.input:
        data = json.loads(args.input.read_text(encoding='utf-8'))
    else:
        with urlopen(SOURCE + '.json', timeout=20) as response:
            data = json.load(response)
    channels = build_channels(data, args.nitro_only, args.enable)
    result = {'version': 1, 'source_url': SOURCE, 'retrieved_at': date.today().isoformat(),
              'note': 'Requires a compatible MagentaTV multicast connection and router. '
                      'Addresses checked against the upstream catalogue; playback not verified.',
              'channels': channels}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('%d channels, %d stream variants -> %s' % (
        len(channels), sum(len(channel['sources']) for channel in channels), args.out))


if __name__ == '__main__':
    main()
