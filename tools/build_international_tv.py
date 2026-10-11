#!/usr/bin/env python3
"""Import requested countries and Europe: one TV channel, HD first, no sports.

Input is a fresh iptv-org API snapshot. HLS sources must yield a media
playlist and a current media segment; DASH manifests are kept as separate
manifest-only evidence. Country/feed metadata never proves stream quality.
"""
import argparse
import concurrent.futures
from datetime import date
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.build_tv_catalog import allowed, to_channel, USER_AGENT, RACING_NAMES

REQUESTED = {'JP', 'CN', 'RU', 'UA', 'US', 'UK', 'FR', 'MX', 'CA'}
EUROPE_TERRITORIES = {'AX', 'FO', 'GI', 'GG', 'IM', 'JE', 'XK'}
SPORT_NAMES = re.compile(
    r'\bsports?\b|\bsport\d|\bfootball\b|\bsoccer\b|\btennis\b|\bgolf\b|'
    r'\bespn\b|\bdazn\b|\bbein\b|\beurosport\b|\bufc\b|\bwwe\b|\bfight\w*\b|'
    r'\bfutbol\b|\bfutebol\b|\bfutball\b|\bdeportes?\b|\bспорт\w*|体育|體育', re.I)
LANGUAGES = dict(zip(
    'eng deu fra spa ita por nld rus ukr jpn zho pol swe nor dan fin isl ell tur '
    'ron hun ces slk slv hrv srp bos bul mkd sqi est lav lit bel kat hye aze kaz '
    'heb ara hin kor'.split(),
    'en de fr es it pt nl ru uk ja zh pl sv no da fi is el tr ro hu cs sk sl hr sr '
    'bs bg mk sq et lv lt be ka hy az kk he ar hi ko'.split()))


def selected_countries(regions):
    europe = next(region['countries'] for region in regions if region['code'] == 'EUR')
    return REQUESTED | set(europe) | EUROPE_TERRITORIES


def entries(channels, feeds, streams, logos, regions, countries):
    selected = selected_countries(regions)
    meta = {c['id']: c for c in channels}
    feed_map = {(f['channel'], f['id']): f for f in feeds}
    main = {f['channel']: f for f in feeds if f.get('is_main')}
    fallback_languages = {c['code']: c.get('languages', []) for c in countries}
    images = {logo['channel']: logo['url'] for logo in logos if logo.get('in_use')}
    for stream in streams:
        channel = meta.get(stream.get('channel'))
        if not channel or channel['country'] not in selected:
            continue
        categories = channel.get('categories', [])
        if ('sports' in categories or channel.get('closed') or channel.get('replaced_by')
                or SPORT_NAMES.search(channel['name']) or RACING_NAMES.search(channel['name'])):
            continue
        url = stream['url']
        parts = urlsplit(url)
        if not parts.hostname or parts.username or parts.password:
            continue
        try:
            if not ipaddress.ip_address(parts.hostname).is_global:
                continue
        except ValueError:
            pass
        feed = feed_map.get((channel['id'], stream.get('feed'))) or main.get(channel['id'], {})
        codes = feed.get('languages') or fallback_languages.get(channel['country'], [])
        labels = ' '.join('[%s]' % label for label in stream.get('labels', []))
        quality = stream.get('quality') or ''
        entry = {
            'country': channel['country'].lower().replace('uk', 'gb'),
            'name': channel['name'], 'channel_id': channel['id'],
            'label': channel['name'] + (' (%s)' % quality if quality else '') + ' ' + labels,
            'url': url, 'group': ';'.join(categories), 'logo': images.get(channel['id'], ''),
            'epg_id': channel['id'], 'feed_name': feed.get('name', ''),
            'languages': [LANGUAGES.get(code, code) for code in codes],
            'nsfw': channel.get('is_nsfw') is not False,
            'headers': {key:stream[field] for key, field in
                (('User-Agent','user_agent'),('Referer','referrer')) if stream.get(field)},
        }
        if allowed(entry):
            yield entry


def download(url, headers, limit=131072, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent':USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(limit), response.geturl()
    except Exception:
        return 0, b'', url


def variants(text, base):
    lines = text.splitlines()
    result = []
    for index, line in enumerate(lines):
        if line.startswith('#EXT-X-STREAM-INF:'):
            match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
            height = int(match.group(2)) if match else 0
            bandwidth = re.search(r'(?:^|,)BANDWIDTH=(\d+)', line.partition(':')[2])
            for target in lines[index+1:]:
                if target.strip() and not target.startswith('#'):
                    result.append((height, int(bandwidth.group(1)) if bandwidth else 0,
                                   urljoin(base, target.strip())))
                    break
    return sorted(result, reverse=True)


def verify(entry, fetch=download):
    status, raw, base = fetch(entry['url'], entry['headers'])
    text = raw.decode('utf-8', 'replace')
    if status != 200:
        return None
    if '<MPD' in text[:4096]:
        # DRM-protected DASH is outside the live-TV playback capabilities.
        if 'ContentProtection' in text:
            return None
        return {'url':entry['url'], 'height':0, 'method':'http_manifest_only'}
    if '#EXTM3U' not in text[:2048]:
        return None
    options = variants(text, base)
    media = [(height, url) for height, _, url in options] or [(0, base)]
    for height, url in media:
        if options:
            state, body, media_base = fetch(url, entry['headers'])
            playlist = body.decode('utf-8', 'replace')
        else:
            state, playlist, media_base = status, text, base
        if state != 200 or '#EXTM3U' not in playlist[:2048]:
            continue
        if re.search(r'#EXT-X-KEY:.*(?:METHOD=SAMPLE-AES|KEYFORMAT=)', playlist):
            continue
        segments = [line.strip() for line in playlist.splitlines() if line.strip() and not line.startswith('#')]
        if not segments or '#EXTINF:' not in playlist:
            continue
        # A recent complete segment avoids mistaking a playlist-only response
        # or a geo/auth error on its media URLs for a usable stream.
        segment = segments[-2] if len(segments) > 1 else segments[-1]
        state, body, _ = fetch(urljoin(media_base, segment), {**entry['headers'], 'Range':'bytes=0-4095'}, limit=4096)
        if state not in (200, 206) or not body or b'<html' in body[:512].lower():
            continue
        if '#EXT-X-KEY:' in playlist:
            key = re.search(r'#EXT-X-KEY:[^\n]*URI="([^"]+)"', playlist)
            if key:
                key_state, key_body, _ = fetch(urljoin(media_base, key.group(1)), entry['headers'], limit=32)
                if key_state != 200 or len(key_body) != 16:
                    continue
        # Keep the master for adaptive playback if its best variant works.
        # Otherwise use the checked lower-quality variant, not a broken HD master.
        good_url = entry['url'] if not options or url == options[0][2] else url
        return {'url':good_url, 'height':height, 'method':'http_media_segment'}
    return None


def build(candidates, existing, check=verify, workers=48):
    known_urls = {s['url'] for c in existing for s in c.get('sources', [])}
    candidates = list({e['url']:e for e in candidates if e['url'] not in known_urls}.values())
    previous = {c['epg_id'].partition('@')[0]:c for c in existing if c.get('epg_id') and c['section']=='tv'}
    result = {}
    report = {'candidates':len(candidates), 'checked':0, 'accepted_sources':0, 'countries':{}}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        pending = {pool.submit(check, e):e for e in candidates}
        for future in concurrent.futures.as_completed(pending):
            entry = pending[future]
            good = future.result()
            report['checked'] += 1
            if report['checked'] % 200 == 0:
                print('Checked %d/%d; accepted %d' % (report['checked'],len(candidates),report['accepted_sources']),flush=True)
            if not good:
                continue
            candidate = dict(entry, url=good['url'])
            channel = to_channel(candidate, 'ok', date.today().isoformat())
            if channel['section'] != 'tv':
                continue
            channel.update(name=entry['name'], section='tv', language=entry['languages'], nsfw=entry['nsfw'],
                publisher='iptv-org:'+entry['channel_id'],
                id='gxs:tv:%s:iptv-org-%s' % (entry['country'],entry['channel_id'].lower()))
            old = previous.get(entry['channel_id'])
            if old:
                channel.update(name=old['name'], publisher=old['publisher'])
            source = channel['sources'][0]
            height = good.get('height',0)
            source.update(source_id='iptv-org-'+hashlib.sha256(good['url'].encode()).hexdigest()[:16],
                protocol='dash' if good['method']=='http_manifest_only' else 'hls',
                official=False, language=entry['languages'], display_name=entry['feed_name'],
                rights_evidence_url='https://github.com/iptv-org/iptv#legal',
                catalogue_url='https://iptv-org.github.io/', verification_method=good['method'])
            if height:
                source['quality'] = 'uhd' if height >= 2160 else 'hd' if height >= 720 else 'sd'
                source['verified_height'] = height
            target = result.setdefault(channel['id'],dict(channel,sources=[]))
            if source['url'] not in {s['url'] for s in target['sources']}:
                target['sources'].append(source)
                report['accepted_sources'] += 1
    channels = sorted(result.values(),key=lambda c:(c['country'],c['name'].casefold(),c['id']))
    for channel in channels:
        channel['language'] = sorted({code for source in channel['sources'] for code in source['language']})
        channel['sources'].sort(key=lambda s:({'uhd':0,'hd':1,'sd':2,'unknown':3}[s['quality']],s['source_id']))
        report['countries'][channel['country']] = report['countries'].get(channel['country'],0)+1
    return channels, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'resources/livestreams/sources/tv_international.json')
    parser.add_argument('--report',type=Path,default=ROOT/'dist/international-tv-checks.json')
    parser.add_argument('--workers',type=int,default=48)
    args = parser.parse_args()
    data = {key:json.loads((args.input_dir/(key+'.json')).read_bytes())
            for key in ('channels','feeds','streams','logos','regions','countries')}
    existing = []
    for path in (ROOT/'resources/livestreams/sources').glob('*.json'):
        if path.resolve() != args.out.resolve():
            existing.extend(json.loads(path.read_text(encoding='utf-8')).get('channels',[]))
    candidates = list(entries(**data))
    print('Requested-country non-sports candidate streams:',len(candidates),flush=True)
    channels, report = build(candidates,existing,workers=args.workers)
    report['selected_countries'] = sorted(c.lower().replace('uk','gb') for c in selected_countries(data['regions']))
    payload = {'version':1,'retrieved_at':date.today().isoformat(), 'source_url':'https://iptv-org.github.io/',
        'note':'Requested countries and Europe; no new sports. One entry per channel, HD preferred, SD fallback. '
               'Reachable HLS media segments checked. DASH manifest-only checks are separately marked. '
               'HTTP checks do not guarantee Kodi playback or continuing availability.', 'channels':channels}
    args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Imported %d TV channels, %d sources; %d country codes' %
        (len(channels),report['accepted_sources'],len(report['countries'])),flush=True)

if __name__=='__main__':
    main()
