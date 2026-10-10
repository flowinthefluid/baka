"""Optional production-company filtering and actor boycotts, independent of locations.

Light: only productions whose listed companies are all Hollywood studios.
Strict: any studio participation or a studio parent company. The relation graph
is bounded by TMDB's company data; historical informal collaborations are unknown.
"""

import json
import os
import re
import time
import unicodedata
from urllib.parse import quote_plus

from resources.lib.config import cConfig
from resources.lib.tmdb import cTMDB

SCOPES = (('movies', 32300), ('docs', 32301), ('anime', 32302),
          ('categories', 30507), ('locations', 32094), ('people', 31600),
          ('world', 32078), ('companies', 32093), ('random', 32809))
# TMDB company IDs. Independent US studios are not automatically Hollywood.
STUDIOS = {1, 2, 3, 4, 5, 12, 17, 25, 33, 34, 174, 420, 521}
STUDIO_NAMES = {
    'waltdisneypictures', 'waltdisneyproductions', 'pixar', 'lucasfilm',
    'marvelstudios', '20thcenturyfox', '20thcenturystudios',
    'foxsearchlightpictures', 'searchlightpictures', 'warnerbrospictures',
    'warnerbrosentertainment', 'newlinecinema', 'paramountpictures',
    'columbiapictures', 'tristarpictures', 'sonypictures', 'sonypicturesentertainment',
    'universalpictures', 'focusfeatures', 'dreamworksanimation', 'dreamworkspictures',
    'metrogoldwynmayer', 'unitedartists'}
_cache = None
MAX_AGE = 7 * 24 * 60 * 60


def _normal(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', str(value).casefold()) if char.isalnum())


def _request(path, term=''):
    """Small disk cache; failed requests stay retryable."""
    global _cache
    from xbmcvfs import translatePath
    pathToCache = os.path.join(translatePath(cConfig().getAddonInfo('profile')), 'production_metadata.json')
    if _cache is None:
        try:
            with open(pathToCache, encoding='utf-8') as handle:
                _cache = json.load(handle)
            if not isinstance(_cache, dict):
                _cache = {}
        except (OSError, ValueError):
            _cache = {}
    key = path + '?' + term
    entry = _cache.get(key)
    now = time.time()
    if isinstance(entry, dict) and now - entry.get('ts', 0) < MAX_AGE:
        return entry.get('data', {})
    data = cTMDB().getUrl(path, 1, term) or {}
    if data and not data.get('success') is False:
        _cache[key] = {'ts': now, 'data': data}
        if len(_cache) > 1500:
            _cache = dict(sorted(_cache.items(), key=lambda pair: pair[1].get('ts', 0))[-1200:])
        try:
            os.makedirs(os.path.dirname(pathToCache), exist_ok=True)
            with open(pathToCache + '.new', 'w', encoding='utf-8') as handle:
                json.dump(_cache, handle, separators=(',', ':'))
            os.replace(pathToCache + '.new', pathToCache)
        except OSError:
            pass
    return data


def scope(params=None):
    from resources.lib.handler.ParameterHandler import ParameterHandler
    from resources.lib import languages
    params = params or ParameterHandler()
    explicit = params.getValue('hollywoodScope')
    if explicit in dict(SCOPES):
        return explicit
    preset = params.getValue('catPreset') or ''
    if preset.startswith(('country:', 'region:', 'location_')):
        return 'locations'
    if preset.startswith('world_'):
        return 'world'
    if preset.startswith('company_'):
        return 'companies'
    if params.getValue('catPerson'):
        return 'people'
    if params.getValue('randomKind'):
        return 'random'
    if params.getValue('catLevel'):
        return 'categories'
    return languages.currentTheme() or 'movies'


def mode(params=None):
    from resources.lib import languages
    from resources.lib.handler.ParameterHandler import ParameterHandler
    params = params or ParameterHandler()
    conf = cConfig()
    theme = languages.themeForCategory(params.getValue('contentTheme') or params.getValue('randomKind'))
    contexts = {scope(params), theme or languages.currentTheme() or 'movies'}
    active = conf.getSettingBool('hollywoodGlobal', False) or bool(contexts.intersection(
        conf.getSetting('hollywoodScopes', '').split(',')))
    selected = conf.getSetting('hollywoodMode', 'light')
    return ('strict' if selected == 'strict' else 'light') if active else ''


def editScopes():
    import xbmcgui
    active = set(cConfig().getSetting('hollywoodScopes', '').split(','))
    result = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32802),
        [cConfig().getLocalizedString(label) for key, label in SCOPES],
        preselect=[index for index, (key, label) in enumerate(SCOPES) if key in active])
    if result is not None:
        cConfig().setSetting('hollywoodScopes', ','.join(SCOPES[index][0] for index in result))


def _studio(company):
    return company.get('id') in STUDIOS or _normal(company.get('name', '')) in STUDIO_NAMES


def _connected(company, seen=None):
    if _studio(company):
        return True
    seen = set() if seen is None else seen
    companyId = str(company.get('id') or '')
    if not re.fullmatch('[1-9]\\d{0,9}', companyId) or companyId in seen or len(seen) >= 8:
        return None
    seen.add(companyId)
    details = _request('company/' + companyId)
    if not details:
        return None
    if _studio(details):
        return True
    parent = details.get('parent_company')
    return _connected(parent, seen) if isinstance(parent, dict) and parent else False


def _identity(element, params):
    media = element._mediaType if element else (params.getValue('mediaType') or params.getValue('searchMedia'))
    if media not in ('movie', 'tv', 'tvshow', 'season', 'episode'):
        return '', ''
    series = media in ('tv', 'tvshow', 'season', 'episode')
    kind = 'tv' if series else 'movie'
    explicit = params.getValue('searchTmdbID') or params.getValue('filterTmdbID')
    if not explicit and media not in ('episode', 'season'):
        explicit = params.getValue('tmdbID') or (element._tmdbID if element else '')
    if re.fullmatch(r'[1-9]\d{0,9}', str(explicit or '')):
        return kind, str(explicit)
    values = element.getItemValues() if element else {}
    title = ((values.get('TVShowTitle') or params.getValue('TVShowTitle') or params.getValue('watchlistTitle'))
             if media in ('episode', 'season') else
             (params.getValue('searchTitle') or (element.getTitle() if element else '') or params.getValue('MovieTitle')))
    if not title:
        return kind, ''
    year = (element._sYear if element else '') or params.getValue('searchYear') or params.getValue('watchlistYear')
    rows = _request('search/' + kind, 'query=' + quote_plus(title)).get('results', [])
    exact = [row for row in rows if _normal(title) in {
        _normal(row.get('title') or row.get('name', '')),
        _normal(row.get('original_title') or row.get('original_name', ''))}
        and (not year or str(row.get('release_date') or row.get('first_air_date') or '').startswith(str(year)))]
    return kind, str(exact[0]['id']) if len(exact) == 1 else ''


def allowed(element=None, params=None):
    from resources.lib.handler.ParameterHandler import ParameterHandler
    from resources.lib import personfilters
    params = params or ParameterHandler()
    selectedMode = mode(params)
    boycott = set(personfilters.stored('boycott'))
    if not selectedMode and not boycott:
        return True
    kind, titleId = _identity(element, params)
    if not kind:
        return True  # menus, live TV, sports and webcams
    unknownAllowed = not (boycott or selectedMode == 'strict') or not cConfig().getSettingBool('productionUnknownHide', True)
    if not titleId:
        return unknownAllowed
    # Preserve an unambiguous series ID down through season/provider routes.
    params.setParam('filterTmdbID', titleId)
    params.setParam('hollywoodScope', scope(params))
    if selectedMode:
        details = _request(kind + '/' + titleId)
        companies = details.get('production_companies')
        if not isinstance(companies, list) or not companies:
            if not unknownAllowed:
                return False
        elif selectedMode == 'light':
            if all(_studio(company) for company in companies):
                return False
        else:
            connections = [_connected(company) for company in companies]
            if True in connections or (None in connections and not unknownAllowed):
                return False
    if boycott:
        credits = _request(kind + '/' + titleId + ('/aggregate_credits' if kind == 'tv' else '/credits'))
        if not isinstance(credits.get('cast'), list):
            return unknownAllowed
        if any(str(person.get('id')) in boycott for person in credits['cast']):
            return False
    return True
