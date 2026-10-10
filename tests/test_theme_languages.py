"""Independent theme choices survive updates and reach provider/hoster routes."""

import sys

from conftest import set_setting
from resources.lib import languages
from resources.lib.config import cConfig
from resources.lib.handler.ParameterHandler import ParameterHandler
from test_languages import _main


def test_movie_english_does_not_enable_anime_english(monkeypatch):
    languages.applyThemeChoice('movies', ['de', 'en'], [])
    languages.applyThemeChoice('docs', ['de'], [])
    languages.applyThemeChoice('anime', ['de'], ['de'])
    assert languages.streamAllowed('en', theme='movies')
    assert not languages.streamAllowed('en', theme='docs')
    assert not languages.streamAllowed('en', theme='anime')
    assert not languages.streamAllowed('en', 'de', theme='anime')
    assert languages.streamAllowed('de', theme='anime')
    assert languages.streamAllowed('ja', 'de', theme='anime')
    assert not languages.streamAllowed('ja', 'en', theme='anime')
    assert not languages.sourceVisible({'languages': ['en'], 'subtitles': ['de']}, 'anime')
    assert languages.sourceVisible({'languages': ['ja'], 'subtitles': ['de']}, 'anime')
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?site=aniworld'])
    assert languages.currentTheme() == 'anime' and not languages.streamAllowed('en')
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?site=mixed&contentTheme=movies'])
    assert languages.currentTheme() == 'movies' and languages.streamAllowed('en')


def test_wizard_has_requested_language_order_and_only_three_questions_once(monkeypatch, real_strings):
    calls = []
    responses = iter([[1, 2], [0], [2, len(languages.LANGUAGE_SELECTION_CODES) + 1]])

    class Dialog:
        def multiselect(self, title, labels, preselect):
            calls.append((title, labels))
            return next(responses)

    monkeypatch.setattr(languages.xbmcgui, 'Dialog', Dialog)
    assert languages.ensureSetup()
    assert len(calls) == 3
    assert all(labels[:3] == ['Nicht anzeigen', 'Englisch', 'Deutsch'] for title, labels in calls)
    assert not languages.themeEnabled('dokus')
    assert languages.audioLanguages('movies') == ['de', 'en']
    assert languages.audioLanguages('anime') == ['de']
    assert languages.subtitleLanguages('anime') == ['de']
    assert cConfig().getSetting('langSetupDone') == 'true'
    # A fresh module or an addon version change does not reset the persisted flag.
    assert not languages.ensureSetup()
    assert len(calls) == 3


def test_existing_install_keeps_choices_and_does_not_get_upgrade_wizard(monkeypatch):
    set_setting('langSetupDone', 'true')
    set_setting('langAudio_en', 'true')
    set_setting('langAudio_de', 'false')
    monkeypatch.setattr(languages, 'chooseThemeLanguages', lambda **kwargs: (_ for _ in ()).throw(AssertionError('upgrade prompt')))
    assert not languages.ensureSetup()
    assert languages.audioLanguages('movies') == ['en']
    assert languages.audioLanguages('anime') == ['en']  # unchanged until user edits this profile


def test_cancel_manual_wizard_stops_without_partial_writes(monkeypatch):
    languages.applyThemeChoice('movies', ['en'], [])
    calls = []

    class Dialog:
        def multiselect(self, *args, **kwargs):
            calls.append(args)
            return [2] if len(calls) == 1 else None

    monkeypatch.setattr(languages.xbmcgui, 'Dialog', Dialog)
    assert not languages.chooseThemeLanguages()
    assert len(calls) == 2 and languages.audioLanguages('movies') == ['en']


def test_disabled_theme_hides_provider_and_direct_category(monkeypatch):
    main = _main(monkeypatch)
    languages.applyThemeChoice('anime', [], [], False)
    assert not languages.sourceVisible({'languages': []}, 'anime')
    assert not languages.sourceVisibleAny({'categories': ['animes'], 'languages': ['de']})
    calls = []

    class Gui:
        def showInfo(self):
            calls.append('info')

        def setEndOfDirectory(self):
            calls.append('end')

        def addFolder(self, *args):
            raise AssertionError('disabled theme is still listed')

    class Handler:
        def getPluginsForContentCategory(self, category):
            return [{'id': 'aniworld', 'name': 'AniWorld', 'languages': ['de']}]

    monkeypatch.setattr(main, 'cGui', Gui)
    monkeypatch.setattr(main, 'cPluginHandler', Handler)
    params = ParameterHandler()
    params.setParam('category', 'animes')
    main.showContentCategory(params)
    assert calls == ['info', 'end']


def test_provider_folder_carries_theme_into_next_kodi_invocation(monkeypatch):
    main = _main(monkeypatch)
    rows = []

    class Gui:
        def addFolder(self, element, params):
            rows.append(params.getAllParameters().copy())

    main._addPluginFolders(Gui(), [{'id': 'mixed', 'name': 'Mixed'}], 'dokus')
    assert rows[0]['contentTheme'] == 'docs'
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?site=mixed&contentTheme=docs'])
    child = ParameterHandler()
    child.setParam('page', '2')
    assert child.getValue('contentTheme') == 'docs' and languages.currentTheme() == 'docs'


def test_actual_hoster_candidates_use_anime_profile(monkeypatch):
    import types
    from resources.lib.gui.hoster import cHosterGui
    monkeypatch.setitem(sys.modules, 'resolveurl', types.ModuleType('resolveurl'))
    languages.applyThemeChoice('anime', ['de'], ['de'])
    monkeypatch.setattr(sys, 'argv', ['plugin', '1', '?site=aniworld&contentTheme=anime'])
    candidates = [languages.tagStream({'name': 'VOE', 'resolveable': True,
                                      'link': 'https://example.com/' + audio}, audio, subs)
                  for audio, subs in [('en', ''), ('de', ''), ('ja', 'de'), ('en', 'de')]]
    result = cHosterGui()._cHosterGui__getPriorities(candidates)
    assert [(c['audio'], c['subs']) for c in result] == [('de', ''), ('ja', 'de')]
