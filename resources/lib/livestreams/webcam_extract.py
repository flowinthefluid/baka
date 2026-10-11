"""Public webcam players: extract media, never substitute directory thumbnails."""
import html
import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

USER_AGENT = 'Mozilla/5.0'


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag.lower(), dict(attrs)))


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', value or ''))).strip()


def json_assignment(text, variable):
    match = re.search(r'\b' + re.escape(variable) + r'\s*=\s*', text)
    if not match:
        return None
    try:
        return json.JSONDecoder().raw_decode(text[match.end():])[0]
    except ValueError:
        return None


def _media(url, protocol, page):
    url = urljoin(page, html.unescape(url.replace('\\/', '/')))
    if urlsplit(url).scheme not in ('http', 'https', 'plugin'):
        return None
    return {'url': url, 'protocol': protocol,
            'headers': {'User-Agent': USER_AGENT, 'Referer': page}}


def extract(text, page):
    """Return media + explicitly embedded/operator pages for bounded follow-up."""
    host = (urlsplit(page).hostname or '').lower()
    tags = Page(text).tags
    media, links = [], []
    youtube = re.search(r"new\s+YT\.Player\([^;]{0,2500}?videoId\s*:\s*['\"]([A-Za-z0-9_-]{11})['\"]", text)
    if youtube:
        media.append({'url':'plugin://plugin.video.youtube/play/?video_id=' + youtube.group(1),
                      'protocol':'plugin', 'headers':{}})
    if host.endswith('earthcam.com'):
        data = json_assignment(text, 'json_base') or {}
        cams = data.get('cam', {})
        requested = parse_qs(urlsplit(page).query).get('cam', [''])[0]
        selected = cams.get(requested) if requested else None
        if requested and selected is None:
            return [], []  # Never play a different camera than the requested view.
        if selected is None:
            current = json_assignment(text, 'currentName')
            selected = cams.get(current) or next(iter(cams.values()), {})
        stream = selected.get('stream') or (selected.get('html5_streamingdomain', '') +
                                             selected.get('html5_streampath', ''))
        if '.m3u8' in stream:
            media.append(_media(stream, 'hls', page))
    if host.endswith('skylinewebcams.com'):
        match = re.search(r"\bsource\s*:\s*['\"](livee?\.m3u8[^'\"]+)['\"]", text)
        if match:
            stream = 'https://hd-auth.skylinewebcams.com/' + match.group(1).replace('livee.', 'live.')
            media.append(_media(stream, 'hls', page))
    if host.endswith('panoramablick.com'):
        # Main player image only: not og:image, nearby cameras or archive tabs.
        match = re.search(r'<div[^>]+class=["\'][^"\']*field-name-field-cam(?:\s|["\'])[^>]*>.*?<img[^>]+src=["\']([^"\']+)', text, re.S)
        if not match:
            match = re.search(r'<div[^>]+class=["\'][^"\']*field-name-field-image[^"\']*["\'].*?<img[^>]+src=["\'](https://archive\.panoramablick\.com/archive/[^"\']+\.jpg)', text, re.S)
        if match:
            media.append(_media(match.group(1), 'jpeg', page))
    for tag, attrs in tags:
        src = attrs.get('src') or attrs.get('data-src') or ''
        if tag == 'iframe' and src:
            if 'youtube.com/embed/' in src or 'youtube-nocookie.com/embed/' in src:
                video = urlsplit(src).path.split('/embed/', 1)[-1].split('/')[0]
                if re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
                    media.append({'url': 'plugin://plugin.video.youtube/play/?video_id=' + video,
                                  'protocol': 'plugin', 'headers': {}})
            elif not any(word in src.lower() for word in ('advert', 'doubleclick', 'google', 'facebook', 'cookie')):
                links.append(urljoin(page, src))
        elif tag in ('source', 'video') and src:
            protocol = 'hls' if '.m3u8' in src else ('dash' if '.mpd' in src else 'mp4')
            media.append(_media(src, protocol, page))
        elif tag == 'img' and (attrs.get('id') in ('webcam-image', 'webcam', 'live-image')
                              or 'webcamImage' in attrs.get('class', '').split()):
            media.append(_media(src, 'jpeg', page))
        elif tag == 'a' and ('player-external-link' in attrs.get('class', '').split()
                            or '/click/source?' in attrs.get('href', '')):
            links.append(urljoin(page, attrs.get('href', '')))
    # HLS/DASH in standard public player config or JSON-LD contentUrl.
    for match in re.finditer(r"(?:source|file|contentUrl|hls|hlsUrl|streamUrl)\s*['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", text, re.I):
        value = match.group(1).replace('\\/', '/')
        if host.endswith('skylinewebcams.com') and value.startswith(('live.', 'livee.')):
            continue  # Skyline's relative configuration requires its dedicated CDN.
        if '.m3u8' in value or '.mpd' in value:
            media.append(_media(value, 'dash' if '.mpd' in value else 'hls', page))
    result, seen = [], set()
    for value in media:
        if value and value['url'] not in seen:
            seen.add(value['url'])
            result.append(value)
    return result, list(dict.fromkeys(links))


def fetch_document(url, session=None):
    """Read bounded HTML/JSON; never buffer a continuous camera response."""
    import requests
    with (session or requests).get(url, headers={'User-Agent': USER_AGENT}, timeout=(8, 8), stream=True) as response:
        response.raise_for_status()
        kind = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
        protocol = {'image/jpeg':'jpeg', 'image/jpg':'jpeg', 'multipart/x-mixed-replace':'mjpeg',
                    'application/vnd.apple.mpegurl':'hls', 'application/x-mpegurl':'hls',
                    'application/dash+xml':'dash', 'video/mp4':'mp4'}.get(kind)
        if protocol:
            return {'url':response.url, 'text':'', 'pages':1,
                    'media':_media(response.url, protocol, url)}
        chunks, size, deadline = [], 0, time.monotonic() + 25
        for chunk in response.iter_content(chunk_size=1024):
            size += len(chunk)
            if size > 4 * 1024 * 1024 or time.monotonic() > deadline:
                raise ValueError('Camera page exceeds the read budget')
            chunks.append(chunk)
        data = b''.join(chunks)
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = data.decode('cp1252', errors='replace')
        return {'url':response.url, 'text':text,
                'pages':int(response.headers.get('X-WP-TotalPages','1'))}


def fetch_page(url, session=None):
    value = fetch_document(url, session)
    return value['media'] if value.get('media') else (value['text'], value['url'])


def resolve(page, fetch=None, max_depth=3):
    """Follow only embeds/operator links, with a small budget and no JS execution."""
    fetch = fetch or fetch_page
    seen = set()
    queue = [(page, 0)]
    while queue and len(seen) < 6:
        url, depth = queue.pop(0)
        if url in seen or urlsplit(url).scheme not in ('http', 'https'):
            continue
        seen.add(url)
        try:
            fetched = fetch(url)
            if isinstance(fetched, dict) and fetched.get('protocol'):
                return fetched
            text, final = fetched
            candidates, links = extract(text, final)
        except Exception:
            continue
        if candidates:
            return candidates[0]
        if depth < max_depth:
            queue.extend((link, depth + 1) for link in links[:3])
    return None


def resolve_source(source):
    result = resolve(source['url'])
    if not result:
        return None
    return dict(source, **result, resolver_page=source['url'])
