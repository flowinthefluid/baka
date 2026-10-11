"""English-only providers, opt-in subtitles, per-theme union and cache upgrade."""
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


def test_german_provider_with_english_films_hidden_in_english_profile():
    english_only()
    german = provider('hdfilme', ['de'])
    english = provider('english', ['en'])
    assert not languages.sourceVisible(german,'movies')
    assert not languages.sourceVisibleAny(german)
    assert languages.sourceVisible(english,'movies')
    assert languages.splitSources([german,english],'alle') == ([english],[german])
    set_setting('langSourceCatalogFilter','false')
    assert languages.sourceVisible(german,'movies')  # Explicit alternative: matching audio only.


def test_optional_german_original_subtitles_and_themes_remain_independent():
    english_only()
    anime=provider('anime4',['de'],audio=('de','ja'),categories=('animes',))
    assert not languages.sourceVisibleAny(anime)
    languages.applyThemeChoice('anime',['en'],['de'])
    assert languages.sourceVisibleAny(anime)
    assert languages.streamAllowed('ja','de','anime')
    assert not languages.streamAllowed('de','de','anime')
    assert not languages.sourceVisible(provider('hdfilme',['de']),'movies')
    assert languages.sourceTheme(anime,'alle') == 'anime'
    assert languages.sourceTheme(provider('docs',['en'],categories=('dokus',)),'alle') == 'docs'


def test_all_folder_uses_profiles_without_reintroducing_excluded_languages(monkeypatch):
    english_only()
    main=importlib.import_module('baka')
    monkeypatch.setitem(sys.modules,'resolveurl',types.ModuleType('resolveurl'))
    german=provider('hdfilme',['de'])
    english=provider('english',['en'])
    monkeypatch.setattr(main.cPluginHandler,'getPluginsForContentCategory',lambda self,cat:[german,english])
    added=[]
    monkeypatch.setattr(main.cGui,'addFolder',lambda self,el,params=None,*args:added.append((el.getTitle(),el.getFunction())))
    monkeypatch.setattr(main.cGui,'setEndOfDirectory',lambda *args:None)
    params=ParameterHandler()
    params.setParam('category','alle')
    main.showContentCategory(params)
    assert added == [('english','load')]
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
    assert not languages.sourceVisibleAny(provider('hdfilme',['de']))
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
    assert not languages.sourceVisibleAny(available[0])
