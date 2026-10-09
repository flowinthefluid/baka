# -*- coding: utf-8 -*-
"""Seitenanzeige "Seite X von Y" und Sprung zu einer beliebigen Seite."""

import json
import sys
import types
from urllib.parse import parse_qsl, urlsplit

from resources.lib import paging


def test_page_number_is_found_in_parameters_and_urls():
    jump = paging.describe({'page': '2'}, {'page': '3'}, 9)
    assert (jump['key'], jump['page'], jump['total']) == ('page', 2, 9)
    jump = paging.describe({'sUrl': 'https://x/filme/page/4/'}, {'sUrl': 'https://x/filme/page/5/'})
    assert jump['template'] == 'https://x/filme/page/{page}/' and jump['page'] == 4 and jump['total'] == 0
    jump = paging.describe({'sUrl': 'https://x/filme/'}, {'sUrl': 'https://x/filme/page/2/'})
    assert jump['page'] == 1 and jump['first'] == 'https://x/filme/'
    assert jump['template'] == 'https://x/filme/page/{page}/'
    jump = paging.describe({'sUrl': 'https://x/?s=foo'}, {'sUrl': 'https://x/?s=foo&page=2'})
    assert jump['template'] == 'https://x/?s=foo&page={page}'


def test_titles_with_numbers_are_never_taken_for_pages():
    jump = paging.describe({}, {'searchTitle': 'Fast 2', 'searchTmdbID': '584', 'page': '2'})
    assert jump['key'] == 'page' and jump['page'] == 1
    assert paging.describe({}, {'searchTitle': 'Fast 2'}) is None
    assert paging.describe({'sUrl': 'https://x/a'}, {'sUrl': 'https://x/a'}) is None
    assert paging.describe({'sUrl': 'https://x/genre/7'}, {'sUrl': 'https://x/genre/9'}) is None


def test_jump_links_open_the_chosen_page():
    jump = paging.describe({'sUrl': 'https://x/filme/'}, {'sUrl': 'https://x/filme/page/2/'}, 40)
    data = json.loads(paging.jumpParams(jump, 'megakino', 'showEntries',
                                        {'sUrl': 'https://x/filme/page/2/', 'site': 'old', 'trumb': ''}))
    url = paging.targetUrl(data, 17)
    query = dict(parse_qsl(urlsplit(url).query))
    assert url.startswith('plugin://plugin.video.baka/?')
    assert query == {'site': 'megakino', 'function': 'showEntries', 'sUrl': 'https://x/filme/page/17/'}
    assert dict(parse_qsl(urlsplit(paging.targetUrl(data, 1)).query))['sUrl'] == 'https://x/filme/'
    assert paging.targetUrl(data, 41) is None and paging.targetUrl(data, 0) is None
    assert paging.targetUrl(dict(data, site='../../evil'), 3) is None


def test_page_label_sits_between_last_entry_and_next_page(monkeypatch):
    from resources.lib.gui import gui as gui_module
    from resources.lib.handler.ParameterHandler import ParameterHandler

    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.baka/', '1',
                                      '?site=megakino&function=showEntries&sUrl=https%3A%2F%2Fx%2Ffilme%2Fpage%2F3%2F'])
    added = []
    monkeypatch.setattr(gui_module.cGui, 'addFolder', lambda self, element, params='', *args, **kwargs: added.append(
        (element.getFunction(), element.getTitle())))
    params = ParameterHandler()
    params.setParam('sUrl', 'https://x/filme/page/4/')
    oGui = gui_module.cGui()
    oGui.addNextPage('megakino', 'showEntries', params, 12)
    assert [function for function, title in added] == ['jumpToPage', 'showEntries']
    assert added[0][1] == '[I]Seite 3 von 12[/I]'

    added.clear()
    oGui.globalSearch = True
    oGui.addNextPage('megakino', 'showEntries', params)
    assert [function for function, title in added] == ['showEntries']


def test_jump_dialog_updates_the_container(monkeypatch):
    import xbmc
    import xbmcgui
    import xbmcplugin
    from resources.lib.handler.ParameterHandler import ParameterHandler

    jump = paging.describe({'page': '1'}, {'page': '2', 'catLevel': 'entries'}, 500)
    params = ParameterHandler()
    params.setParam('pageJump', paging.jumpParams(jump, 'categories', 'categories', {'page': '2', 'catLevel': 'entries'}))
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.baka/', '3', ''])
    calls = []
    monkeypatch.setattr(xbmc, 'executebuiltin', calls.append)
    monkeypatch.setattr(xbmcplugin, 'endOfDirectory', lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(xbmcgui, 'Dialog', lambda: types.SimpleNamespace(
        numeric=lambda *args: '120', notification=lambda *args: calls.append('notification')), raising=False)
    paging.jump(params)
    assert len(calls) == 1 and calls[0].startswith('Container.Update(plugin://plugin.video.baka/?')
    query = dict(parse_qsl(urlsplit(calls[0][len('Container.Update('):-1]).query))
    assert query == {'site': 'categories', 'function': 'categories', 'page': '120', 'catLevel': 'entries'}

    calls.clear()
    monkeypatch.setattr(xbmcgui, 'Dialog', lambda: types.SimpleNamespace(
        numeric=lambda *args: '900', notification=lambda *args: calls.append('notification')), raising=False)
    paging.jump(params)
    assert calls == ['notification']
