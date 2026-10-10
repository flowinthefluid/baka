"""Sportarten fuer Sender; gemischte Programme bleiben als solche markiert."""

import re

SPORTS = (
    ('football', 32320, 'Fußball', r'fifa|golazo|football|fussball|fußball|soccer|barca|real.?madrid|mutv|brondby|fck'),
    ('motorsport', 32321, 'Motorsport', r'\bf1\b|formula|racing|racer|rally|motor|nhra|monster jam|speed|drift'),
    ('tennis', 32322, 'Tennis', r'tennis'),
    ('basketball', 32323, 'Basketball', r'\bnba\b|basketball'),
    ('combat', 32324, 'Kampfsport', r'\bmma\b|fight|combat|boxing|kickbox|bellator|wrestling|\bwwe\b|\bpfl\b|\bufc\b|glory'),
    ('winter', 32325, 'Wintersport', r'\bski\b|snow|winter|\bnhl\b|hockey'),
    ('cycling', 32326, 'Radsport', r'cycling|bicycle|biking'),
    ('golf', 32327, 'Golf', r'golf|\bpga\b'),
    ('american_football', 32328, 'American Football', r'\bnfl\b|american football'),
    ('baseball', 32329, 'Baseball', r'\bmlb\b|baseball'),
    ('cricket', 32330, 'Cricket', r'cricket'),
    ('water', 32331, 'Wassersport', r'nautical|sailing|surf|water sport'),
    ('billiards', 32332, 'Billard & Snooker', r'billiard|snooker|kozoom'),
    ('darts', 32333, 'Darts', r'darts'),
    ('handball', 32334, 'Handball', r'handball|handboll'),
    ('esports', 32335, 'E-Sport', r'\be-?sports?\b|gaming'),
    ('bowling', 32337, 'Bowling', r'bowling'),
    ('lacrosse', 32338, 'Lacrosse', r'lacrosse'),
    ('strength', 32339, 'Kraftsport', r'strongman|powerlift|weightlift'),
    ('other', 32336, 'Weitere / gemischte Sportarten', None),
)
SPORT_IDS = tuple(item[0] for item in SPORTS)


def classify(name):
    kinds = [key for key, _label, _fallback, pattern in SPORTS
             if pattern and re.search(pattern, name or '', re.I)]
    # "American Football" ist nicht gleichzeitig Fußball.
    if 'american_football' in kinds and 'football' in kinds:
        kinds.remove('football')
    return kinds or ['other']


def kinds(channel):
    return channel.get('sport') or classify(channel.get('name', ''))


def label(key):
    from resources.lib.livestreams.taxonomy import _localized
    return next((_localized(number, fallback) for slug, number, fallback, _ in SPORTS if slug == key), key)
