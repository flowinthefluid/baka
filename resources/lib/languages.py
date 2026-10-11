# -*- coding: utf-8 -*-
# Python 3
"""Sprachen und Regionen: welche Quellen und Streams sichtbar sind.

Drei Achsen bleiben getrennt: die Inhaltsart bestimmt das Menue (Filme,
Serien ...), die Sprache ist ein Filter und das Land gibt es nur dort als
Ebene, wo es selbst der Inhalt ist (Mediatheken, Live-TV).

Quellen geben ihre Sprachen als Modul-Attribute an::

    SITE_LANGUAGES = ('de', 'en')   # Tonspuren; () = sprachunabhaengig
    SITE_SUBTITLES = ('de',)        # Untertitel, z.B. Japanisch mit DE-UT
    SITE_REGIONS = ('de', 'at')     # nur bei regional gebundenen Quellen
    SITE_CATALOG_LANGUAGES = ('de',)  # Sprache des Anbieterkatalogs, getrennt vom Ton

Fehlt SITE_LANGUAGES, gilt die Quelle als deutsch - so waren alle Quellen
vor der Internationalisierung.
"""

import xbmc
import xbmcgui

from resources.lib.config import cConfig

# Sprachen mit eigenem Schalter (ISO 639-1) und ihrem Anzeigenamen.
LANGUAGES = (
    ('de', 32000), ('en', 32001), ('ja', 32002), ('es', 32003), ('fr', 32004),
    ('it', 32005), ('tr', 32006), ('hi', 32007), ('ko', 32008), ('pt', 32009),
    ('pl', 32010), ('ru', 32011), ('ar', 32012), ('nl', 32013), ('zh', 32014),
)
LANGUAGE_CODES = tuple(code for code, stringId in LANGUAGES)
LANGUAGE_SELECTION_CODES = ('en', 'de') + tuple(code for code in LANGUAGE_CODES if code not in ('en', 'de'))

# Laender (ISO 3166-1 alpha-2) fuer Mediatheken, Live-TV und Vorschlaege.
COUNTRIES = (
    ('de', 32020), ('at', 32021), ('ch', 32022), ('gb', 32023), ('us', 32024),
    ('ie', 32025), ('fr', 32026), ('be', 32027), ('it', 32028), ('es', 32029),
    ('pt', 32030), ('br', 32031), ('tr', 32032), ('in', 32033), ('jp', 32034),
    ('kr', 32035), ('cn', 32036), ('nl', 32037), ('pl', 32038), ('ru', 32039),
    ('hr', 32040), ('ca', 32041), ('au', 32042), ('mx', 32043), ('ng', 32044),
    ('se', 32045), ('no', 32046), ('dk', 32047), ('int', 32048),
)
COUNTRY_CODES = tuple(code for code, stringId in COUNTRIES)

# Laendervorschlag fuer "Meine Laender" aus den gewaehlten Sprachen.
LANGUAGE_COUNTRIES = {
    'de': ('de', 'at', 'ch'), 'en': ('gb', 'us', 'ie', 'ca', 'au'), 'ja': ('jp',),
    'es': ('es', 'mx'), 'fr': ('fr', 'be', 'ch', 'ca'), 'it': ('it', 'ch'),
    'tr': ('tr',), 'hi': ('in',), 'ko': ('kr',), 'pt': ('pt', 'br'), 'pl': ('pl',),
    'ru': ('ru',), 'ar': (), 'nl': ('nl', 'be'), 'zh': ('cn',),
}

AUDIO_SETTING = 'langAudio_%s'
SUBS_SETTING = 'langSubs_%s'
PREFERRED_SETTING = 'langAudioPreferred'
OTHER_MODE_SETTING = 'langOtherMode'        # 'folder' | 'hide'
COUNTRIES_SETTING = 'regionCountries'       # CSV; leer = alle Laender
SETUP_SETTING = 'langSetupDone'
DEFAULT_SOURCE_LANGUAGES = ('de',)
THEMES = (('movies', 32300, 'Filme / Serien'), ('docs', 32301, 'Dokus'), ('anime', 32302, 'Animes'))
_CATEGORY_THEMES = {'filme': 'movies', 'serien': 'movies', 'dokus': 'docs', 'animes': 'anime'}


def themeForCategory(category):
    return _CATEGORY_THEMES.get(category, category if category in ('movies', 'docs', 'anime') else '')


def currentTheme():
    from resources.lib.handler.ParameterHandler import ParameterHandler
    params = ParameterHandler().getAllParameters()
    explicit = themeForCategory(params.get('contentTheme') or params.get('category') or params.get('randomKind'))
    if explicit:
        return explicit
    # Alte Favoriten haben noch keinen Themenparameter. Reine Animequellen
    # bleiben trotzdem im Animeprofil; andere Quellen nutzen das allgemeine Profil.
    if params.get('site') in ('aniworld', 'anime4', 'animeloads', 'animetoast', 'animestream',
                              'kayoanime', 'hianime', 'gogoanime', 'animeonsen', 'proxer'):
        return 'anime'
    return ''


def _profileSetting(theme, field):
    return 'langProfile_%s_%s' % (theme, field)


def themeEnabled(theme):
    theme = themeForCategory(theme)
    return not theme or cConfig().getSettingBool(_profileSetting(theme, 'enabled'), True)


def _profile(theme=None):
    theme = currentTheme() if theme is None else themeForCategory(theme)
    config = cConfig()
    if not theme or not config.getSettingBool(_profileSetting(theme, 'custom'), False):
        return None
    return {'theme': theme, 'enabled': themeEnabled(theme),
            'audio': [code for code in config.getSetting(_profileSetting(theme, 'audio'), '').split(',')
                      if code in LANGUAGE_CODES],
            'subs': [code for code in config.getSetting(_profileSetting(theme, 'subs'), '').split(',')
                     if code in LANGUAGE_CODES]}


def _localized(stringId, fallback):
    text = cConfig().getLocalizedString(stringId)
    return text if text and not str(text).startswith('#') else fallback


def languageLabel(code):
    stringId = dict(LANGUAGES).get(code)
    return _localized(stringId, code.upper()) if stringId else code.upper()


def countryLabel(code):
    stringId = dict(COUNTRIES).get((code or '').lower())
    return _localized(stringId, (code or '').upper()) if stringId else (code or '').upper()


def kodiLanguage():
    """Sprache der Kodi-Oberflaeche als ISO 639-1, sonst ''."""
    try:
        return (xbmc.getLanguage(xbmc.ISO_639_1) or '').lower()[:2]
    except Exception:
        return ''


# --- Gewaehlte Sprachen und Laender ----------------------------------------

def _enabledAudio():
    config = cConfig()
    return [code for code in LANGUAGE_CODES if config.getSettingBool(AUDIO_SETTING % code, code == 'de')]


def preferredLanguage(theme=None):
    profile = _profile(theme)
    enabled = profile['audio'] if profile else _enabledAudio()
    choice = cConfig().getSetting(PREFERRED_SETTING, 'auto')
    if choice in enabled:
        return choice
    kodi = kodiLanguage()
    if kodi in enabled:
        return kodi
    return enabled[0] if enabled else ''


def audioLanguages(theme=None):
    """Eingeschaltete Tonsprachen, die bevorzugte zuerst."""
    profile = _profile(theme)
    enabled = list(profile['audio']) if profile and profile['enabled'] else ([] if profile else _enabledAudio())
    preferred = preferredLanguage(theme)
    if preferred in enabled:
        enabled.remove(preferred)
        enabled.insert(0, preferred)
    return enabled


def subtitleLanguages(theme=None):
    """Untertitelsprachen fuer Originalton-Streams, bevorzugte Tonsprache zuerst."""
    config = cConfig()
    profile = _profile(theme)
    enabled = profile['subs'] if profile and profile['enabled'] else ([] if profile else
              [code for code in LANGUAGE_CODES if config.getSettingBool(SUBS_SETTING % code, code == 'de')])
    order = audioLanguages(theme)
    return sorted(enabled, key=lambda code: order.index(code) if code in order else len(order))


def countries():
    """Gewaehlte Laender; leer bedeutet: keine Einschraenkung."""
    value = cConfig().getSetting(COUNTRIES_SETTING, '') or ''
    return [code for code in (part.strip().lower() for part in value.split(',')) if code in COUNTRY_CODES]


def countryVisible(code):
    chosen = countries()
    return not chosen or (code or '').lower() in chosen


def suggestedCountries(languageCodes):
    result = []
    for code in languageCodes:
        for country in LANGUAGE_COUNTRIES.get(code, ()):
            if country not in result:
                result.append(country)
    return result


def otherLanguagesMode(theme=None):
    if _profile(theme):
        return 'hide'
    # "Alle" und die Hauptansicht sind die Vereinigung der Themenprofile,
    # keine zweite Moeglichkeit, ausgeschlossene Sprachen einzublenden.
    if not themeForCategory(theme or currentTheme()) and any(
            cConfig().getSettingBool(_profileSetting(key, 'custom'), False) for key, _, _ in THEMES):
        return 'hide'
    return 'hide' if cConfig().getSetting(OTHER_MODE_SETTING, 'folder') == 'hide' else 'folder'


# --- Quellen ---------------------------------------------------------------

def sourceLanguages(plugin):
    languages = plugin.get('languages')
    return tuple(languages) if languages is not None else DEFAULT_SOURCE_LANGUAGES


def sourceVisible(plugin, theme=None):
    """Quelle passt zu den gewaehlten Ton- oder Untertitelsprachen."""
    resolved_theme = currentTheme() if theme is None else themeForCategory(theme)
    if not themeEnabled(resolved_theme):
        return False
    languages = sourceLanguages(plugin)
    if not languages:
        return True  # sprachunabhaengig, z.B. Wetter-Webcams
    catalog_languages = plugin.get('catalog_languages') or ()
    if (catalog_languages and cConfig().getSettingBool('langSourceCatalogFilter', True)
            and not set(catalog_languages) & set(audioLanguages(theme) + subtitleLanguages(theme))):
        return False
    if set(languages) & set(audioLanguages(theme)):
        return True
    if resolved_theme == 'anime' and _profile(theme) and 'ja' not in languages:
        return False
    subtitles = set(plugin.get('subtitles') or ()) & set(subtitleLanguages(theme))
    return any(audio != sub for audio in languages for sub in subtitles)


def splitSources(plugins, theme=None):
    """Teilt Quellen in (eigene Sprachen, andere Sprachen)."""
    mine, others = [], []
    for plugin in plugins:
        visible = sourceVisibleAny(plugin) if theme == 'alle' else sourceVisible(plugin, theme)
        (mine if visible else others).append(plugin)
    return mine, others


def sourceVisibleAny(plugin):
    categories = [category for category in plugin.get('categories', ()) if themeForCategory(category)]
    return any(sourceVisible(plugin, category) for category in categories) if categories else sourceVisible(plugin)


def sourceTheme(plugin, category):
    """Themenprofil auch bei reinen Anime-/Dokuquellen im Ordner Alle tragen."""
    explicit = themeForCategory(category)
    if explicit:
        return explicit
    themes = {themeForCategory(value) for value in plugin.get('categories', ())}
    themes.discard('')
    return next(iter(themes)) if len(themes) == 1 else ''


def sourceMainLanguage(plugin):
    """Sprache, unter der eine fremdsprachige Quelle einsortiert wird."""
    languages = sourceLanguages(plugin)
    return languages[0] if languages else ''


# --- Streams ---------------------------------------------------------------

def streamAllowed(audio, subs='', theme=None):
    """Stream zeigen? Unbekannte Sprache wird nie ausgefiltert."""
    selected_theme = currentTheme() if theme is None else themeForCategory(theme)
    if not themeEnabled(selected_theme):
        return False
    if not audio:
        return True
    if audio in audioLanguages(theme):
        return True
    # Anime-Originalton bedeutet Japanisch mit UT, nicht englische Synchro mit UT.
    if selected_theme == 'anime' and _profile(theme) and audio != 'ja':
        return False
    return bool(subs) and audio != subs and subs in subtitleLanguages(theme)


def streamLabel(audio, subs=''):
    if not audio:
        return ''
    if subs:
        return '(%s) Sub: (%s)' % (audio.upper(), subs.upper())
    return '(%s)' % audio.upper()


def streamRank(audio, subs=''):
    """Sortierschluessel: bevorzugte Tonsprache, weitere Tonsprachen, Untertitel."""
    if not audio:
        return (3, 0)
    audioOrder = audioLanguages()
    if audio in audioOrder and not subs:
        return (0, audioOrder.index(audio))
    if audio in audioOrder:
        return (0, len(audioOrder) + audioOrder.index(audio))
    subsOrder = subtitleLanguages()
    if subs in subsOrder:
        return (1, subsOrder.index(subs))
    return (2, 0)


def tagStream(hoster, audio, subs=''):
    """Traegt Sprache, Anzeige und Sortierung einheitlich in einen Hoster ein."""
    hoster['audio'] = audio or ''
    hoster['subs'] = subs or ''
    hoster['languageCode'] = streamLabel(audio, subs)
    return hoster


def siteValue(choices, allValue):
    """Waehlt einen Sprachparameter fuer Seiten mit eigener Sprachauswahl.

    ``choices`` ordnet Sprachen dem Wert der Seite zu, z.B. {'de': '2',
    'en': '3'}. Ist genau eine dieser Sprachen gewaehlt, gilt ihr Wert,
    sonst ``allValue``.
    """
    enabled = [code for code in choices if code in audioLanguages()]
    return choices[enabled[0]] if len(enabled) == 1 else allValue


# --- Einrichtung -----------------------------------------------------------

def applyChoice(audio, subs, preferred=''):
    config = cConfig()
    for code in LANGUAGE_CODES:
        config.setSetting(AUDIO_SETTING % code, 'true' if code in audio else 'false')
        config.setSetting(SUBS_SETTING % code, 'true' if code in subs else 'false')
    config.setSetting(PREFERRED_SETTING, preferred if preferred in audio else 'auto')
    if not countries():
        config.setSetting(COUNTRIES_SETTING, ','.join(suggestedCountries(audio)))
    config.setSetting(SETUP_SETTING, 'true')


def ensureSetup(interactive=True):
    """Fragt beim ersten Start einmalig, welche Sprachen verstanden werden."""
    if cConfig().getSettingBool(SETUP_SETTING, False) or not interactive:
        return False
    return chooseThemeLanguages(first_run=True)


def _themeLabel(theme):
    return next((_localized(number, fallback) for key, number, fallback in THEMES if key == theme), theme)


def _chooseTheme(theme, first_run=False):
    profile = _profile(theme)
    audio = profile['audio'] if profile else _enabledAudio()
    subs = profile['subs'] if profile else subtitleLanguages('')
    if first_run:
        kodi = kodiLanguage()
        audio = [kodi if kodi in LANGUAGE_CODES else 'de']
        subs = []  # Untertitel/Originalton nur nach bewusster Auswahl.
    labels = [_localized(32303, 'Nicht anzeigen')] + [languageLabel(code) for code in LANGUAGE_SELECTION_CODES]
    original_index = len(labels)
    labels.append(_localized(32304, 'Japanischer Originalton mit deutschen Untertiteln') if theme == 'anime'
                  else _localized(32305, 'Originalton mit deutschen Untertiteln'))
    preselect = [LANGUAGE_SELECTION_CODES.index(code) + 1 for code in audio]
    if 'de' in subs:
        preselect.append(original_index)
    if not themeEnabled(theme):
        preselect = [0]
    selected = xbmcgui.Dialog().multiselect(_themeLabel(theme), labels, preselect=preselect)
    if selected is None:
        return (theme, audio, subs, themeEnabled(theme)) if first_run else None
    if 0 in selected:
        return theme, [], [], False
    chosen_audio = {code for index, code in enumerate(LANGUAGE_SELECTION_CODES, 1) if index in selected}
    audio = [code for code in LANGUAGE_CODES if code in chosen_audio]
    subs = ['de'] if original_index in selected else []
    return theme, audio, subs, bool(audio or subs)


def applyThemeChoice(theme, audio, subs, enabled=True):
    if theme not in dict((key, number) for key, number, fallback in THEMES):
        return False
    config = cConfig()
    config.setSetting(_profileSetting(theme, 'audio'), ','.join(code for code in LANGUAGE_CODES if code in audio))
    config.setSetting(_profileSetting(theme, 'subs'), ','.join(code for code in LANGUAGE_CODES if code in subs))
    config.setSetting(_profileSetting(theme, 'enabled'), 'true' if enabled else 'false')
    config.setSetting(_profileSetting(theme, 'custom'), 'true')
    return True


def chooseThemeLanguages(first_run=False):
    # Gather choices before writing, so cancelling a manual edit changes nothing.
    choices = []
    for key, number, fallback in THEMES:
        choice = _chooseTheme(key, first_run)
        if choice is None:
            return False
        choices.append(choice)
    for choice in choices:
        applyThemeChoice(*choice)
    if first_run:
        audio = list(dict.fromkeys(code for _, selected, _, enabled in choices if enabled for code in selected))
        subs = list(dict.fromkeys(code for _, _, selected, enabled in choices if enabled for code in selected))
        kodi = kodiLanguage()
        preferred = kodi if kodi in audio else (audio[0] if audio else 'de')
        applyChoice(audio, subs, preferred)
        cConfig().setSetting('tmdb_lang', preferred)
    return True


def editTheme(theme):
    if theme not in ('movies', 'docs', 'anime'):
        return False
    choice = _chooseTheme(theme)
    return applyThemeChoice(*choice) if choice is not None else False


def chooseLanguages():
    """Fragt, welche Sprachen verstanden werden (auch aus den Einstellungen)."""
    current = _enabledAudio() if cConfig().getSettingBool(SETUP_SETTING, False) else []
    kodi = kodiLanguage()
    preselect = [LANGUAGE_SELECTION_CODES.index(code) for code in (current or [kodi if kodi in LANGUAGE_CODES else 'de'])]
    selected = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32074),
                                            [languageLabel(code) for code in LANGUAGE_SELECTION_CODES],
                                            preselect=preselect)
    if selected is None:
        if current:
            return False
        selected = preselect
    chosen = [LANGUAGE_SELECTION_CODES[index] for index in selected] or [LANGUAGE_SELECTION_CODES[index] for index in preselect]
    preferred = kodi if kodi in chosen else chosen[0]
    applyChoice(chosen, chosen, preferred)
    # Titel und Beschreibungen von TMDB in der bevorzugten Sprache; alle
    # Sprachen oben sind auch TMDB-Sprachen (Einstellung tmdb_lang).
    cConfig().setSetting('tmdb_lang', preferred)
    return True


def editCountries():
    chosen = set(countries())
    selected = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32068),
                                            [countryLabel(code) for code in COUNTRY_CODES],
                                            preselect=[index for index, code in enumerate(COUNTRY_CODES)
                                                       if code in chosen])
    if selected is not None:
        cConfig().setSetting(COUNTRIES_SETTING, ','.join(COUNTRY_CODES[index] for index in selected))
