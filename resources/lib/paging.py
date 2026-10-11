# -*- coding: utf-8 -*-
# Python 3
"""Seitenanzeige "Seite X von Y" mit Sprung zu einer beliebigen Seite.

Quellen kennen meist nur den Link zur naechsten Seite. Der Vergleich mit
der aktuellen Seite zeigt, welche Zahl die Seite angibt (z.B. ``/page/3/``,
``?page=3`` oder ein eigener Parameter ``page``). Daraus entsteht der Link
zu jeder anderen Seite. Laesst sich die Seitenzahl nicht sicher erkennen,
erscheint keine Seitenanzeige.
"""

import json
import os
import re
import sys
from urllib.parse import unquote_plus, urlencode

# Parameter, die nur die Navigation selbst beschreiben.
IGNORED = ('site', 'function', 'title', 'trumb', 'params', 'playMode', 'pageJump')
MAX_PAGE = 100000
_NAME = re.compile(r'[A-Za-z0-9_.-]{1,80}')


def _exactTemplate(old, new):
    """Zahl N im neuen Wert, deren Ersatz durch N-1 genau den alten ergibt."""
    for match in re.finditer(r'\d+', new):
        number = int(match.group())
        if not 2 <= number <= MAX_PAGE:
            continue
        template = new[:match.start()] + '{page}' + new[match.end():]
        if template.replace('{page}', str(number - 1)) == old:
            return template, number - 1
    return None


def _firstPageTemplate(old, new):
    """Erste Seite: Die Seitenzahl taucht erst im Link zur zweiten Seite auf,
    z.B. ".../filme/" -> ".../filme/page/2/" oder kein page -> page=2."""
    prefix = len(os.path.commonprefix([old, new]))
    suffix = len(os.path.commonprefix([old[prefix:][::-1], new[prefix:][::-1]]))
    if old[prefix:len(old) - suffix]:
        return None
    added = new[prefix:len(new) - suffix]
    twos = list(re.finditer(r'(?<!\d)2(?!\d)', added))
    if len(twos) != 1:
        return None
    start = prefix + twos[0].start()
    return new[:start] + '{page}' + new[start + 1:], 1


def describe(current, nextParams, total=None):
    """Seitenzahl im Link zur naechsten Seite finden; None, wenn unsicher.

    Zuerst zaehlt nur ein exakter Treffer (Seite N -> N-1 ergibt die aktuelle
    Seite). Die Sonderregel fuer die erste Seite gilt nur fuer Seiten- und
    Adressparameter, damit z.B. ein Titel "Fast 2" nie als Seite gilt.
    """
    keys = [key for key in nextParams if key not in IGNORED]
    candidates = [(key, _exactTemplate) for key in keys]
    candidates += [(key, _firstPageTemplate) for key in keys
                   if 'page' in key.lower() or 'url' in key.lower()]
    for key, finder in candidates:
        old = str(current.get(key, '') or '')
        if key.lower() in ('page', 'ipage', 'spage') and old in ('', '0') and str(nextParams[key]) == '2':
            return {'key':key, 'template':'{page}', 'page':1, 'first':old or '1',
                    'total':int(total) if total and int(total) >= 1 else 0}
        found = finder(old, str(nextParams[key]))
        if found:
            template, page = found
            return {'key': key, 'template': template, 'page': page, 'first': old,
                    'total': int(total) if total and int(total) >= page else 0}
    return None


def describeCurrent(current):
    """Letzte Seite ohne Next-Link: nur ausdrueckliche Seitenparameter/URLs."""
    for key, value in current.items():
        value = str(value or '')
        if key.lower() in ('page', 'ipage', 'spage') and value.isdigit():
            match = re.fullmatch(r'\d+', value)
        elif key in ('sUrl', 'entryUrl'):
            match = re.search(r'(?:/page/|[?&]page=)(\d+)', value)
        else:
            continue
        if match:
            page = int(match.group(1) if match.lastindex else match.group())
            if 1 < page <= MAX_PAGE:
                start,end = match.span(1) if match.lastindex else match.span()
                return {'key':key, 'template':value[:start]+'{page}'+value[end:],
                        'page':page, 'first':'', 'total':0}
    return None


def _text(stringId, fallback, *args):
    """Uebersetzter Text; passt er nicht zu den Werten, der Standardtext."""
    from resources.lib.config import cConfig

    try:
        text = cConfig().getLocalizedString(stringId)
        return (text if text and not text.startswith('#') else fallback) % args
    except (TypeError, ValueError):
        return fallback % args


def label(jump):
    prefix = _text(30284, '[I]Start page search  >>> [/I] Page ')
    if jump['total']:
        return '%s%s%s%s%s' % (prefix, jump['page'], _text(30285, ' of '),
                               jump['total'], _text(30286, ' Pages [I]<<<[/I]'))
    return '%s%s [I]<<<[/I]' % (prefix, jump['page'])


def jumpParams(jump, site, function, nextParams):
    data = dict(jump, site=site, function=function,
                params=dict((key, str(value)) for key, value in nextParams.items() if key not in IGNORED))
    return json.dumps(data, separators=(',', ':'))


def targetUrl(data, page, pluginPath='plugin://plugin.video.baka/'):
    """Link zu Seite ``page`` oder None bei ungueltiger Eingabe."""
    if not isinstance(data, dict) or not _NAME.fullmatch(str(data.get('site', ''))) or \
            not _NAME.fullmatch(str(data.get('function', ''))) or not isinstance(data.get('params'), dict):
        return None
    total = int(data.get('total') or 0)
    if page < 1 or page > MAX_PAGE or (total and page > total):
        return None
    params = dict((str(key), unquote_plus(str(value))) for key, value in data['params'].items())
    template = str(data.get('template', ''))
    if '{page}' not in template:
        return None
    params[str(data['key'])] = (data['first'] if page == 1 and int(data.get('page', 0)) == 1
                              and data.get('first') else template.replace('{page}', str(page)))
    query = dict(site=data['site'], function=data['function'])
    query.update(params)
    return '%s?%s' % (pluginPath, urlencode(query))


def jump(params):
    """Fragt die Seitenzahl ab und oeffnet die Seite."""
    import xbmc
    import xbmcgui
    import xbmcplugin
    from resources.lib.config import cConfig

    try:
        xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=False, updateListing=False, cacheToDisc=False)
    except (IndexError, ValueError):
        pass
    try:
        data = json.loads(params.getValue('pageJump') or '')
    except (TypeError, ValueError):
        return
    value = xbmcgui.Dialog().numeric(0, cConfig().getLocalizedString(32098), str(data.get('page', '')))
    if not value or not str(value).isdigit():
        return
    url = targetUrl(data, int(value), sys.argv[0] if sys.argv and sys.argv[0].startswith('plugin://') else
                    'plugin://plugin.video.baka/')
    if not url:
        xbmcgui.Dialog().notification('Baka', _text(32099, 'Seite %s gibt es nicht.', value),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        return
    xbmc.executebuiltin('Container.Update(%s)' % url)
