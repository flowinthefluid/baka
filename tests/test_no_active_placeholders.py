# -*- coding: utf-8 -*-
"""Active media needs a check date; deferred public players need dated provenance."""
import glob
import json
import os
from urllib.parse import urlsplit

import pytest

from resources.lib.livestreams import model

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'resources', 'livestreams', 'sources')


def _shipped():
    out = []
    for path in sorted(glob.glob(os.path.join(_SRC, '*.json'))):
        for raw in (json.load(open(path, encoding='utf-8')).get('channels') or []):
            ch = model.normalize_channel(raw)
            if ch:
                out.append(ch)
    return out


def test_no_active_source_uses_placeholder_domain():
    offenders = []
    for ch in _shipped():
        for s in ch['sources']:
            if s.get('active') and model.is_placeholder_url(s['url']):
                offenders.append('%s -> %s' % (ch['id'], s['url']))
    assert not offenders, 'Aktive Platzhalter-Quellen: %s' % offenders


def test_active_source_requires_verification_or_documented_player_listing():
    missing = []
    for ch in _shipped():
        for s in ch['sources']:
            if s.get('active') and not (s.get('last_verified_at') or ch.get('last_verified_at')):
                listing = urlsplit(s.get('listing_evidence_url',''))
                if (s.get('resolver') == 'webcam_page' and s.get('provider_id') == 'skyline'
                    and s.get('verification') == 'listed-public-player' and s.get('listed_at')
                    and listing.scheme == 'https' and listing.hostname == 'www.skylinewebcams.com'
                    and listing.path.startswith('/en/webcam/') and listing.path.endswith('.html')):
                    continue
                missing.append('%s -> %s' % (ch['id'], s['url']))
    assert not missing, 'Active sources without dated verification or player provenance: %s' % missing[:10]


@pytest.mark.parametrize('url, is_ph', [
    ('https://example.org/a.jpg', True),
    ('https://example.gov/x.jpg', True),
    ('http://203.0.113.10:8080/video.mjpg', True),
    ('http://198.51.100.5/s', True),
    ('http://192.0.2.9/s', True),
    ('plugin://plugin.video.youtube/play/?channel_id=UC_EXAMPLE&live=1', True),
    ('https://zdf-hls-15.akamaized.net/hls/live/x/master.m3u8', False),
    ('https://mcdn.daserste.de/x/master.m3u8', False),
])
def test_is_placeholder_url(url, is_ph):
    assert model.is_placeholder_url(url) is is_ph


def test_placeholder_source_is_auto_deactivated_even_if_marked_active():
    src = model.normalize_source({'url': 'https://example.org/live.m3u8',
                                  'official': True, 'active': True})
    assert src['active'] is False   # Platzhalter kann nie aktiv sein
