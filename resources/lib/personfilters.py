"""Actor visibility, citizenship selection and explicit cast boycotts."""

import json
import re
import xbmc
import xbmcgui

from resources.lib.config import cConfig

SETTINGS = {'hide': 'hiddenActors', 'boycott': 'boycottedActors'}


def stored(action):
    if action not in SETTINGS:
        return {}
    try:
        data = json.loads(cConfig().getSetting(SETTINGS[action], '{}'))
    except (ValueError, TypeError):
        return {}
    return {str(key): str(value) for key, value in data.items()
            if re.fullmatch(r'[1-9]\d{0,9}', str(key))} if isinstance(data, dict) else {}


def excludedCountries():
    from resources.lib import filmregions
    raw = set(cConfig().getSetting('actorExcludedCountries', '').split(','))
    codes = raw & set(filmregions.catalog())
    regions = {key[7:] for key in raw if key.startswith('region:')}
    codes.update(code for code, row in filmregions.catalog().items() if row['region'] in regions)
    return codes


def active():
    return bool(stored('hide') or stored('boycott') or excludedCountries())


def filterPeople(people):
    hidden = set(stored('hide')) | set(stored('boycott'))
    visible = [person for person in people if str(person.get('id')) not in hidden]
    excluded = excludedCountries()
    if excluded and visible:
        from resources.lib import persondata
        nationalities = persondata.nationalities([person['id'] for person in visible])
        visible = [person for person in visible if not excluded.intersection(
            nationalities.get(str(person['id']), []))]
    return visible


def action(params):
    kind = params.getValue('personAction')
    personId = str(params.getValue('personId'))
    if kind not in SETTINGS or not re.fullmatch(r'[1-9]\d{0,9}', personId):
        return False
    data = stored(kind)
    data[personId] = str(params.getValue('personName') or personId)[:200]
    cConfig().setSetting(SETTINGS[kind], json.dumps(data, ensure_ascii=False))
    xbmc.executebuiltin('Container.Refresh')
    return True


def manage(kind):
    data = stored(kind)
    keys = sorted(data, key=lambda key: data[key].casefold())
    result = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32706),
                                          [data[key] for key in keys], preselect=[])
    if result is not None and kind in SETTINGS:
        for index in result:
            data.pop(keys[index], None)
        cConfig().setSetting(SETTINGS[kind], json.dumps(data, ensure_ascii=False))


def editCountries():
    from resources.lib import filmregions
    regions = list(filmregions.REGIONS)
    codes = sorted(filmregions.catalog(), key=lambda code: filmregions.name(code).casefold())
    options = [('region:' + region, cConfig().getLocalizedString(label)) for region, label in regions]
    options.extend((code, filmregions.name(code)) for code in codes)
    selected = set(cConfig().getSetting('actorExcludedCountries', '').split(','))
    result = xbmcgui.Dialog().multiselect(cConfig().getLocalizedString(32703),
        [label for key, label in options],
        preselect=[index for index, (key, label) in enumerate(options) if key in selected])
    if result is not None:
        cConfig().setSetting('actorExcludedCountries', ','.join(options[index][0] for index in result))
