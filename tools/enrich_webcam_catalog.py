"""Enrich existing cameras from cached metadata without recrawling providers."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resources.lib.livestreams import webcam_geography, webcam_topics


def enrich(channels, cache):
    for channel in channels:
        text = ''
        for url in channel.get('directory_urls', []):
            path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
            if path.exists():
                page = json.loads(path.read_text(encoding='utf-8'))
                text = page.get('text', '')
                location = webcam_geography.coordinates_from_page(text)
                if location:
                    channel['coordinates'] = location
                    channel['coordinate_evidence_url'] = url
                    break
        channel['genre'] = webcam_topics.classify(channel['name'], existing=channel.get('genre', []))
    return channels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.cache/world-webcams-pages')
    args = parser.parse_args()
    for name in ('world_webcams.json', 'public_webcams.json'):
        path = ROOT / 'resources/livestreams/sources' / name
        data = json.loads(path.read_text(encoding='utf-8'))
        enrich(data['channels'], args.cache)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(name, len(data['channels']), 'cameras;', sum(bool(c.get('coordinates')) for c in data['channels']), 'located')
        print(dict(Counter(topic for c in data['channels'] for topic in c['genre'])))


if __name__ == '__main__':
    main()