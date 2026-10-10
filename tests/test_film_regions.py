import sys
from conftest import set_setting
from resources.lib import filmregions, categories
from resources.lib.handler.ParameterHandler import ParameterHandler


def test_country_queries_honor_zero_votes_and_paging(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['', '1', '?catPreset=region:central_america&page=3'])
    path, query, page = categories._buildQuery(ParameterHandler())
    assert path == 'discover/movie' and page == 3
    assert 'vote_count' not in query
    assert all(code in query for code in ('BZ', 'CR', 'SV', 'GT', 'HN', 'NI', 'PA', 'MX'))
    set_setting('categoryMinVotes', '10')
    assert 'vote_count.gte=10' in categories._buildQuery(ParameterHandler())[1]


def test_legacy_country_link_has_no_hidden_fifty_vote_threshold(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['', '1', '?catPreset=location_central_america'])
    assert 'vote_count.gte=50' not in categories._buildQuery(ParameterHandler())[1]


def test_invalid_or_empty_region_query_is_rejected():
    assert filmregions.query('country:DE&foo=1') is None
    assert filmregions.query('region:missing') is None
    set_setting('filmLocationCountries', '-')
    assert filmregions.query('region:asia') is None
    assert not filmregions.selected()


def test_main_menu_is_compact_and_region_menu_is_optional(monkeypatch):
    from resources.lib.gui.gui import cGui
    listed = []
    monkeypatch.setattr(cGui, 'addFolder', lambda self, element, params: listed.append(dict(params.getAllParameters())))
    monkeypatch.setattr(cGui, 'setEndOfDirectory', lambda *args: None)
    monkeypatch.setattr(sys, 'argv', ['', '1', '?'])
    filmregions.menu(ParameterHandler())
    countries = [row['catPreset'][8:] for row in listed if row.get('catPreset', '').startswith('country:')]
    assert countries == list(filmregions.DIRECT)
    assert len(listed) < 20
    assert any(row.get('filmRegion') == 'central_america' for row in listed)
    listed.clear()
    set_setting('filmLocationIndividualCountries', 'false')
    params = ParameterHandler()
    params.setParam('filmRegion', 'asia')
    filmregions.menu(params)
    assert len(listed) == 1 and listed[0]['catPreset'] == 'region:asia'
