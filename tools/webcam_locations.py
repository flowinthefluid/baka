"""Build-time country lookup for camera coordinates (Natural Earth, public domain)."""
import json
from functools import lru_cache
from pathlib import Path

DATA_URL = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson'


@lru_cache(maxsize=1)
def boundaries():
    import requests
    path = Path(__file__).resolve().parents[1] / '.cache/webcam-country-boundaries.json'
    if not path.exists():
        response = requests.get(DATA_URL, timeout=20)
        response.raise_for_status()
        data = response.json()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')
    return json.loads(path.read_text(encoding='utf-8'))['features']


def in_ring(x, y, ring):
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
        previous = current
    return inside


def country_at(longitude, latitude):
    for feature in boundaries():
        geometry = feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        for rings in polygons:
            ring = rings[0]
            if not (min(p[0] for p in ring) <= longitude <= max(p[0] for p in ring)
                    and min(p[1] for p in ring) <= latitude <= max(p[1] for p in ring)):
                continue
            if in_ring(longitude, latitude, ring) and not any(in_ring(longitude, latitude, hole) for hole in rings[1:]):
                code = feature['properties'].get('ISO_A2_EH') or feature['properties'].get('ISO_A2')
                return code.lower() if code and code != '-99' else 'int'
    return 'int'
