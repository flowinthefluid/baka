# -*- coding: utf-8 -*-
"""Sprachen & Regionen: Quellen, Streams, Menues und Einstellungen."""

import importlib
import re
import shutil
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path

from conftest import set_setting
from resources.lib import languages

ROOT = Path(__file__).resolve().parents[1]


def _main(monkeypatch):
    monkeypatch.setitem(sys.modules, 'resolveurl', types.ModuleType('resolveurl'))
    return importlib.import_module('baka')


def _enable(audio, subs=()):
    for code in languages.LANGUAGE_CODES:
        set_setting(languages.AUDIO_SETTING % code, 'true' if code in audio else 'false')
        set_setting(languages.SUBS_SETTING % code, 'true' if code in subs else 'false')


# --- Quellen und Streams ---------------------------------------------------

def test_default_is_german_audio_and_german_subtitles():
    assert languages.audioLanguages() == ['de']
    assert languages.subtitleLanguages() == ['de']


def test_sources_are_visible_by_audio_or_subtitles():
    german = {'id': 'megakino'}
    english = {'id': 'kayoanime', 'languages': ('ja', 'en'), 'subtitles': ('en',)}
    subbed = {'id': 'proxer', 'languages': ('ja',), 'subtitles': ('de', 'en')}
    neutral = {'id': 'weathercams', 'languages': ()}
    mine, others = languages.splitSources([german, english, subbed, neutral])
    assert mine == [german, subbed, neutral] and others == [english]
    _enable(['en'])
    assert languages.sourceVisible(english) and not languages.sourceVisible(german)
    assert languages.sourceMainLanguage(english) == 'ja'


def test_streams_are_filtered_labelled_and_ranked_by_preference():
    _enable(['de', 'en'], ['de'])
    set_setting(languages.PREFERRED_SETTING, 'en')
    assert languages.audioLanguages() == ['en', 'de']
    assert languages.streamAllowed('de') and languages.streamAllowed('ja', 'de')
    assert not languages.streamAllowed('ja', 'en') and languages.streamAllowed('')
    assert languages.streamLabel('ja', 'de') == '(JA) Sub: (DE)' and languages.streamLabel('de') == '(DE)'
    ordered = sorted([('ja', 'de'), ('de', ''), ('', ''), ('en', '')], key=lambda pair: languages.streamRank(*pair))
    assert ordered == [('en', ''), ('de', ''), ('ja', 'de'), ('', '')]
    hoster = languages.tagStream({'name': 'VOE'}, 'ja', 'de')
    assert hoster == {'name': 'VOE', 'audio': 'ja', 'subs': 'de', 'languageCode': '(JA) Sub: (DE)'}


def test_site_values_follow_a_single_chosen_language():
    choices = {'de': '2', 'en': '3'}
    assert languages.siteValue(choices, 'all') == '2'
    _enable(['de', 'en'])
    assert languages.siteValue(choices, 'all') == 'all'
    _enable(['en', 'ja'])
    assert languages.siteValue(choices, 'all') == '3'


# --- Einrichtung -----------------------------------------------------------

def test_new_users_are_asked_once_and_service_never_asks(monkeypatch):
    assert not languages.ensureSetup(interactive=False)
    monkeypatch.setattr(languages, 'kodiLanguage', lambda: 'en')
    asked = []
    responses = iter(([1, 2], [2], [2, 16]))
    monkeypatch.setattr(languages.xbmcgui.Dialog, 'multiselect', lambda self, heading, labels, preselect=None:
                        asked.append(preselect) or next(responses), raising=False)
    assert languages.ensureSetup(interactive=True)
    assert asked == [[1, 16], [1, 16], [1, 16]]
    assert languages.audioLanguages() == ['en', 'de'] and languages.preferredLanguage() == 'en'
    assert languages.audioLanguages('anime') == ['de']
    from resources.lib.config import cConfig
    assert cConfig().getSetting('tmdb_lang') == 'en'
    assert languages.countries() == ['de', 'at', 'ch', 'gb', 'us', 'ie', 'ca', 'au']
    assert not languages.ensureSetup(interactive=True)


def test_countries_editor_and_visibility(monkeypatch):
    assert languages.countryVisible('jp')  # nichts gewaehlt = alle Laender
    monkeypatch.setattr(languages.xbmcgui.Dialog, 'multiselect',
                        lambda *args, **kwargs: [0, 2], raising=False)
    languages.editCountries()
    assert languages.countries() == ['de', 'ch']
    assert languages.countryVisible('CH') and not languages.countryVisible('at')


# --- Menues und Suche ------------------------------------------------------

def _category(monkeypatch, main, plugins):
    monkeypatch.setattr(main.cPluginHandler, 'getPluginsForContentCategory', lambda self, category: plugins)
    added = []
    monkeypatch.setattr(main.cGui, 'addFolder', lambda self, element, params=None, *args: added.append(
        (element.getTitle(), element.getFunction(), dict(params.getAllParameters()) if params else {})))
    monkeypatch.setattr(main.cGui, 'setEndOfDirectory', lambda self, success=True: None)
    return added


def test_content_folders_list_own_languages_and_collect_the_rest(monkeypatch):
    from resources.lib.handler.ParameterHandler import ParameterHandler

    main = _main(monkeypatch)
    plugins = [{'id': 'megakino', 'name': 'Megakino'},
               {'id': 'kayoanime', 'name': 'KayoAnime', 'languages': ('ja', 'en'), 'subtitles': ('en',)},
               {'id': 'hindi', 'name': 'Hindi', 'languages': ('hi',)}]
    added = _category(monkeypatch, main, plugins)
    params = ParameterHandler()
    params.setParam('category', 'animes')
    main.showContentCategory(params)
    functions = [function for title, function, extra in added]
    assert functions == ['randomMovies', 'load', 'showOtherLanguages']
    assert added[1][0] == 'Megakino' and added[2][2]['category'] == 'animes'

    added.clear()
    other = ParameterHandler()
    other.setParam('category', 'animes')
    main.showOtherLanguages(other)
    assert [extra.get('otherLanguage') for title, function, extra in added] == ['hi', 'ja']
    added.clear()
    other.setParam('otherLanguage', 'hi')
    main.showOtherLanguages(other)
    assert [title for title, function, extra in added] == ['Hindi']

    added.clear()
    set_setting(languages.OTHER_MODE_SETTING, 'hide')
    main.showContentCategory(params)
    assert [function for title, function, extra in added] == ['randomMovies', 'load']


def test_global_search_only_queries_sources_in_my_languages(monkeypatch):
    main = _main(monkeypatch)
    plugins = [{'id': 'megakino', 'name': 'Megakino', 'globalsearch': True},
               {'id': 'kayoanime', 'name': 'KayoAnime', 'globalsearch': True, 'languages': ('ja', 'en'),
                'subtitles': ('en',)}]
    monkeypatch.setattr(main.cPluginHandler, 'getAvailablePlugins', lambda self: plugins)
    searched = []
    monkeypatch.setattr(main, '_runPluginSearches', lambda found, *args: searched.append(
        [plugin['id'] for plugin in found]) or False)
    monkeypatch.setattr(main.xbmcgui, 'DialogProgress', lambda: types.SimpleNamespace(
        create=lambda *args: None, close=lambda: None), raising=False)
    monkeypatch.setattr(main.cGui, 'setEndOfDirectory', lambda self, success=True: None)
    main._collectGlobalSearchResults('Naruto', lambda plugin: True)
    assert searched == [['megakino']]


def test_hosters_are_sorted_by_language_preference():
    _enable(['de', 'en'], ['de'])
    hosters = [{'name': 'A', 'audio': 'ja', 'subs': 'de'}, {'name': 'B', 'audio': 'en', 'subs': ''},
               {'name': 'C', 'audio': 'de', 'subs': ''}]
    ranked = sorted(enumerate(hosters), key=lambda entry: (
        languages.streamRank(entry[1]['audio'], entry[1]['subs']), entry[0]))
    assert [hoster['name'] for index, hoster in ranked] == ['C', 'B', 'A']
    source = (ROOT / 'resources' / 'lib' / 'gui' / 'hoster.py').read_text(encoding='utf-8')
    assert 'languages.streamRank(' in source


# --- Kategorien und Regionales ---------------------------------------------

def test_world_cinema_entries_are_queries_and_can_be_hidden(monkeypatch):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    assert all(key in categories.PRESET_QUERIES for stringId, key in categories.WORLD_CINEMA)
    folders = []
    monkeypatch.setattr(categories, '_addFolder', lambda title, function, params, *args: folders.append(
        params.getValue('catPreset')))
    monkeypatch.setattr(categories.cGui, 'setEndOfDirectory', lambda self, *args: None)
    set_setting(categories.WORLD_CINEMA_HIDDEN_SETTING, 'world_bollywood,world_telenovelas')
    categories._outsideHollywood(ParameterHandler())
    assert 'world_bollywood' not in folders and 'world_kdrama' in folders
    assert folders[-2:] == ['outside_locations', 'no_hollywood_companies']
    monkeypatch.setattr(importlib.import_module('xbmcgui'), 'Dialog', lambda: types.SimpleNamespace(
        multiselect=lambda *args, **kwargs: [0]), raising=False)
    categories.editWorldCinema()
    hidden = categories._worldCinemaHidden()
    assert 'world_bollywood' not in hidden and len(hidden) == len(categories.WORLD_CINEMA) - 1


def test_fixed_german_category_names_are_translated(real_strings):
    from resources.lib import categories

    assert categories._t('Uebernatuerliches') == 'Übernatürliches'
    assert categories._t('Pixar') == 'Pixar'
    english = (ROOT / 'resources' / 'language' / 'resource.language.en_gb' / 'strings.po').read_text(encoding='utf-8')
    german = (ROOT / 'resources' / 'language' / 'resource.language.de_de' / 'strings.po').read_text(encoding='utf-8')
    for stringId in list(categories.LABEL_IDS.values()) + [32073, 32078, 32093, 32094]:
        assert 'msgctxt "#%d"' % stringId in english and 'msgctxt "#%d"' % stringId in german


def test_mediatheken_get_a_country_level_only_for_several_countries(monkeypatch, real_strings):
    from resources.lib import categories
    from resources.lib.handler.ParameterHandler import ParameterHandler

    added = []

    class Gui(object):
        def addFolder(self, element, params=None, *args, **kwargs):
            added.append((element.getTitle(), element.getFunction(),
                          params.getValue('catCountry') if params else None))

        def setEndOfDirectory(self, *args):
            pass

        def showInfo(self, *args):
            added.append(('info', None, None))

    monkeypatch.setattr(categories, 'cGui', Gui)
    set_setting(languages.COUNTRIES_SETTING, 'de,at')
    params = ParameterHandler()
    categories._mediatheken(params)
    assert [entry[2] for entry in added] == ['de', 'at']
    added.clear()
    params.setParam('catCountry', 'at')
    categories._mediatheken(params)
    titles = [entry[0] for entry in added]
    assert any(title.startswith('ORF') for title in titles) and not any(title.startswith('SRF') for title in titles)
    assert not any(title.startswith('ZDF') for title in titles)
    added.clear()
    set_setting(languages.COUNTRIES_SETTING, 'ch')
    categories._mediatheken(ParameterHandler())
    titles = [entry[0] for entry in added]
    assert any(title.startswith('SRF') for title in titles) and 'ARD Mediathek' not in titles


def test_live_tv_follows_my_countries_but_webcams_stay_worldwide():
    from resources.lib import contentgate

    tv = {'id': 'gxs:tv:at:orf1', 'name': 'ORF 1', 'section': 'tv', 'country': 'at', 'language': ['de'],
          'genre': ['news'], 'nsfw': False, 'publisher': 'orf', 'logo': '', 'epg_id': '',
          'sources': [{'source_id': 's1', 'url': 'https://x/master.m3u8', 'protocol': 'hls',
                       'quality': 'hd', 'official': True, 'reliability': 'high', 'region': 'at',
                       'headers': {}}]}
    assert contentgate.is_channel_visible(tv)  # nichts gewaehlt = alle Laender
    set_setting(languages.COUNTRIES_SETTING, 'de')
    assert not contentgate.is_channel_visible(tv)
    assert contentgate.is_channel_visible(dict(tv, country='de'))
    assert contentgate.is_channel_visible(dict(tv, country='int'))
    assert contentgate.is_channel_visible(dict(tv, section='webcam', country='us'))


# --- Einstellungen und Quellen ---------------------------------------------

def test_language_settings_page_matches_the_language_list():
    root = ET.parse(ROOT / 'resources' / 'settings.xml').getroot()
    page = root.find(".//category[@id='languages']")
    ids = {setting.get('id') for setting in page.iter('setting')}
    for code in languages.LANGUAGE_CODES:
        assert languages.AUDIO_SETTING % code in ids and languages.SUBS_SETTING % code in ids
    assert {'langAudioPreferred', 'langOtherMode', 'regionCountries', 'tmdb_lang', 'langSetupDone'} <= ids
    assert root.find(".//setting[@id='prefLanguage']") is None
    options = [option.text for option in root.findall(".//setting[@id='langAudioPreferred']//option")]
    assert '' not in options and None not in options  # leere Optionen lassen Kodi abstuerzen


def test_source_settings_follow_their_languages(tmp_path, monkeypatch):
    from tools import register_site

    assert register_site.LANGUAGE_TOGGLES == languages.LANGUAGE_CODES
    copy = tmp_path / 'settings.xml'
    shutil.copy(ROOT / 'resources' / 'settings.xml', copy)
    monkeypatch.setattr(register_site, 'SETTINGS', str(copy))
    assert not register_site.syncLanguageVisibility()  # bereits abgeglichen
    root = ET.parse(copy).getroot()
    kinox = ET.tostring(root.find(".//group[@id='plugin_kinox']"), encoding='unicode')
    assert 'langAudio_hi' in kinox and 'langSubs_en' in kinox
    megakino = root.find(".//setting[@id='plugin_megakino']//dependency[@setting='langAudio_de']")
    assert megakino is not None
    assert register_site.languageDependency((), (), '') == ''  # sprachunabhaengige Quellen


def test_sites_no_longer_read_the_old_language_setting():
    for path in (ROOT / 'sites').glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert re.search(r"^SITE_LANGUAGES = ", text, re.M), path.name
        assert 'prefLanguage' not in text, path.name


def test_kinox_hides_languages_nobody_chose():
    from sites import kinox

    cookie = getattr(kinox, '__getPreferredLanguage')()
    hidden = cookie[len('ListNeededLanguage='):-1].split('%2C')
    assert '1' not in hidden and '15' not in hidden and '2' in hidden and cookie.endswith(';')


def test_language_codes_are_shareable_in_profiles():
    from resources.lib import backup

    allowed = backup._shareSettingIds()
    assert allowed['regionCountries'] == ('codes', []) and allowed['langAudio_en'][0] == 'boolean'
    assert backup._validShareValue('de,at,ch', allowed['regionCountries'])
    assert not backup._validShareValue('de;rm -rf', allowed['regionCountries'])
    assert backup._validShareValue('epicFavorites,livestreams,settings', allowed['mainMenuOrder'])
