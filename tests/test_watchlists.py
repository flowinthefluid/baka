# -*- coding: utf-8 -*-
"""Eigene Watchlists in der Epic-Watchlist und "Liste abspielen"."""

import importlib
import sys
import types
from urllib.parse import parse_qsl, urlsplit

import pytest

from conftest import set_setting
from resources.lib import epicfavorites


MOVIE = {'title': 'Heat', 'target': 'plugin://plugin.video.baka/?site=megakino&function=showHosters&sUrl=heat',
         'media_type': 'movie', 'is_folder': True, 'thumbnail': 'https://img/heat.jpg'}
EPISODE = {'title': 'Carrie S01E01', 'target': 'plugin://plugin.video.baka/?site=serienstream&function=showHosters&sUrl=e1',
           'media_type': 'episode', 'is_folder': True}
SEARCH = {'title': 'Baraka', 'target': 'plugin://plugin.video.baka/?site=random&function=searchTMDB&searchTitle=Baraka',
          'media_type': 'movie', 'is_folder': True}
SERIES = {'title': 'Carrie', 'target': 'plugin://plugin.video.baka/?site=serienstream&function=showSeasons&sUrl=c',
          'media_type': 'tvshow', 'is_folder': True}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(epicfavorites, '_profilePath', lambda: str(tmp_path / 'epic_favorites.json'))
    return tmp_path


def _main(monkeypatch):
    monkeypatch.setitem(sys.modules, 'resolveurl', types.ModuleType('resolveurl'))
    return importlib.import_module('baka')


def _watchlist(name):
    assert epicfavorites.createFolder('', name)
    return next(folder['id'] for folder in epicfavorites.watchlists() if folder['name'] == name)


def test_root_lists_own_watchlists_next_to_statuses(store, monkeypatch, real_strings):
    from resources.lib.gui.gui import cGui
    from resources.lib.handler.ParameterHandler import ParameterHandler

    main = _main(monkeypatch)
    filmabend = _watchlist('Filmabend')
    epicfavorites.addEntry('', MOVIE)  # frueherer Favorit ohne Watchlist
    added = []
    monkeypatch.setattr(cGui, 'addFolder', lambda self, element, params=None, *args: added.append(
        (element.getTitle(), element.getFunction(), dict(params.getAllParameters()) if params else {})))
    monkeypatch.setattr(cGui, 'setView', lambda *args: None)
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    main.showEpicFavorites(ParameterHandler())
    titles = [title for title, function, extra in added]
    assert titles[:4] == ['Geplant', 'Am Schauen', 'Abgeschlossen', 'Abgebrochen']
    assert titles[4:7] == ['Filmabend', 'Favorites', 'Neue Watchlist']
    assert added[4][2]['path'] == filmabend


def test_watchlists_keep_subfolders_and_offer_playback(store, monkeypatch, real_strings):
    from resources.lib.gui.gui import cGui
    from resources.lib.handler.ParameterHandler import ParameterHandler

    main = _main(monkeypatch)
    filmabend = _watchlist('Filmabend')
    assert epicfavorites.createFolder(filmabend, 'Klassiker')
    for entry in (MOVIE, EPISODE, SEARCH, SERIES):
        epicfavorites.addEntry(filmabend, entry)
    added = []
    monkeypatch.setattr(cGui, 'addFolder', lambda self, element, params=None, *args: added.append(
        (element.getTitle(), element.getFunction())))
    monkeypatch.setattr(cGui, 'setView', lambda *args: None)
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    params = ParameterHandler()
    params.setParam('path', filmabend)
    main.showEpicFavorites(params)
    assert added[0] == ('Liste abspielen (2)', 'playEpicList')
    assert ('Klassiker', 'showEpicFavorites') in added
    assert [function for title, function in added].count('openEpicFavorite') == 4


def test_only_direct_sources_are_playable(store):
    filmabend = _watchlist('Filmabend')
    for entry in (MOVIE, EPISODE, SEARCH, SERIES):
        epicfavorites.addEntry(filmabend, entry)
    playable, skipped = epicfavorites.playTargets(filmabend, ['megakino', 'serienstream'])
    assert [entry['title'] for entry, route in playable] == ['Heat', 'Carrie S01E01'] and skipped == 2
    query = dict(parse_qsl(urlsplit(playable[0][1]).query))
    assert query['site'] == 'megakino' and query['function'] == 'showHosters'
    assert query['playMode'] == 'play' and query['mediaType'] == 'movie' and query['MovieTitle'] == 'Heat'


def test_adding_always_goes_into_a_watchlist(store, monkeypatch, real_strings):
    filmabend = _watchlist('Filmabend')
    shown = []

    def select(self, heading, labels):
        shown.append(labels)
        return labels.index('Filmabend') if len(shown) == 1 else 0

    monkeypatch.setattr(epicfavorites.xbmcgui.Dialog, 'select', select, raising=False)
    assert epicfavorites.chooseFolder() == filmabend
    assert not any('speichern' in label for label in shown[0])  # oben kein "Hier speichern"
    assert 'Neue Watchlist' in shown[0] and shown[1][0] == 'In Filmabend speichern'


def test_playing_a_watchlist_queues_every_entry(store, monkeypatch, real_strings):
    import xbmc
    from resources.lib import episodequeue
    from resources.lib.gui.hoster import cHosterGui

    main = _main(monkeypatch)
    filmabend = _watchlist('Filmabend')
    for entry in (MOVIE, SEARCH, EPISODE):
        epicfavorites.addEntry(filmabend, entry)
    monkeypatch.setattr(main.cPluginHandler, 'getPluginNames', lambda self: ['megakino', 'serienstream'])
    monkeypatch.setattr(main, '_endFailedDirectory', lambda: None)
    infos = []
    monkeypatch.setattr(main.cGui, 'showInfo', lambda self, *args: infos.append(args))
    stored = {}
    monkeypatch.setattr(episodequeue, 'store', lambda queueId, targets: stored.update(id=queueId, targets=targets) or True)
    monkeypatch.setattr(episodequeue, 'getTargets', lambda queueId: list(stored['targets']))
    added = []
    monkeypatch.setattr(xbmc.PlayList, 'add', lambda self, url, *args: added.append(url), raising=False)
    played = []
    monkeypatch.setattr(xbmc.Player, 'play', lambda self, *args: played.append(True), raising=False)
    set_setting('autoNextEpisodeEnabled', 'false')  # Watchlists spielen trotzdem komplett
    from resources.lib.handler.ParameterHandler import ParameterHandler
    params = ParameterHandler()
    params.setParam('path', filmabend)
    main.playEpicList(params)
    assert len(stored['targets']) == 2 and added == stored['targets'] and played == [True]
    first = dict(parse_qsl(urlsplit(added[0]).query))
    assert first['episodeQueue'] == stored['id'] and first['episodeIndex'] == '0'
    assert dict(parse_qsl(urlsplit(added[1]).query))['episodeIndex'] == '1'
    assert infos[-1][1] == 'Ohne direkte Quelle übersprungen: 1'
    assert cHosterGui.playQueue(stored['id'], 0) is True and len(added) == 3  # Episoden: nur eine
