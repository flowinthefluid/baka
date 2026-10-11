"""Source-language isolation for every supported language and theme."""
import importlib
import json
from pathlib import Path
import sys
import types

import pytest

from conftest import set_setting
from resources.lib import languages
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.pluginHandler import cPluginHandler


def english_only():
    for theme, _, _ in languages.THEMES:
        languages.applyThemeChoice(theme, ['en'], [])
    languages.applyChoice(['en'], [], 'en')


def provider(cid, catalogs, audio=('de','en'), categories=('filme','serien','dokus')):
    return {'id':cid,'name':cid,'catalog_languages':catalogs,'languages':audio,
            'categories':categories,'subtitles':('de',)}


@pytest.mark.parametrize('selected', languages.LANGUAGE_CODES)
@pytest.mark.parametrize('available', languages.LANGUAGE_CODES)
@pytest.mark.parametrize('theme', [key for key, _, _ in languages.THEMES])
def test_content_filter_for_every_language_pair_and_theme(selected, available, theme):
    for key, _, _ in languages.THEMES:
        languages.applyThemeChoice(key, [selected], [])
    languages.applyChoice([selected], [], selected)
    catalog = next(code for code in languages.LANGUAGE_CODES if code != selected)
    set_setting('langSourceCatalogFilter', 'true')  # Persisted 1.1.5 settings cannot hide hybrids.
    source = provider('catalog_fixture', [catalog], audio=(available,),
                      categories=('filme', 'serien', 'dokus', 'animes'))
    expected = available == selected
    assert languages.sourceVisible(source, theme) is expected
    assert languages.sourceVisibleAny(source) is expected
    assert languages.splitSources([source], 'alle') == (
        ([source], []) if expected else ([], [source]))
    assert languages.otherLanguagesMode('alle') == 'hide'


@pytest.mark.parametrize('selected', languages.LANGUAGE_CODES)
@pytest.mark.parametrize('theme', ['movies', 'docs'])
def test_matching_catalog_still_requires_selected_audio_or_explicit_subtitles(selected, theme):
    other = next(code for code in languages.LANGUAGE_CODES if code != selected)
    languages.applyThemeChoice(theme, [selected], [])
    source = provider('subtitle_fixture', [selected], audio=(other,))
    source['subtitles'] = (selected,)
    assert not languages.sourceVisible(source, theme)
    assert not languages.streamAllowed(other, selected, theme)
    languages.applyThemeChoice(theme, [selected], [selected])
    assert languages.sourceVisible(source, theme)
    assert languages.streamAllowed(other, selected, theme)


def test_spanish_french_and_japanese_profiles_and_multiple_selected_languages():
    languages.applyChoice(['en'], [], 'en')  # Old global preferences cannot override profiles.
    languages.applyThemeChoice('movies', ['es', 'fr'], [])
    languages.applyThemeChoice('docs', ['fr'], [])
    languages.applyThemeChoice('anime', ['ja'], [])
    sources = [provider(code, [code], audio=(code,),
                        categories=('filme', 'serien', 'dokus', 'animes'))
               for code in ('de', 'en', 'es', 'fr', 'ja')]
    assert [p['id'] for p in languages.splitSources(sources, 'movies')[0]] == ['es', 'fr']
    assert [p['id'] for p in languages.splitSources(sources, 'docs')[0]] == ['fr']
    assert [p['id'] for p in languages.splitSources(sources, 'anime')[0]] == ['ja']
    assert [p['id'] for p in languages.splitSources(sources, 'alle')[0]] == ['es', 'fr', 'ja']
    spanish_docs = provider('spanish_docs', ['es'], audio=('es',), categories=('dokus',))
    assert not languages.sourceVisibleAny(spanish_docs)


@pytest.mark.parametrize('code', languages.LANGUAGE_CODES)
def test_installation_preselects_only_each_supported_kodi_language(monkeypatch, code):
    monkeypatch.setattr(languages, 'kodiLanguage', lambda: code)
    asked = []
    monkeypatch.setattr(languages.xbmcgui.Dialog, 'multiselect',
                        lambda self, heading, labels, preselect=None:
                        asked.append(list(preselect)) or list(preselect), raising=False)
    assert languages.ensureSetup()
    index = languages.LANGUAGE_SELECTION_CODES.index(code) + 1
    assert asked == [[index], [index], [index]]
    for theme, _, _ in languages.THEMES:
        assert languages.audioLanguages(theme) == [code]
        assert languages.subtitleLanguages(theme) == []
    assert not languages.ensureSetup()
    assert len(asked) == 3


def test_hybrid_provider_visible_but_german_only_provider_hidden_in_english_profile():
    english_only()
    german = provider('german_only', ['de'], audio=('de',))
    hybrid = provider('hdfilme', ['de'])
    english = provider('english', ['en'])
    assert not languages.sourceVisible(german,'movies')
    assert not languages.sourceVisibleAny(german)
    assert languages.sourceVisible(english,'movies')
    assert languages.sourceVisible(hybrid,'movies')
    assert languages.splitSources([german,hybrid,english],'alle') == ([hybrid,english],[german])
    assert languages.streamAllowed('en', theme='movies')
    assert not languages.streamAllowed('de', theme='movies')


def test_optional_german_original_subtitles_and_themes_remain_independent():
    english_only()
    anime=provider('anime4',['de'],audio=('de','ja'),categories=('animes',))
    assert not languages.sourceVisibleAny(anime)
    languages.applyThemeChoice('anime',['en'],['de'])
    assert languages.sourceVisibleAny(anime)
    assert languages.streamAllowed('ja','de','anime')
    assert not languages.streamAllowed('de','de','anime')
    assert not languages.sourceVisible(provider('german_only',['de'],audio=('de',)),'movies')
    assert languages.sourceTheme(anime,'alle') == 'anime'
    assert languages.sourceTheme(provider('docs',['en'],categories=('dokus',)),'alle') == 'docs'


def test_all_folder_uses_profiles_without_reintroducing_excluded_languages(monkeypatch):
    english_only()
    monkeypatch.setitem(sys.modules,'resolveurl',types.ModuleType('resolveurl'))
    main=importlib.import_module('baka')
    german=provider('german_only',['de'],audio=('de',))
    hybrid=provider('hdfilme',['de'])
    english=provider('english',['en'])
    monkeypatch.setattr(main.cPluginHandler,'getPluginsForContentCategory',lambda self,cat:[german,hybrid,english])
    added=[]
    monkeypatch.setattr(main.cGui,'addFolder',lambda self,el,params=None,*args:added.append((el.getTitle(),el.getFunction())))
    monkeypatch.setattr(main.cGui,'setEndOfDirectory',lambda *args:None)
    params=ParameterHandler()
    params.setParam('category','alle')
    main.showContentCategory(params)
    assert added == [('hdfilme','load'),('english','load')]
    assert languages.otherLanguagesMode('alle') == 'hide'
    assert languages.otherLanguagesMode('movies') == 'hide'
    added.clear()
    main.showOtherLanguages(params)
    assert not added


def test_english_installation_has_no_automatic_german_option(monkeypatch):
    monkeypatch.setattr(languages,'kodiLanguage',lambda:'en')
    asked=[]
    monkeypatch.setattr(languages.xbmcgui.Dialog,'multiselect',lambda self,heading,labels,preselect=None:
                        asked.append(list(preselect)) or list(preselect),raising=False)
    assert languages.ensureSetup()
    assert asked == [[1],[1],[1]]
    for theme,_,_ in languages.THEMES:
        assert languages.audioLanguages(theme) == ['en']
        assert languages.subtitleLanguages(theme) == []
    assert languages.subtitleLanguages('') == []
    assert not languages.sourceVisibleAny(provider('german_only',['de'],audio=('de',)))
    assert languages.sourceVisibleAny(provider('hdfilme',['de']))
    assert not languages.ensureSetup()  # No repeat prompt on updates.


@pytest.mark.parametrize('site',['anime4','animeloads','animetoast','animestream','aniworld','kayoanime','proxer'])
def test_old_anime_links_keep_anime_profile(monkeypatch,site):
    languages.applyThemeChoice('movies',['en'],[])
    languages.applyThemeChoice('anime',['de'],[])
    monkeypatch.setattr(sys,'argv',['plugin://plugin.video.baka/','1','?site='+site])
    assert languages.currentTheme() == 'anime'
    assert not languages.streamAllowed('en')
    assert languages.streamAllowed('de')


def test_old_plugin_cache_gets_catalog_language_even_with_newer_timestamp(tmp_path,monkeypatch):
    name='fixture_catalog_provider'
    site=tmp_path/(name+'.py')
    site.write_text("SITE_NAME='Fixture'\nSITE_LANGUAGES=('de','en')\nSITE_CATALOG_LANGUAGES=('de',)\nCONTENT_CATEGORIES=('filme',)\n",encoding='utf-8')
    monkeypatch.syspath_prepend(str(tmp_path))
    handler=cPluginHandler()
    handler.defaultFolder=str(tmp_path)
    handler.profilePath=str(tmp_path)
    handler.pluginDBFile=str(tmp_path/'pluginDB')
    Path(handler.pluginDBFile).write_text(json.dumps({name:{'name':'Old','modified':site.stat().st_mtime+100,
        'languages':['de','en'],'categories':['filme']}}),encoding='utf-8')
    set_setting('plugin_'+name,'true')
    available=handler.getAvailablePlugins()
    assert available[0]['catalog_languages'] == ['de']
    english_only()
    assert languages.sourceVisibleAny(available[0])


@pytest.mark.parametrize('selected', languages.LANGUAGE_CODES)
def test_hybrid_sources_keep_only_selected_content_for_every_language(selected):
    other = next(code for code in languages.LANGUAGE_CODES if code != selected)
    for theme, _, _ in languages.THEMES:
        languages.applyThemeChoice(theme, [selected], [])
        source = provider('hybrid', [other], audio=(other, selected))
        assert languages.sourceVisible(source, theme)
        assert languages.streamAllowed(selected, theme=theme)
        assert not languages.streamAllowed(other, theme=theme)


def test_actual_hdfilme_listing_filters_german_films_without_hiding_source(monkeypatch):
    from sites import hdfilme
    english_only()
    set_setting('langSourceCatalogFilter', 'true')
    assert languages.sourceVisible(provider('hdfilme', ['de'], hdfilme.SITE_LANGUAGES), 'movies')
    html = ''.join('<div class="box-product"><h3><a href="https://fixture/'+str(i)+'">'+title+
                   '</a></h3><li><p>2025 </p></li>'
                   for i, title in enumerate(('Deutscher Film', 'Deutscher Titel *English*', 'English title')))
    monkeypatch.setattr(hdfilme.cRequestHandler, 'request', lambda self: html)
    shown = []
    gui = types.SimpleNamespace(addFolder=lambda element, *args: shown.append(element.getTitle()))
    hdfilme.showEntries('https://fixture/list', sGui=gui)
    assert shown == ['Deutscher Titel (2025)']
