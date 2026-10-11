#!/usr/bin/env python3
"""Extract public webcam media from the five requested directories.

Cached, resumable build. Provider pages with expiring HLS addresses are kept as
resolver sources; their media is extracted again by Kodi at playback time.
Directories and still-image previews alone never become playable cameras.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import threading
import time
from urllib.parse import urljoin, urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resources.lib.livestreams import webcam_extract as extractor
from resources.lib.livestreams import webcam_geography, webcam_topics

DIRECTORIES = {'worldcam': 'https://worldcam.eu/',
               'skyline': 'https://www.skylinewebcams.com/',
               'panorama': 'https://www.panoramablick.com/',
               'earthcam': 'https://www.earthcam.com/',
               'liveworld': 'https://liveworldwebcams.com/'}
COUNTRIES = json.loads((ROOT / 'resources/data/film_countries.json').read_text(encoding='utf-8'))['countries']


def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


COUNTRY_LOOKUP = {slug(row[field]): row['code'].lower() for row in COUNTRIES for field in ('en', 'de')}
COUNTRY_LOOKUP.update({'united-states': 'us', 'usa': 'us', 'united-kingdom': 'gb',
                       'espana': 'es', 'italia': 'it', 'polska': 'pl', 'deutschland': 'de',
                       'osterreich': 'at', 'oesterreich': 'at', 'hrvatska': 'hr', 'czech-republic': 'cz',
                       'caribbean-netherlands': 'bq', 'zanzibar': 'tz', 'ivory-coast': 'ci',
                       'ellada': 'gr', 'brasil': 'br', 'us-virgin-islands': 'vi', 'norge': 'no',
                       'slovenija': 'si', 'sint-maarten': 'sx', 'bosnia-and-herzegovina': 'ba',
                       'repubblica-di-san-marino': 'sm', 'congo-drc': 'cd',
                       'democratic-republic-of-the-congo': 'cd', 'congo':'cd', 'bvi':'vg', 'british-virgin-islands':'vg',
                       'bonaire':'bq', 'curacao':'cw', 'turks-and-caicos':'tc', 'turks-and-caicos-islands':'tc',
                       'st-barts':'bl', 'st-barth':'bl', 'saint-barthelemy':'bl', 'jersey-island':'je',
                       'north-macedonia':'mk', 'jersey':'je', 'australian-capital-territory':'au'})
THEMES = {'mountains': ('mountain', 'berg', 'summit', 'alps', 'alpen', 'peak', 'dachstein'),
          'beach': ('beach', 'strand', 'playa', 'spiaggia', 'shore', 'maldives', 'seaside'),
          'pier': ('pier', 'harbor', 'harbour', 'hafen', 'marina', 'port of'),
          'city': ('city', 'downtown', 'square', 'piazza', 'street', 'plaza', 'skyline', 'town'),
          'ski': ('ski', 'snow', 'schnee', 'winter', 'gondola'),
          'animals': ('animal', 'wildlife', 'elephant', 'zoo', 'safari', 'aquarium'),
          'birds': ('eagle', 'stork', 'osprey', 'owl', 'bird', 'falcon'),
          'lake': ('lake', 'lago', 'loch', 'see ', 'lakes'),
          'river': ('river', 'rivers', 'fluss', 'rhein', 'danube'),
          'volcano': ('volcano', 'volcan', 'etna', 'vulkan'),
          'waterfall': ('waterfall', 'falls', 'wasserfall'),
          'landmark': ('cathedral', 'colosseum', 'temple', 'tower', 'unesco', 'castle'),
          'traffic': ('airport', 'railway', 'runway', 'railfan', 'highway'),
          'park': ('park', 'garden', 'forest', 'woods')}


def genres(title, body=''):
    return webcam_topics.classify(title, body)


def media_identity(media, page):
    """Only merge demonstrated shared players, never similar camera names."""
    if media.get('protocol') == 'plugin':
        return media['url']
    if media.get('protocol') == 'jpeg':
        match = re.match(r'(https://archive\.panoramablick\.com/archive/\d+)/', media.get('url', ''))
        if match:
            return match.group(1)
    return media.get('headers', {}).get('Referer') or page


class Fetcher:
    def __init__(self, cache):
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self.local = threading.local()
        self.panorama_lock = threading.Lock()
        self.panorama_last = 0
        self.skyline_lock = threading.Lock()
        self.skyline_last = 0

    def get(self, url):
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
        if path.exists():
            cached = json.loads(path.read_text(encoding='utf-8'))
            if '\ufffd' not in cached.get('text','') or urlsplit(url).hostname not in ('www.skylinewebcams.com','www.panoramablick.com'):
                return cached
        if not hasattr(self.local, 'session'):
            self.local.session = requests.Session()
        if urlsplit(url).hostname == 'www.panoramablick.com':
            with self.panorama_lock:
                delay = 10 - (time.monotonic() - self.panorama_last)
                if delay > 0:
                    time.sleep(delay)
                self.panorama_last = time.monotonic()
        if urlsplit(url).hostname == 'www.skylinewebcams.com':
            with self.skyline_lock:
                delay = 1 - (time.monotonic() - self.skyline_last)
                if delay > 0:
                    time.sleep(delay)
                self.skyline_last = time.monotonic()
        for attempt in range(3):
            try:
                value = extractor.fetch_document(url, self.local.session)
                if not value.get('media') and len(value['text']) <= 50:
                    raise ValueError('Empty provider response')
                break
            except Exception as exc:
                if attempt == 2 or getattr(getattr(exc,'response',None),'status_code',0) == 429:
                    raise
                time.sleep(2 + attempt * 2)
        path.write_text(json.dumps(value), encoding='utf-8')
        return value

    def page(self, url):
        value = self.get(url)
        return value['media'] if value.get('media') else (value['text'], value['url'])


def country_from_path(url):
    parts = [part for part in urlsplit(url).path.split('/') if part]
    for part in parts:
        if part in COUNTRY_LOOKUP:
            return COUNTRY_LOOKUP[part]
        if part.endswith('-usa'):
            return 'us'
    if parts and parts[0] == 'usa':
        return 'us'
    return 'int'


def camera_links(text, base, directory):
    result = {}
    for tag, attrs in extractor.Page(text).tags:
        if tag != 'a':
            continue
        url = urljoin(DIRECTORIES['skyline'] if directory == 'skyline' else base,
                      attrs.get('href', '')).split('#')[0]
        path = urlsplit(url).path
        if urlsplit(url).netloc != urlsplit(base).netloc:
            continue
        if directory == 'skyline' and re.match(r'/en/(?:webcam|webcam-from-web)/(?:[^/]+/){2,4}[^/]+\.html$', path):
            result[url] = attrs.get('title', '')
        if directory == 'worldcam' and re.search(r'/webcams/(?:[^/]+/){1,3}\d+-[^/]+$', path):
            result[url] = attrs.get('title', '')
        if directory == 'panorama' and path.startswith('/wetter-webcam/') and path.endswith('.html'):
            result[url] = attrs.get('title', '')
    if directory == 'skyline':
        for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text, re.S):
            url = urljoin(DIRECTORIES['skyline'], match.group(1))
            if url in result:
                alt = re.search(r'<img[^>]+alt="([^"]+)"', match.group(2))
                if alt:
                    result[url] = re.sub(r'^Webcam\s+', '', html.unescape(alt.group(1)))
    return result


def discover_skyline(fetch):
    root = fetch.get(DIRECTORIES['skyline'])
    countries = set()
    for tag, attrs in extractor.Page(root['text']).tags:
        href = attrs.get('href', '')
        if tag == 'a' and re.fullmatch(r'/en/webcam/[^/]+\.html', href):
            countries.add(urljoin(root['url'], href))
    result = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(fetch.get, url): url for url in sorted(countries)}
        for job in as_completed(jobs):
            try:
                page = job.result()
                result.update(camera_links(page['text'], page['url'], 'skyline'))
            except Exception as exc:
                print('Skyline index failed:', jobs[job], type(exc).__name__, flush=True)
    return [{'directory': 'skyline', 'url': url, 'country': country_from_path(url),
             'name': result[url], 'native_skyline': '/en/webcam/' in url and bool(result[url])}
            for url in sorted(result)]


def discover_liveworld(fetch):
    api = DIRECTORIES['liveworld'] + 'wp-json/wp/v2/'
    first = fetch.get(api + 'categories?per_page=100&_fields=id,name,slug,parent')
    cats = json.loads(first['text'])
    for page in range(2, first['pages'] + 1):
        cats += json.loads(fetch.get(api + f'categories?per_page=100&_fields=id,name,slug,parent&page={page}')['text'])
    cats = {row['id']: row for row in cats}
    fields = 'id,link,title,content,categories'
    first = fetch.get(api + f'posts?per_page=100&_fields={fields}')
    posts = json.loads(first['text'])
    for page in range(2, first['pages'] + 1):
        posts += json.loads(fetch.get(api + f'posts?per_page=100&_fields={fields}&page={page}')['text'])
    result = []
    for post in posts:
        title = extractor.clean(post['title']['rendered'])
        # The directory also publishes restored historical films; these are not webcams.
        if any(cats.get(c,{}).get('slug') == 'time-travel'
               or re.fullmatch(r'(?:18|19)\d{2}s', cats.get(c,{}).get('slug','')) for c in post['categories']):
            continue
        if re.search(r'\b(?:18|19)\d{2}s?\b', title) and not re.search(r'\bwebcam\b', title, re.I):
            continue
        country = next((COUNTRY_LOOKUP[cats[c]['slug']] for c in post['categories']
                        if c in cats and cats[c]['slug'] in COUNTRY_LOOKUP), 'int')
        result.append({'directory': 'liveworld', 'url': post['link'], 'country': country,
                       'name': title,
                       'body': extractor.clean(post['content']['rendered'])})
    return result


def discover_earthcam(fetch):
    data = json.loads(fetch.get('https://www.earthcam.com/api/ectv/player/playlist.php?r=playlist&a=fetch')['text'])['data']
    urls = {}
    for playlist in data.values():
        for item in playlist.get('playlist_items', []):
            # The fresh playlist carries rotating tokens. Persist its public page instead.
            url = item.get('url', '')
            if '.earthcam.com' in urlsplit(url).netloc and item.get('stream'):
                urls[url] = {'directory': 'earthcam', 'url': url, 'name': item.get('title', ''),
                             'city': item.get('city', ''), 'country': COUNTRY_LOOKUP.get(slug(item.get('country', '')), 'int')}
    root = fetch.get(DIRECTORIES['earthcam'])
    for tag, attrs in extractor.Page(root['text']).tags:
        url = urljoin(root['url'], attrs.get('href', ''))
        if tag == 'a' and 'cam=' in url and urlsplit(url).netloc == 'www.earthcam.com':
            urls.setdefault(url, {'directory': 'earthcam', 'url': url, 'country': country_from_path(url)})
    return list(urls.values())


def discover_worldcam(fetch, pages_per_country):
    roots = ['https://worldcam.eu/webcams/' + continent for continent in
             ('europe', 'north-america', 'south-america', 'africa', 'asia', 'australia-oceania', 'poles')]
    indices, cameras = set(roots), {}
    for root in roots:
        page = fetch.get(root)
        cameras.update(camera_links(page['text'], root, 'worldcam'))
        for tag, attrs in extractor.Page(page['text']).tags:
            url = urljoin(root, attrs.get('href', ''))
            if tag == 'a' and re.fullmatch(r'/webcams/[^/]+/[^/]+', urlsplit(url).path):
                indices.add(url)
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(fetch.get, url + (f'?page={page}' if page > 1 else ''))
                for url in sorted(indices) for page in range(1, pages_per_country + 1)]
        for job in as_completed(jobs):
            try:
                page = job.result()
                cameras.update(camera_links(page['text'], page['url'], 'worldcam'))
            except Exception:
                pass
    return [{'directory': 'worldcam', 'url': url, 'country': country_from_path(url)} for url in sorted(cameras)]


def discover_panorama(fetch):
    countries = set()
    root = fetch.get(DIRECTORIES['panorama'])
    for tag, attrs in extractor.Page(root['text']).tags:
        href = attrs.get('href', '')
        if tag == 'a' and href.startswith('/wetter-webcams/') and href.endswith('.html'):
            countries.add(urljoin(root['url'], href))
    # All continental listings, with the provider's 10-second crawl delay.
    countries.update('https://www.panoramablick.com/wetter-webcams/' + name + '.html'
                     for name in ('afrika', 'amerika', 'antarktis', 'asien', 'australien', 'karibik', 'neuseeland', 'ozeanien'))
    result = {}
    for url in sorted(countries):
        try:
            page = fetch.get(url)
            for match in re.finditer(r'<a[^>]+class="cam-item[^"\n]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page['text'], re.S):
                href, block = match.groups()
                camera = urljoin(url, href)
                image = re.search(r'<img[^>]+src="(https://archive\.panoramablick\.com/archive/\d+/\d{4}/[^" ]+\.jpg)', block)
                title = re.search(r'<div class="title">(.*?)</div>', block, re.S)
                if image and title and '/wetter-webcam/' in camera:
                    result[camera] = {'directory': 'panorama', 'url': camera,
                                      'country': country_from_path(url.replace('.html', '')),
                                      'name': extractor.clean(title.group(1)), 'current_image': image.group(1)}
        except Exception:
            pass
    return list(result.values())


def build_camera(record, fetch):
    if record.get('native_skyline'):
        # Native Skyline listings identify a known public HLS player. Its session
        # token must be extracted on play; bulk-fetching tokens serves no purpose.
        page = {'text': '<h1>' + html.escape(record['name']) + '</h1>', 'url': record['url']}
        media = {'protocol': 'hls'}
        cached = fetch.cache / (hashlib.sha256(record['url'].encode()).hexdigest() + '.json')
        if cached.exists():
            page = fetch.get(record['url'])
            resolved = extractor.resolve(page['url'], fetch=fetch.page)
            if resolved:
                media = resolved
                record = dict(record, native_skyline=False)
    elif record.get('current_image') and record.get('country') != 'int':
        # Country listings carry the same dated live frame as the main player,
        # not an og:image or a small preview. Resolve the current frame on play.
        page = {'text': '<h1>' + html.escape(record['name']) + '</h1>', 'url': record['url']}
        media = {'url': record['current_image'], 'protocol': 'jpeg'}
    else:
        page = fetch.get(record['url'])
        media = extractor.resolve(page['url'], fetch=fetch.page)
    text, final = page['text'], page['url']
    if not media:
        return None
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S | re.I)
    name = extractor.clean(h1.group(1)) if h1 else record.get('name', '')
    name = re.sub(r'(?:\s*[-|]\s*)?(?:Live cam|Live Webcam|Webcam)\s*$', '', name, flags=re.I).strip()
    name = re.sub(r'^Wetter\s*&\s*Webcam\s*', '', name, flags=re.I)
    if not name:
        return None
    country = record.get('country', 'int')
    if record['directory'] == 'panorama':
        country = {'hurghada.html':'eg','panamakanal.html':'pa'}.get(urlsplit(final).path.split('/')[-1],country)
    if country == 'int':
        country = next((COUNTRY_LOOKUP[slug(part)] for part in re.split(r'\s[-–|]\s', name)
                        if slug(part) in COUNTRY_LOOKUP), 'int')
    # Only camera breadcrumbs can identify a country; global navigation cannot.
    if country == 'int':
        breadcrumb = re.search(r'<div[^>]+class="breadcrumb[^"\n]*"[^>]*>(.*?)</div>', text, re.S)
        for tag, attrs in extractor.Page(breadcrumb.group(1) if breadcrumb else '').tags:
            href = attrs.get('href', '')
            if tag == 'a' and href.startswith('/wetter-webcams/'):
                guessed = country_from_path(href.replace('.html', ''))
                if guessed != 'int':
                    country = guessed
                    break
    if country == 'int' and record['directory'] == 'panorama':
        coordinates = re.search(r'"coordinates"\s*:\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]', text)
        if coordinates:
            from tools.webcam_locations import country_at
            country = country_at(*map(float, coordinates.groups()))
    city = record.get('city') or ''
    if not city and record['directory'] == 'skyline':
        parts = urlsplit(final).path.split('/')
        if len(parts) > 6:
            city = parts[-2].replace('-', ' ').title()
    if not city:
        city = re.split(r'\s[-–|]\s', name)[0]
        city = re.sub(r'\s+Webcam.*$', '', city, flags=re.I).strip()
    date = datetime.now(timezone.utc).date().isoformat()
    return {'id': 'baka:webcam:' + record['directory'] + ':' + hashlib.sha256(final.encode()).hexdigest()[:16],
            'name': name, 'section': 'webcam', 'country': country, 'city': city,
            'coordinates': webcam_geography.coordinates_from_page(text),
            'language': [], 'genre': genres(name, record.get('body', '')),
            'nsfw': False, 'publisher': record['directory'], 'canonical_url': media_identity(media, final),
            'directory_urls': [record['url']],
            'sources': [{'source_id': record['directory'] + '-' + hashlib.sha256(final.encode()).hexdigest()[:16],
                         'provider_id': record['directory'], 'display_name': record['directory'],
                         'url': final, 'resolver': 'webcam_page', 'protocol': media['protocol'], 'quality': 'unknown',
                         'official': False, 'rights_evidence_url': final,
                         'last_verified_at': '' if record.get('native_skyline') else date,
                         'listed_at': date,
                         'listing_evidence_url': ('https://www.skylinewebcams.com/en/webcam/'
                             + urlsplit(record['url']).path.split('/')[3] + '.html') if record.get('native_skyline') else '',
                         'verification': 'listed-public-player' if record.get('native_skyline') else 'extracted-media',
                         'active': True}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directories', default=','.join(DIRECTORIES))
    parser.add_argument('--worldcam-pages', type=int, default=1)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--limit', type=int, default=0, help='Optional per-directory development limit; 0 imports all discoveries')
    parser.add_argument('--out', type=Path, default=ROOT / 'resources/livestreams/sources/world_webcams.json')
    args = parser.parse_args()
    fetch = Fetcher(ROOT / '.cache/world-webcams-pages')
    records = []
    discover = {'skyline': lambda: discover_skyline(fetch), 'liveworld': lambda: discover_liveworld(fetch),
                'earthcam': lambda: discover_earthcam(fetch),
                'worldcam': lambda: discover_worldcam(fetch, args.worldcam_pages),
                'panorama': lambda: discover_panorama(fetch)}
    for name in args.directories.split(','):
        found = discover[name]()
        print(name, 'discovered', len(found), flush=True)
        records.extend(found[:args.limit] if args.limit else found)
    results, failures = [], Counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(build_camera, record, fetch): record for record in records}
        for index, job in enumerate(as_completed(jobs), 1):
            record = jobs[job]
            try:
                camera = job.result()
                if camera:
                    results.append(camera)
                else:
                    failures[record['directory'] + ':no-media'] += 1
            except Exception as exc:
                failures[record['directory'] + ':' + type(exc).__name__] += 1
            if index % 25 == 0 or index == len(jobs):
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps({'version': 1, 'channels': sorted(results, key=lambda c:c['id'])},
                                               ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                print(index, '/', len(jobs), 'catalogued', len(results), 'failures', dict(failures), flush=True)
    report = {'discovered': len(records), 'extracted': len(results), 'failures': dict(failures),
              'directories': dict(Counter(c['publisher'] for c in results)),
              'countries': dict(Counter(c['country'] for c in results)),
              'verification': 'Media extraction or native public-player listing; playback has not been tested for every camera.'}
    (ROOT / '.cache' / (args.out.stem + '.report.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
