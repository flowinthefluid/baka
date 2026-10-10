import json
import sys
import pytest

from conftest import set_setting
from resources.lib import productionfilter as filters, personfilters, persondata
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler


def params(**values):
    result = ParameterHandler()
    result.addParams(values)
    return result


def movie(title='German film in New York'):
    element = cGuiElement(title, 'source', 'getHosters')
    element.setMediaType('movie')
    return element


def test_disabled_filters_make_no_requests(monkeypatch):
    monkeypatch.setattr(filters, '_request', lambda *args: pytest.fail('unexpected metadata request'))
    assert filters.allowed(movie(), params())


@pytest.mark.parametrize('mode,companies,allowed', [
    ('light', [{'id': 2, 'name': 'Walt Disney Pictures'}], False),
    ('light', [{'id': 2}, {'id': 900000, 'name': 'Independent German Studio'}], True),
    ('strict', [{'id': 2}, {'id': 900000}], False),
    ('strict', [{'id': 900000, 'name': 'Independent German Studio'}], True),
])
def test_production_modes_do_not_use_locations(monkeypatch, mode, companies, allowed):
    set_setting('hollywoodGlobal', 'true')
    set_setting('hollywoodMode', mode)
    def request(path, term=''):
        if path == 'movie/42':
            return {'production_companies': companies, 'production_countries': [{'iso_3166_1': 'DE'}]}
        return {'id': 900000, 'name': 'Independent German Studio', 'origin_country': 'DE', 'parent_company': None}
    monkeypatch.setattr(filters, '_request', request)
    assert filters.allowed(movie(), params(searchTmdbID=42)) is allowed


def test_strict_follows_parent_company(monkeypatch):
    set_setting('hollywoodGlobal', 'true')
    set_setting('hollywoodMode', 'strict')
    monkeypatch.setattr(filters, '_request', lambda path, term='': {
        'movie/42': {'production_companies': [{'id': 900000}]},
        'company/900000': {'id': 900000, 'parent_company': {'id': 17}},
    }.get(path, {}))
    assert not filters.allowed(movie(), params(searchTmdbID=42))


def test_parent_cycle_is_unknown_and_bounded(monkeypatch):
    calls = []
    monkeypatch.setattr(filters, '_request', lambda path: calls.append(path) or {
        'id': 900000, 'parent_company': {'id': 900000}})
    assert filters._connected({'id': 900000}) is None
    assert len(calls) == 1


@pytest.mark.parametrize('mode,hide,allowed', [('light', True, True), ('strict', True, False), ('strict', False, True)])
def test_unknown_data_policy(monkeypatch, mode, hide, allowed):
    set_setting('hollywoodGlobal', 'true')
    set_setting('hollywoodMode', mode)
    set_setting('productionUnknownHide', str(hide).lower())
    monkeypatch.setattr(filters, '_request', lambda *args: {})
    assert filters.allowed(movie(), params(searchTmdbID=42)) is allowed


def test_hidden_actor_does_not_hide_movies_but_boycott_does(monkeypatch):
    set_setting('hiddenActors', json.dumps({'123': 'Actor'}))
    monkeypatch.setattr(filters, '_request', lambda *args: pytest.fail('hide must not fetch cast'))
    assert filters.allowed(movie(), params(searchTmdbID=42))
    set_setting('boycottedActors', json.dumps({'123': 'Actor'}))
    monkeypatch.setattr(filters, '_request', lambda *args: {'cast': [{'id': 123}]})
    assert not filters.allowed(movie(), params(searchTmdbID=42))
    assert personfilters.filterPeople([{'id': 123}, {'id': 124}]) == [{'id': 124}]


def test_series_boycott_uses_all_seasons_not_episode_tmdb_id(monkeypatch):
    set_setting('boycottedActors', '{"123":"Actor"}')
    episode = cGuiElement('Episode 1', 'source', 'getHosters')
    episode.setMediaType('episode')
    episode._tmdbID = 999  # episode ID must not be used as a series ID
    episode.setTVShowTitle('Series')
    calls = []
    def request(path, term=''):
        calls.append(path)
        if path == 'search/tv':
            return {'results': [{'id': 42, 'name': 'Series'}]}
        return {'cast': [{'id': 123}]}
    monkeypatch.setattr(filters, '_request', request)
    assert not filters.allowed(episode, params(tmdbID=999))
    assert calls == ['search/tv', 'tv/42/aggregate_credits']


def test_ambiguous_search_is_not_silently_matched(monkeypatch):
    set_setting('hollywoodGlobal', 'true')
    set_setting('hollywoodMode', 'strict')
    monkeypatch.setattr(filters, '_request', lambda *args: {'results': [
        {'id': 1, 'title': 'Movie'}, {'id': 2, 'title': 'Movie'}]})
    assert not filters.allowed(movie('Movie'), params())


def test_global_filter_cannot_be_disabled_by_other_section():
    set_setting('hollywoodScopes', 'locations')
    assert filters.mode(params(hollywoodScope='locations')) == 'light'
    assert filters.mode(params(hollywoodScope='anime', contentTheme='anime')) == ''
    set_setting('hollywoodGlobal', 'true')
    assert filters.mode(params(hollywoodScope='anime', contentTheme='anime')) == 'light'


def test_theme_filter_applies_to_random_docs():
    set_setting('hollywoodScopes', 'docs')
    assert filters.mode(params(hollywoodScope='random', randomKind='dokus')) == 'light'


def test_menu_and_live_tv_are_not_films(monkeypatch):
    set_setting('hollywoodGlobal', 'true')
    set_setting('hollywoodMode', 'strict')
    monkeypatch.setattr(filters, '_request', lambda *args: pytest.fail('menu is not a title'))
    assert filters.allowed(cGuiElement('Actors', 'categories', 'categories'), params(mediaType='movie'))
    assert filters.allowed(params=params(mediaType='video'))


def test_citizenship_regions_and_unknowns(monkeypatch):
    set_setting('actorExcludedCountries', 'DE,US,region:asia')
    monkeypatch.setattr(persondata, 'nationalities', lambda ids: {'1': ['DE'], '2': ['KR'], '3': ['CA']})
    assert personfilters.filterPeople([{'id': value} for value in range(1, 5)]) == [{'id': 3}, {'id': 4}]


def test_nationality_uses_citizenship_and_caches(monkeypatch):
    cache = {}
    monkeypatch.setattr(persondata, '_loadCache', lambda: cache.copy())
    monkeypatch.setattr(persondata, '_saveCache', lambda data: cache.update(data))
    calls = []
    def request(query):
        calls.append(query)
        assert 'wdt:P27/wdt:P297' in query
        assert 'P495' not in query
        return {'results': {'bindings': [{'tmdb': {'value': '42'}, 'country': {'value': 'DE'}}]}}
    monkeypatch.setattr(persondata, '_request', request)
    assert persondata.nationalities([42, 'malicious']) == {'42': ['DE']}
    assert persondata.nationalities([42]) == {'42': ['DE']}
    assert len(calls) == 1


def test_person_action_validates_id_and_is_reversible(monkeypatch):
    assert not personfilters.action(params(personAction='boycott', personId='1&foo=2'))
    assert personfilters.action(params(personAction='hide', personId=42, personName='Actor'))
    assert personfilters.stored('hide') == {'42': 'Actor'}
    monkeypatch.setattr(personfilters.xbmcgui.Dialog, 'multiselect', lambda *args, **kwargs: [0])
    personfilters.manage('hide')
    assert personfilters.stored('hide') == {}


def test_blocked_hoster_does_not_resolve_or_try_more_hosters(monkeypatch):
    from resources.lib.gui.hoster import cHosterGui
    monkeypatch.setattr(filters, 'allowed', lambda **kwargs: False)
    monkeypatch.setattr(cHosterGui, '_getInfoAndResolve', lambda *args: pytest.fail('blocked title was resolved'))
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.baka/', '7', '?mediaType=movie'])
    player = cHosterGui()
    assert player.play() is False
    assert player._playbackHandled is True


def test_gui_does_not_reuse_first_movies_filter_identity(monkeypatch):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui import gui
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.baka/', '7', '?catLevel=entries'])
    monkeypatch.setattr(cGui, '_cGui__createContextMenu', lambda self, element, item, *args: item)
    monkeypatch.setattr(gui.xbmcplugin, 'addDirectoryItem', lambda *args: None)
    seen = []
    def allowed(element, itemParams):
        seen.append(itemParams.getValue('filterTmdbID'))
        itemParams.setParam('filterTmdbID', itemParams.getValue('searchTmdbID'))
        return True
    monkeypatch.setattr(filters, 'allowed', allowed)
    shared = params(catLevel='entries')
    for value in (41, 42):
        shared.setParam('searchTmdbID', value)
        cGui().addFolder(movie(), shared)
    assert seen == [False, False]
    assert not shared.getValue('filterTmdbID')
