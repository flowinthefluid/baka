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
LEGACY_SETTING = 'prefLanguage'             # 0 alle, 1 DE, 2 EN, 3 JA
DEFAULT_SOURCE_LANGUAGES = ('de',)


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


def preferredLanguage():
    enabled = _enabledAudio()
    choice = cConfig().getSetting(PREFERRED_SETTING, 'auto')
    if choice in enabled:
        return choice
    kodi = kodiLanguage()
    if kodi in enabled:
        return kodi
    return enabled[0] if enabled else ''


def audioLanguages():
    """Eingeschaltete Tonsprachen, die bevorzugte zuerst."""
    enabled = _enabledAudio()
    preferred = preferredLanguage()
    if preferred in enabled:
        enabled.remove(preferred)
        enabled.insert(0, preferred)
    return enabled


def subtitleLanguages():
    """Untertitelsprachen fuer Originalton-Streams, bevorzugte Tonsprache zuerst."""
    config = cConfig()
    enabled = [code for code in LANGUAGE_CODES if config.getSettingBool(SUBS_SETTING % code, code == 'de')]
    order = audioLanguages()
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


def otherLanguagesMode():
    return 'hide' if cConfig().getSetting(OTHER_MODE_SETTING, 'folder') == 'hide' else 'folder'


# --- Quellen ---------------------------------------------------------------

def sourceLanguages(plugin):
    languages = plugin.get('languages')
    return tuple(languages) if languages is not None else DEFAULT_SOURCE_LANGUAGES


def sourceVisible(plugin):
    """Quelle passt zu den gewaehlten Ton- oder Untertitelsprachen."""
    languages = sourceLanguages(plugin)
    if not languages:
        return True  # sprachunabhaengig, z.B. Wetter-Webcams
    if set(languages) & set(audioLanguages()):
        return True
    return bool(set(plugin.get('subtitles') or ()) & set(subtitleLanguages()))


def splitSources(plugins):
    """Teilt Quellen in (eigene Sprachen, andere Sprachen)."""
    mine, others = [], []
    for plugin in plugins:
        (mine if sourceVisible(plugin) else others).append(plugin)
    return mine, others


def sourceMainLanguage(plugin):
    """Sprache, unter der eine fremdsprachige Quelle einsortiert wird."""
    languages = sourceLanguages(plugin)
    return languages[0] if languages else ''


# --- Streams ---------------------------------------------------------------

def streamAllowed(audio, subs=''):
    """Stream zeigen? Unbekannte Sprache wird nie ausgefiltert."""
    if not audio:
        return True
    if audio in audioLanguages():
        return True
    return bool(subs) and subs in subtitleLanguages()


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


def _legacyChoice(value):
    """Uebernimmt die alte Einstellung "Bevorzugte Sprache" (Alle/DE/EN/JA)."""
    if value == '1':
        return ['de'], [], 'de'
    if value == '2':
        return ['en', 'de'], [], 'en'
    if value == '3':
        return ['ja', 'de'], ['de', 'en'], 'ja'
    return ['de', 'en', 'ja'], ['de', 'en'], 'de'


def ensureSetup(interactive=True, migratedFrom=''):
    """Richtet die Sprachen beim ersten Start einmalig ein.

    Wer von GerXStream kommt, behaelt seine bisherige Auswahl ohne Rueckfrage.
    Alle anderen werden einmal gefragt, welche Sprachen sie verstehen.
    """
    config = cConfig()
    if config.getSettingBool(SETUP_SETTING, False):
        return False
    legacy = config.getSetting(LEGACY_SETTING, '')
    if migratedFrom or legacy in ('1', '2', '3'):
        applyChoice(*_legacyChoice(legacy))
        return True
    if not interactive:
        return False
    return chooseLanguages()


def chooseLanguages():
    """Fragt, welche Sprachen verstanden werden (auch aus den Einstellungen)."""
    current = _enabledAudio() if cConfig().getSettingBool(SETUP_SETTING, False) else []
    kodi = kodiLanguage()
    preselect = [LANGUAGE_CODES.index(code) for code in (current or [kodi if kodi in LANGUAGE_CODES else 'de'])]
    selected = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32074),
                                            [languageLabel(code) for code in LANGUAGE_CODES],
                                            preselect=preselect)
    if selected is None:
        if current:
            return False
        selected = preselect
    chosen = [LANGUAGE_CODES[index] for index in selected] or [LANGUAGE_CODES[index] for index in preselect]
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
