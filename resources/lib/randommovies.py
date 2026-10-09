import random
from datetime import date, timedelta
from urllib.parse import parse_qs

import xbmc
import xbmcgui

from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tmdb import cTMDB

# Zufallsauswahl je Inhaltsordner des Hauptmenues. Die Kennungen entsprechen
# den Inhaltskategorien aus dem pluginHandler. Filme behalten die alten
# Setting-Kennungen, damit vorhandene Einstellungen erhalten bleiben.
# 'fixed' ist das Pflichtgenre je TMDB-Medium; gemischte Arten ziehen Filme
# und Serien anteilig zur Katalog-Groesse.
KINDS = {
    'filme': {'label': 30868, 'art': 'movies.png', 'media': ('movie',), 'fixed': {},
              'settings': '', 'companies': True},
    'serien': {'label': 31891, 'art': 'series.png', 'media': ('tv',), 'fixed': {},
               'settings': 'Series'},
    'animes': {'label': 31892, 'art': 'anime.png', 'media': ('movie', 'tv'),
               'fixed': {'movie': '16', 'tv': '16'}, 'language': 'ja', 'settings': 'Anime'},
    'dokus': {'label': 31893, 'art': 'dokus.png', 'media': ('movie', 'tv'),
              'fixed': {'movie': '99', 'tv': '99'}, 'settings': 'Docs'},
    'kinder': {'label': 31894, 'art': 'kinder.png', 'media': ('movie', 'tv'),
               'fixed': {'movie': '10751', 'tv': '10762'}, 'settings': 'Kids'},
}

# TMDB meldet groessere Trefferzahlen nur noch als 20001.
TMDB_RESULT_CAP = 20000

# Offizielle TMDB-Seriengenres. Die Filmgenres ergeben sich wie bisher aus
# allen bekannten Genres ohne die reinen Seriengenres.
TV_GENRES = (16, 18, 35, 37, 80, 99, 9648, 10751, 10759, 10762, 10763, 10764,
             10765, 10766, 10767, 10768)


def _kind(kind):
    return kind if kind in KINDS else None


def _setting(kind, name):
    return 'random%s%s' % (KINDS[kind]['settings'], name)


def label(kind):
    return cConfig().getLocalizedString(KINDS[kind]['label'])


def _mediaGenres(media):
    from resources.lib.categories import TV_ONLY_GENRES

    if media == 'tv':
        return set(TV_GENRES)
    return {genre_id for genre_id in cTMDB.TMDB_GENRES if genre_id not in TV_ONLY_GENRES}


def _genres(kind='filme'):
    config = KINDS[kind]
    fixed = {int(genre_id) for genre_id in config['fixed'].values()}
    ids = set().union(*(_mediaGenres(media) for media in config['media'])) - fixed
    return sorted(((genre_id, cTMDB.TMDB_GENRES[genre_id]) for genre_id in ids),
                  key=lambda entry: entry[1])


def _companies():
    from resources.lib.categories import COMPANY_PRESETS, PRESET_QUERIES

    return [(parse_qs(PRESET_QUERIES[key][1])['with_companies'][0], name)
            for name, key in COMPANY_PRESETS]


def _excludedGenres(kind='filme'):
    valid = {str(genre_id) for genre_id, name in _genres(kind)}
    return set(cConfig().getSetting(_setting(kind, 'ExcludedGenres'), '').split(',')) & valid


def editGenres(kind='filme'):
    if not _kind(kind):
        return
    genres = _genres(kind)
    excluded = _excludedGenres(kind)
    selected = xbmcgui.Dialog().multiselect(
        '%s: %s' % (label(kind), cConfig().getLocalizedString(31701)), [name for genre_id, name in genres],
        preselect=[index for index, (genre_id, name) in enumerate(genres) if str(genre_id) not in excluded])
    if selected is not None:
        allowed = set(selected)
        cConfig().setSetting(_setting(kind, 'ExcludedGenres'), ','.join(
            str(genre_id) for index, (genre_id, name) in enumerate(genres) if index not in allowed))


def menuEntry(kind, art):
    """Ordner "Zufaellige ..." fuer den Inhaltsordner des Hauptmenues."""
    element = cGuiElement(label(kind), 'random', 'randomMovies')
    element.setThumbnail(art)
    params = ParameterHandler()
    params.setParam('randomKind', kind)
    return element, params


def _folder(title, level, mode='', value='', kind='filme'):
    params = ParameterHandler()
    params.setParam('randomKind', kind)
    params.setParam('randomLevel', level)
    params.setParam('randomMode', mode)
    params.setParam('randomValue', value)
    cGui().addFolder(cGuiElement(title, 'random', 'randomMovies'), params)


def showMenu():
    params = ParameterHandler()
    kind = _kind(params.getValue('randomKind') or 'filme')
    if not kind:
        cGui().setEndOfDirectory(False)
        return
    level = params.getValue('randomLevel') or 'root'
    if level == 'entries':
        _entries(params, kind)
        return
    if level == 'genres':
        for genre_id, name in _genres(kind):
            _folder(name, 'entries', 'genre', str(genre_id), kind)
    elif level == 'companies' and KINDS[kind].get('companies'):
        for company_id, name in _companies():
            _folder(name, 'entries', 'company', company_id, kind)
    else:
        _folder('Random', 'entries', 'random', kind=kind)
        _folder(cConfig().getLocalizedString(31702), 'genres', kind=kind)
        if KINDS[kind].get('companies'):
            _folder(cConfig().getLocalizedString(31703), 'companies', kind=kind)
    cGui().setEndOfDirectory()


def _query(mode, value, kind='filme', media='movie'):
    config = KINDS[kind]
    field = 'primary_release_date' if media == 'movie' else 'first_air_date'
    terms = ['include_adult=false', 'sort_by=%s.asc' % field]
    with_genres = [config['fixed'][media]] if media in config['fixed'] else []
    if config.get('language'):
        terms.append('with_original_language=' + config['language'])
    if mode == 'genre':
        if value not in {str(genre_id) for genre_id, name in _genres(kind)}:
            return None
        with_genres.append(value)
    elif mode == 'company':
        if not config.get('companies') or value not in {company_id for company_id, name in _companies()}:
            return None
        terms.append('with_companies=' + value)
    elif mode == 'random':
        excluded = _excludedGenres(kind)
        if len(excluded) == len(_genres(kind)):
            return None
        own = sorted(genre_id for genre_id in excluded if int(genre_id) in _mediaGenres(media))
        if own:
            terms.append('without_genres=' + ','.join(own))
    else:
        return None
    if with_genres:
        terms.append('with_genres=' + ','.join(with_genres))
    return '&'.join(terms)


def _queries(kind, mode, value):
    """TMDB-Abfrage je Medium; ein reines Filmgenre ueberspringt Serien."""
    queries = {}
    for media in KINDS[kind]['media']:
        if mode == 'genre' and value.isdigit() and int(value) not in _mediaGenres(media):
            continue
        extra = _query(mode, value, kind, media)
        if extra is None:
            return None
        queries[media] = extra
    return queries or None


class _Catalog(object):
    """Ein datierter TMDB-Discover-Katalog (Filme oder Serien)."""

    def __init__(self, tmdb, extra, media, canceled, start, end, selected, progress):
        self.tmdb = tmdb
        self.extra = extra
        self.media = media
        self.field = 'primary_release_date' if media == 'movie' else 'first_air_date'
        self.canceled = canceled
        self.start = start
        self.end = end
        self.selected = selected
        self.progress = progress

    def query(self, first, last, page=1):
        if self.canceled():
            return {}
        self.progress(len(self.selected))
        terms = '%s&%s.gte=%s&%s.lte=%s' % (self.extra, self.field, first, self.field, last)
        data = self.tmdb.getUrl('discover/' + self.media, page, terms) or {}
        if self.canceled():
            return {}
        if 'total_results' not in data:
            raise ValueError(cConfig().getLocalizedString(31715))
        return data

    def parts(self, scanned):
        """Zerlegt den Zeitraum, bis keine Trefferzahl mehr gedeckelt ist."""
        found = []

        def split(first, last, data):
            if self.canceled():
                return
            if int(data.get('total_results') or 0) <= TMDB_RESULT_CAP:
                found.append((first, last, int(data.get('total_results') or 0), data))
                scanned(((last - self.start).days + 1) / ((self.end - self.start).days + 1))
                return
            if first >= last:
                raise ValueError('TMDB-Trefferlimit fuer einen einzelnen Erscheinungstag erreicht')
            middle = first + timedelta(days=(last - first).days // 2)
            split(first, middle, self.query(first, middle))
            split(middle + timedelta(days=1), last, self.query(middle + timedelta(days=1), last))

        split(self.start, self.end, self.query(self.start, self.end))
        return found

    def collect(self, first, last, ranks, data):
        if not ranks or self.canceled():
            return
        total = int(data.get('total_results') or 0)
        if total > 10000:
            if first >= last:
                raise ValueError('TMDB-Seitenlimit fuer einen einzelnen Erscheinungstag erreicht')
            middle = first + timedelta(days=(last - first).days // 2)
            left = self.query(first, middle)
            if self.canceled():
                return
            left_count = int(left.get('total_results') or 0)
            self.collect(first, middle, [rank for rank in ranks if rank < left_count], left)
            right_ranks = [rank - left_count for rank in ranks if rank >= left_count]
            if right_ranks:
                self.collect(middle + timedelta(days=1), last, right_ranks,
                             self.query(middle + timedelta(days=1), last))
            return
        pages = {}
        for rank in ranks:
            if rank < total:
                pages.setdefault(rank // 20 + 1, []).append(rank % 20)
        for page, offsets in pages.items():
            if self.canceled():
                return
            results = (data if page == 1 else self.query(first, last, page)).get('results') or []
            for offset in offsets:
                if offset < len(results):
                    results[offset]['_media'] = self.media
                    self.selected.append(results[offset])
            self.progress(len(self.selected))


def sampleCatalogs(tmdb, queries, count, canceled=lambda: False, start=None, end=None,
                   progress=lambda count: None, scanned=lambda fraction: None):
    """Zieht gleichverteilt aus der Vereinigung datierter TMDB-Kataloge.

    TMDB meldet groessere Trefferzahlen nur noch gedeckelt. Jeder Katalog wird
    deshalb zuerst in Zeitraeume mit echter Trefferzahl zerlegt; die
    Zaehlabfragen landen im normalen TMDB-Cache.
    """
    start = start or date(1800, 1, 1)
    end = end or date.today()
    selected = []
    parts = []
    for index, (media, extra) in enumerate(queries.items()):
        catalog = _Catalog(tmdb, extra, media, canceled, start, end, selected, progress)
        parts.extend((catalog,) + part for part in catalog.parts(
            lambda fraction, index=index: scanned((index + fraction) / len(queries))))
    total = sum(part[3] for part in parts)
    ranks = sorted(random.sample(range(total), min(count, total)))
    offset = 0
    for catalog, first, last, size, data in parts:
        catalog.collect(first, last, [rank - offset for rank in ranks if offset <= rank < offset + size], data)
        offset += size
    unique = {(item['_media'], item['id']): item for item in selected
              if item.get('id') and (item.get('title') or item.get('name'))}
    selected = list(unique.values())
    random.shuffle(selected)
    return selected


def sampleCatalog(tmdb, extra, count, canceled=lambda: False, start=None, end=None, progress=lambda count: None,
                  media='movie'):
    return sampleCatalogs(tmdb, {media: extra}, count, canceled, start, end, progress)


def _entries(params, kind='filme'):
    from resources.lib import plotinfo

    mode = params.getValue('randomMode') or 'random'
    queries = _queries(kind, mode, str(params.getValue('randomValue') or ''))
    gui = cGui()
    minimum = plotinfo.minimumRating(_setting(kind, 'MinImdb'))
    if queries is None:
        gui.showInfo('GerXStream', cConfig().getLocalizedString(31721))
        gui.setEndOfDirectory(False)
        return
    if not plotinfo.requireImdbKey(minimum):
        gui.setEndOfDirectory(False)
        return
    limit = max(1, min(cConfig().getSettingInt(_setting(kind, 'ItemsCount'), 250), 1000))
    progress = xbmcgui.DialogProgress()
    progress.create(label(kind))
    monitor = xbmc.Monitor()
    canceled = lambda: progress.iscanceled() or monitor.abortRequested()
    candidate_count = min(limit * 4, 1000) if minimum else limit
    try:
        with cRequestHandler.backgroundRequests():
            pool = sampleCatalogs(cTMDB(), queries, candidate_count, canceled,
                                  progress=lambda count: progress.update(30 + min(50, count * 50 // candidate_count)),
                                  scanned=lambda fraction: progress.update(min(30, int(30 * fraction))))
            selected = []
            excluded = _excludedGenres(kind) if mode == 'random' else set()
            for index, item in enumerate(pool):
                if canceled():
                    break
                progress.update(80 + int(20 * index / max(len(pool), 1)))
                if excluded & {str(genre_id) for genre_id in item.get('genre_ids') or []}:
                    continue
                if plotinfo.matchesMinimum(item, item['_media'], minimum):
                    selected.append(item)
                if len(selected) >= limit:
                    break
            aborted = canceled()
    except ValueError as error:
        gui.showInfo('GerXStream', str(error))
        gui.setEndOfDirectory(False)
        return
    finally:
        progress.close()
    if aborted:
        gui.setEndOfDirectory(False)
        return
    if len(selected) < limit:
        gui.showInfo('GerXStream', cConfig().getLocalizedString(31704) % (len(selected), limit))
    for item in selected:
        # discover/movie liefert 'title', discover/tv 'name'.
        title = item.get('title') or item.get('name')
        media = 'movie' if item['_media'] == 'movie' else 'tvshow'
        element = cGuiElement(title, 'random', 'searchTMDB')
        element.setMediaType(media)
        year = (item.get('release_date') or item.get('first_air_date') or '')[:4]
        if year.isdigit():
            element.setYear(year)
        element.setDescription(item.get('overview') or '')
        if item.get('poster_path'):
            element.setThumbnail('https://image.tmdb.org/t/p/w342' + item['poster_path'])
        if item.get('backdrop_path'):
            element.setFanart('https://image.tmdb.org/t/p/w1280' + item['backdrop_path'])
        search = ParameterHandler()
        for key, value in (('searchTitle', title),
                           ('searchOriginalTitle', item.get('original_title') or item.get('original_name') or ''),
                           ('searchYear', year), ('searchMedia', media), ('searchTmdbID', item['id'])):
            search.setParam(key, value)
        gui.addFolder(element, search, True, len(selected))
    gui.setView('tvshows' if all(item['_media'] == 'tv' for item in selected) and selected else 'movies')
    gui.setEndOfDirectory()
