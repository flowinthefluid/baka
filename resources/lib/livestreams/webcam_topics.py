"""Shared, non-exclusive webcam topics derived from catalogue metadata."""
import re
import unicodedata

TERMS = {
    'mountains': ('mountain', 'berg', 'summit', 'alps', 'alpen', 'peak', 'dachstein'),
    'mountain_landscape': ('mountain', 'berglandschaft', 'bergpanorama', 'alps', 'alpen', 'summit', 'peak'),
    'beach': ('beach', 'strand', 'playa', 'spiaggia', 'shore', 'maldives', 'seaside'),
    'desert': ('desert', 'wuste', 'sahara', 'namib', 'atacama', 'mojave', 'death valley'),
    'pier': ('pier', 'harbor', 'harbour', 'hafen', 'marina', 'port of'),
    'city': ('city', 'downtown', 'square', 'piazza', 'street', 'plaza', 'skyline', 'town'),
    'ski': ('ski', 'gondola', 'piste', 'snowboard'),
    'snow_landscape': ('snow', 'schnee', 'winter', 'glacier', 'gletscher', 'ski', 'arctic', 'antarctic'),
    'animals': ('animal', 'wildlife', 'elephant', 'zoo', 'safari', 'aquarium'),
    'birds': ('eagle', 'stork', 'osprey', 'owl', 'bird', 'falcon'),
    'lake': ('lake', 'lago', 'loch', 'see', 'lakes'),
    'river': ('river', 'rivers', 'fluss', 'rhein', 'danube'),
    'volcano': ('volcano', 'volcan', 'etna', 'vulkan'),
    'waterfall': ('waterfall', 'falls', 'wasserfall'),
    'landmark': ('cathedral', 'colosseum', 'temple', 'tower', 'unesco', 'castle'),
    'traffic': ('airport', 'railway', 'runway', 'railfan', 'highway', 'autobahn', 'street', 'road'),
    'roads': ('highway', 'motorway', 'autobahn', 'street', 'road', 'strasse', 'verkehr'),
    'sports_venues': ('stadium', 'stadion', 'arena', 'sports ground', 'sportplatz', 'golf course', 'tennis court', 'ski'),
    'park': ('park', 'garden', 'forest', 'woods'),
    'forest': ('forest', 'wald', 'woods', 'rainforest', 'regenwald'),
    'island': ('island', 'insel', 'maldives', 'seychelles'),
    'airport': ('airport', 'flughafen', 'runway'),
    'railway': ('railway', 'railroad', 'railfan', 'bahnhof', 'eisenbahn'),
    'coast': ('coast', 'kuste', 'shore', 'seaside', 'beach', 'strand'),
    'rockies': ('rocky mountains', 'rockies', 'canmore', 'banff', 'pikes peak', 'jackson hole', 'snow king'),
}


def classify(title, body='', existing=()):
    text = unicodedata.normalize('NFKD', title + ' ' + body[:1000])
    text = ''.join(char for char in text if not unicodedata.combining(char)).casefold()
    result = list(existing or ())
    for topic, terms in TERMS.items():
        if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text) for term in terms):
            result.append(topic)
    if 'rockies' in result:
        result.extend(('mountains', 'mountain_landscape'))
    if 'mountains' in result:
        result.append('mountain_landscape')
    if 'ski' in result:
        result.extend(('snow_landscape', 'sports_venues'))
    return list(dict.fromkeys(result or ['nature']))