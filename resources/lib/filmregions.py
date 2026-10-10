"""Compact film-country menus; selection is separate from live-TV countries."""

import json
import os
from functools import lru_cache

import xbmcgui
from resources.lib.config import cConfig
from resources.lib import languages
from resources.lib.handler.ParameterHandler import ParameterHandler

COUNTRIES_SETTING = 'filmLocationCountries'
DIRECT = ('DE', 'US', 'CA', 'FR', 'GB', 'JP')
DEFAULT = frozenset(('DE', 'US', 'CA', 'FR', 'GB', 'JP', 'AT', 'CH', 'IE', 'IT',
                     'ES', 'PT', 'NL', 'BE', 'PL', 'SE', 'NO', 'DK', 'FI', 'IS',
                     'CN', 'KR', 'TH', 'IN', 'HK', 'TW', 'ID', 'VN', 'PH',
                     'MX', 'BZ', 'CR', 'SV', 'GT', 'HN', 'NI', 'PA',
                     'AR', 'BR', 'CL', 'CO', 'PE', 'UY', 'VE', 'BO', 'EC',
                     'ZA', 'KE', 'GH', 'EG', 'NG', 'MA', 'TN', 'DZ',
                     'AU', 'NZ', 'CU', 'DO', 'JM'))
REGIONS = (('europe', 32501), ('asia', 32502), ('africa', 32503),
           ('central_america', 32055), ('south_america', 32504),
           ('caribbean', 32505), ('oceania', 32506),
           ('north_america', 32507), ('other', 32508))


@lru_cache(maxsize=1)
def catalog():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'film_countries.json')
    with open(path, encoding='utf-8') as handle:
        return {row['code']: row for row in json.load(handle)['countries']}


def selected():
    raw = cConfig().getSetting(COUNTRIES_SETTING, '') or ''
    return (set(raw.split(',')) if raw else set(DEFAULT)) & set(catalog())


def name(code):
    language = 'de' if languages.kodiLanguage() == 'de' else 'en'
    if code == 'US' and language == 'de':
        return 'USA'
    return catalog()[code][language]


def region_codes(region):
    if region not in dict(REGIONS):
        return []
    return sorted(code for code in selected() if catalog()[code]['region'] == region)


def _label(label):
    return cConfig().getLocalizedString(label)


def _country_folder(code):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    params = ParameterHandler()
    params.setParam('catLevel', 'entries')
    params.setParam('catPreset', 'country:' + code)
    params.setParam('catMedia', 'movie')
    params.setParam('hollywoodScope', 'locations')
    params.setParam('page', '1')
    element = cGuiElement(name(code), 'categories', 'categories')
    element.setDescription(_label(32512))
    cGui().addFolder(element, params)


def menu(params):
    from resources.lib.gui.gui import cGui
    from resources.lib.gui.guiElement import cGuiElement
    region = params.getValue('filmRegion')
    if region:
        codes = region_codes(region)
        if codes:
            group = ParameterHandler()
            group.addParams({'catLevel': 'entries', 'catPreset': 'region:' + region,
                             'catMedia': 'movie', 'hollywoodScope': 'locations', 'page': '1'})
            cGui().addFolder(cGuiElement(_label(32509), 'categories', 'categories'), group)
            if cConfig().getSettingBool('filmLocationIndividualCountries', True):
                for code in sorted(set(codes) - set(DIRECT), key=lambda code: name(code).casefold()):
                    _country_folder(code)
    else:
        for code in DIRECT:
            if code in selected():
                _country_folder(code)
        for region, label in REGIONS:
            if set(region_codes(region)) - set(DIRECT):
                group = ParameterHandler()
                group.addParams({'catLevel': 'locationRegion', 'filmRegion': region})
                cGui().addFolder(cGuiElement(_label(label), 'categories', 'categories'), group)
    cGui().setEndOfDirectory()


def edit():
    codes = sorted(catalog(), key=lambda code: name(code).casefold())
    active = selected()
    result = xbmcgui.Dialog().multiselect(_label(32510), [name(code) for code in codes],
                                         preselect=[index for index, code in enumerate(codes) if code in active])
    if result is not None:
        cConfig().setSetting(COUNTRIES_SETTING, ','.join(codes[index] for index in result) or '-')


def query(preset):
    """Validate every country/region before constructing a Discover query."""
    kind, _, code = preset.partition(':')
    if kind == 'country' and code in catalog():
        countries = [code]
    elif kind == 'region':
        countries = region_codes(code)
    else:
        countries = []
    if not countries:
        return None
    return 'with_origin_country=%s&sort_by=popularity.desc' % '|'.join(countries)
