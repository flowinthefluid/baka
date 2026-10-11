# -*- coding: utf-8 -*-
# Python 3
"""In-Addon-Navigation und Wiedergabe fuer den Livestream-Bereich.

Ein einziger Einstieg (``route``), der nach ``lsLevel`` verteilt - dasselbe
Muster wie ``resources/lib/categories.py``. Leere Bereiche zeigen einen
freundlichen Empty-State statt eines kaputten Ordners.

Wiedergabe (``play``) waehlt automatisch die beste Quelle und schaltet bei
einem Fehlstart auf die naechste um (Aufgabe 3d/3e). ``showSources`` listet
alle Quellen mit Beschreibung zur manuellen Wahl (Aufgabe 3c).
"""

import os
import time
from urllib.parse import urlencode

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import contentgate
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.livestreams import catalog, selector, taxonomy, export, epg, sports, curation
from resources.lib.tools import logger

SITE_IDENTIFIER = 'livestreams'
LEVELS = ('root', 'section', 'continents', 'countries', 'genres', 'country', 'genre',
          'channels', 'cities', 'wcategories', 'sources', 'detail',
          'weather', 'rabbithole_list', 'yt_cats', 'yt_live', 'tw_live', 'sport_kinds', 'epg',
          'world_now', 'webcam_stats', 'weather_world', 'weather_countries', 'weather_kinds')
ART = os.path.join(cConfig().getAddonInfo('path'), 'resources', 'art')


def _art(name):
    path = os.path.join(ART, name)
    return path if os.path.exists(path) else os.path.join(ART, 'sources.png')


def _folder(title, level, params_dict, thumb='sources.png'):
    params = ParameterHandler()
    params.setParam('lsLevel', level)
    for key, value in params_dict.items():
        params.setParam(key, value)
    element = cGuiElement(title, SITE_IDENTIFIER, 'route')
    element.setThumbnail(_art(thumb))
    cGui().addFolder(element, params)


def _empty_state(oGui):
    """Freundlicher Hinweis statt eines leeren/kaputten Ordners."""
    text = cConfig().getLocalizedString(31200)
    if not text or str(text).startswith('#'):
        text = 'Hier ist noch nichts verfuegbar. Quellen lassen sich in den Einstellungen erganzen.'
    element = cGuiElement(text, SITE_IDENTIFIER, '')
    element.setThumbnail(_art('sources.png'))
    oGui.addFolder(element, ParameterHandler(), bIsFolder=False)


def route(params=None):
    params = params or ParameterHandler()
    level = params.getValue('lsLevel')
    if level not in LEVELS:
        level = 'root'
    handler = {
        'root': _root,
        'section': _section,
        'countries': _countries,
        'continents': _continents,
        'genres': _genres,
        'country': _channels_filtered,
        'genre': _channels_filtered,
        'channels': _channels_filtered,
        'cities': _cities,
        'wcategories': _wcategories,
        'sources': show_sources,
        'detail': show_detail,
        'weather': weather,
        'rabbithole_list': rabbithole_list,
        'yt_cats': yt_categories,
        'yt_live': yt_live,
        'tw_live': tw_live,
        'sport_kinds': _sport_kinds,
        'epg': _show_epg,
        'world_now': _world_now,
        'webcam_stats': _webcam_stats,
        'weather_world': _weather_world,
        'weather_countries': _weather_countries,
        'weather_kinds': _weather_kinds,
    }[level]
    handler(params)


def _root(params):
    oGui = cGui()
    shown = 0
    for section_id in taxonomy.SECTION_IDS:
        if not contentgate.is_section_visible(section_id):
            continue
        if not catalog.channels_by_section(section_id):
            # Bereich sichtbar, aber (noch) leer -> trotzdem anzeigen, damit
            # der Nutzer den Empty-State und die Einstellungen findet.
            pass
        _folder(taxonomy.section_label(section_id), 'section',
                {'section': section_id}, thumb='%s.png' % section_id)
        shown += 1
    if shown == 0:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _section(params):
    section = params.getValue('section')
    # Wetter hat eine eigene Ansicht (Wetter-Webcams + Live-Wetterzeile).
    if section == 'weather':
        weather(params)
        return
    oGui = cGui()
    if not contentgate.is_section_visible(section):
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return
    # Social zeigt Plattform-Einstiege (YouTube/Twitch) auch ohne kuratierte
    # Kanaele - daher vor dem Leer-Guard behandeln.
    if section == 'social':
        _social(oGui)
        oGui.setEndOfDirectory()
        return
    channels = catalog.channels_by_section(section)
    if not channels:
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return
    # Fernsehen bekommt die reichere Struktur (Laender + Genre).
    if section == 'tv':
        _folder(_label(31210, 'Sender nach Laendern'), 'countries', {'section': section}, 'countries.png')
        _folder(_label(31211, 'Sender nach Genre'), 'genres', {'section': section}, 'genre.png')
    elif section == 'sports':
        _folder(_label(32308, 'Sender nach Sportarten'), 'sport_kinds', {'section': section}, 'genre.png')
        _folder(_label(32309, 'Alle Sportsender'), 'channels', {'section': section}, 'sports.png')
    elif section == 'webcam':
        # Webcams: Rabbithole/Zufall oben, dann nach Laendern und nach Kategorie.
        _rabbithole_play_item(oGui)
        _folder(_label(31222, 'Zufaellig (250)'), 'rabbithole_list', {}, 'sources.png')
        _folder(_label(32918, 'Nach Kontinent, Land und Stadt'), 'continents', {'section': section}, 'countries.png')
        _folder(_label(32925, 'Nach Themen'), 'wcategories', {'section': section}, 'genre.png')
        _folder(_label(32940, 'Around the World Right Now'), 'world_now', {'section': section}, 'webcam.png')
        _folder(_label(32959, 'Weather right now'), 'weather_world', {'section': section}, 'weather.png')
        _folder(_label(32949, 'Webcam statistics'), 'webcam_stats', {'section': section}, 'webcam.png')
    else:
        # Andere Bereiche: direkt die Kanalliste.
        for channel in channels:
            _channel_item(oGui, channel)
    oGui.setEndOfDirectory()


def _label(string_id, fallback):
    text = cConfig().getLocalizedString(string_id)
    return text if text and not str(text).startswith('#') else fallback


def _countries(params):
    oGui = cGui()
    section = params.getValue('section')
    # Webcams: Land -> Stadt; sonst Land -> Kanaele.
    child = 'cities' if section in ('webcam', 'weather') else 'country'
    channels = _filtered_channels(params)
    countries = list(dict.fromkeys(c['country'] for c in channels))
    if section in ('webcam', 'weather'):
        countries.sort(key=lambda code: taxonomy.country_label(code).casefold())
    if section not in ('webcam', 'weather'):
        countries = contentgate.get_visible_countries(catalog.countries_in_section(section))
    if not countries:
        _empty_state(oGui)
    if section == 'tv' and any(country in curation.DACH for country in countries):
        _folder(_label(32306, 'Deutschland / Österreich / Schweiz'), child,
                {'section': section, 'country': 'dach'}, 'countries.png')
        countries = [country for country in countries if country not in curation.DACH]
    for country in countries:
        _folder(taxonomy.country_label(country), child,
                {'section': section, 'country': country}, 'countries.png')
    oGui.setEndOfDirectory()


def _continents(params):
    from resources.lib.livestreams import webcam_geography
    oGui = cGui()
    channels = _filtered_channels(params)
    present = {webcam_geography.continent(channel) for channel in channels}
    for key, label in webcam_geography.CONTINENTS:
        if key in present:
            _folder(_label(label, key), 'countries',
                    {'section': params.getValue('section'), 'continent': key}, 'countries.png')
    if not present:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _cities(params):
    """Staedte innerhalb eines Landes (Webcams). Kanaele ohne Stadt direkt."""
    oGui = cGui()
    section = params.getValue('section')
    country = params.getValue('country')
    channels = _filtered_channels(params)
    cities = []
    for channel in channels:
        city = channel.get('city')
        if city and city not in cities:
            cities.append(city)
    for city in sorted(cities):
        _folder(city, 'channels', {'section': section, 'country': country, 'city': city},
                'countries.png')
    # Kanaele ohne Stadtangabe direkt anzeigen.
    loose = [c for c in channels if not c.get('city')]
    if not cities and not loose:
        _empty_state(oGui)
    for channel in loose:
        _channel_item(oGui, channel)
    oGui.setEndOfDirectory()


def _wcategories(params):
    """Thematische Wege der Webcams (Berge, Tiere, Strände ...)."""
    oGui = cGui()
    section = params.getValue('section')
    present = catalog.genres_in_section(section)
    channels = catalog.channels_by_section(section)
    shown = 0
    for cat in taxonomy.WEBCAM_CATEGORY_IDS:
        if cat == contentgate.NSFW_GENRE:
            continue
        if cat in present and contentgate.is_genre_visible(cat):
            count = sum(cat in (channel.get('genre') or []) for channel in channels)
            _folder('%s (%d)' % (taxonomy.genre_label(cat), count), 'channels',
                    {'section': section, 'genre': cat}, 'genre.png')
            shown += 1
    if shown == 0:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _world_now(params):
    from resources.lib.livestreams import webcam_now
    oGui = cGui()
    groups = webcam_now.group_channels(_filtered_channels(params))
    for key, string_id in webcam_now.GROUPS:
        _folder('%s (%d)' % (_label(string_id, key), len(groups[key])), 'channels',
                {'section': 'webcam', 'solar': key}, 'webcam.png')
    _folder(_label(32918, 'Explore continents, countries and cities'), 'continents',
            {'section': 'webcam'}, 'countries.png')
    oGui.setEndOfDirectory()


def _webcam_stats(params):
    from resources.lib.livestreams import webcam_now
    oGui = cGui()
    stats = webcam_now.statistics(catalog.load_all())
    visible = webcam_now.statistics(catalog.visible_channels())
    for key, string_id in (('cameras', 32950), ('countries', 32951), ('locations', 32952),
                           ('positioned', 32953), ('sources', 32954), ('stations', 32955)):
        _info_item(oGui, '%s: %d' % (_label(string_id, key), stats[key]))
    _info_item(oGui, '%s: %d' % (_label(32956, 'Visible cameras'), visible['cameras']))
    for host, count in sorted(stats['directories'].items()):
        _info_item(oGui, '%s: %d' % (host, count))
    for topic in taxonomy.WEBCAM_CATEGORY_IDS:
        count = visible['topics'].get(topic, 0)
        if count:
            _folder('%s (%d)' % (taxonomy.genre_label(topic), count), 'channels',
                    {'section': 'webcam', 'genre': topic}, 'genre.png')
    oGui.setEndOfDirectory()


def _weather_world(params):
    from resources.lib.livestreams import webcam_geography, webcam_now
    oGui = cGui()
    channels = [channel for channel in _filtered_channels(params) if webcam_now.coordinates(channel)]
    present = {webcam_geography.continent(channel) for channel in channels}
    for key, string_id in webcam_geography.CONTINENTS:
        if key in present:
            _folder(_label(string_id, key), 'weather_countries',
                    {'section': params.getValue('section'), 'continent': key}, 'countries.png')
    if not present:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _weather_countries(params):
    from resources.lib.livestreams import webcam_now
    oGui = cGui()
    countries = {channel['country'] for channel in _filtered_channels(params)
                 if webcam_now.coordinates(channel)}
    for country in sorted(countries, key=taxonomy.country_label):
        _folder(taxonomy.country_label(country), 'weather_kinds',
                {'section': params.getValue('section'), 'country': country}, 'weather.png')
    if not countries:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _weather_kinds(params):
    from resources.lib.livestreams import webcam_weather
    oGui = cGui()
    progress = xbmcgui.DialogProgress()
    progress.create('Baka', _label(32959, 'Weather right now'))
    try:
        groups = webcam_weather.group_channels(_filtered_channels(params), cancelled=progress.iscanceled)
    finally:
        progress.close()
    for key, string_id in webcam_weather.GROUPS:
        filters = {name: params.getValue(name) for name in ('section', 'country', 'continent') if params.getValue(name)}
        filters['weatherKind'] = key
        _folder('%s (%d)' % (_label(string_id, key), len(groups[key])), 'channels', filters, 'weather.png')
    oGui.setEndOfDirectory()


def _genres(params):
    oGui = cGui()
    section = params.getValue('section')
    genres = catalog.genres_in_section(section)
    shown = 0
    for genre in genres:
        if genre == contentgate.NSFW_GENRE and not contentgate.is_nsfw_enabled():
            continue
        if not contentgate.is_genre_visible(genre):
            continue
        _folder(taxonomy.genre_label(genre), 'genre',
                {'section': section, 'genre': genre}, 'genre.png')
        shown += 1
    if shown == 0:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _filtered_channels(params):
    section = params.getValue('section')
    country = params.getValue('country')
    genre = params.getValue('genre')
    city = params.getValue('city')
    sport = params.getValue('sport')
    channels = catalog.channels_by_section(section)
    if params.getValue('continent'):
        from resources.lib.livestreams import webcam_geography
        channels = [c for c in channels if webcam_geography.continent(c) == params.getValue('continent')]
    if country:
        wanted = set(curation.DACH) if country == 'dach' else {country}
        channels = [c for c in channels if wanted & set(c.get('countries') or [c.get('country')])]
    if city:
        channels = [c for c in channels if c.get('city') == city]
    if genre:
        channels = [c for c in channels if genre in (c.get('genre') or [])]
    if sport:
        channels = [c for c in channels if sport in sports.kinds(c)]
    if params.getValue('solar') and section in ('webcam', 'weather'):
        from resources.lib.livestreams import webcam_now
        channels = webcam_now.group_channels(channels).get(params.getValue('solar'), [])
    if params.getValue('weatherKind') and section in ('webcam', 'weather'):
        from resources.lib.livestreams import webcam_weather
        channels = webcam_weather.group_channels(channels).get(params.getValue('weatherKind'), [])
    return sorted(channels, key=lambda channel: channel['name'].casefold())


def _epg_link(params):
    filters = {key: params.getValue(key) for key in ('section', 'country', 'genre', 'sport', 'city')
               if params.getValue(key)}
    _folder(_label(32307, 'EPG – diese Sender'), 'epg', filters, 'epg.png')


def _channels_filtered(params):
    oGui = cGui()
    channels = _filtered_channels(params)
    if not channels:
        _empty_state(oGui)
    elif params.getValue('section') in ('tv', 'sports'):
        _epg_link(params)
    for channel in channels:
        _channel_item(oGui, channel)
    oGui.setEndOfDirectory()


def _sport_kinds(params):
    oGui = cGui()
    present = {kind for channel in catalog.channels_by_section('sports') for kind in sports.kinds(channel)}
    for kind in sports.SPORT_IDS:
        if kind in present:
            _folder(sports.label(kind), 'channels', {'section': 'sports', 'sport': kind}, 'sports.png')
    if not present:
        _empty_state(oGui)
    oGui.setEndOfDirectory()


def _show_epg(params):
    oGui = cGui()
    channels = _filtered_channels(params)
    if not channels:
        _empty_state(oGui)
    for channel in channels:
        line = _epg_line(channel) or _label(32310, 'Keine Programmdaten verfügbar')
        element = cGuiElement('%s  –  %s' % (channel['name'], line), SITE_IDENTIFIER, 'route')
        element.setInfo(line)
        element.setThumbnail(channel.get('logo') or _art('epg.png'))
        child = ParameterHandler()
        child.setParam('lsLevel', 'detail')
        child.setParam('channel', channel['id'])
        oGui.addFolder(element, child)
    oGui.setEndOfDirectory()


def _guide_path():
    try:
        return export.guide_path()
    except Exception:
        return ''


def _epg_line(channel):
    guide = _guide_path()
    if not guide or not (channel.get('epg_id') or channel.get('epg_ids')):
        return ''
    for identifier in channel.get('epg_ids') or [channel['epg_id']]:
        if not identifier:
            continue
        line = epg.now_next_line(guide, identifier)
        if line:
            return line
    return ''


def _channel_item(oGui, channel):
    """Ein Kanal in der Liste.

    Standardweg: der Kanal oeffnet die Senderdetailansicht (empfohlene Quelle
    + zulaessige Varianten + EPG). Bei genau einer Variante und ohne EPG ist
    der schnelle Direktweg sinnvoller: der Kanal ist dann direkt abspielbar.
    """
    approved = catalog.approved_sources(channel)
    source = selector.order_sources(channel, approved)[0] if approved else None
    info = selector.describe(source) if source else ''
    epg_line = _epg_line(channel)

    open_detail = len(approved) > 1 or bool(epg_line) \
        or cConfig().getSetting('hosterSelect') == 'List'
    if open_detail:
        element = cGuiElement(channel['name'], SITE_IDENTIFIER, 'route')
        if info:
            element.setInfo(('%s  %s' % (info, epg_line)).strip())
        params = ParameterHandler()
        params.setParam('lsLevel', 'detail')
        params.setParam('channel', channel['id'])
        if channel.get('logo'):
            element.setThumbnail(channel['logo'])
        oGui.addFolder(element, params)
        return

    element = cGuiElement(channel['name'], SITE_IDENTIFIER, 'play')
    element.setMediaType('video')
    if channel.get('logo'):
        element.setThumbnail(channel['logo'])
    if info:
        element.setInfo(info)
    params = ParameterHandler()
    params.setParam('channel', channel['id'])
    oGui.addFolder(element, params, bIsFolder=False)


def show_detail(params):
    """Senderdetailansicht: empfohlene Quelle + zulaessige Varianten + EPG."""
    oGui = cGui()
    channel = catalog.get_channel(params.getValue('channel'))
    if not channel:
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return

    epg_line = _epg_line(channel)
    guide = _guide_path()
    stand = epg.guide_timestamp(guide) if guide else ''
    if epg_line or stand:
        info = cGuiElement((epg_line + ('   [%s]' % stand if stand else '')).strip(),
                           SITE_IDENTIFIER, '')
        info.setThumbnail(channel.get('logo') or _art('epg.png'))
        oGui.addFolder(info, ParameterHandler(), bIsFolder=False)

    ordered = selector.order_sources(channel, catalog.approved_sources(channel))

    # Empfohlene Quelle (beste) - ein Klick, mit Failover.
    if ordered:
        rec = cGuiElement('%s  %s' % (_label(31230, '> Empfohlene Quelle abspielen'),
                                      selector.describe(ordered[0])),
                          SITE_IDENTIFIER, 'play')
        rec.setMediaType('video')
        if channel.get('logo'):
            rec.setThumbnail(channel['logo'])
        rp = ParameterHandler()
        rp.setParam('channel', channel['id'])
        oGui.addFolder(rec, rp, bIsFolder=False)

    # Alle zulaessigen Varianten einzeln, mit ehrlicher DRM/Login/Geo-Markierung.
    for source in ordered:
        title = '%s  -  %s' % (source.get('display_name') or source.get('publisher') or channel['name'],
                               selector.describe(source))
        marks = []
        if source.get('geo_restricted'):
            marks.append(_label(31231, 'Geo'))
        if source.get('drm'):
            marks.append('DRM')
        if source.get('login_required'):
            marks.append('Login')
        if marks:
            title += '  [%s]' % '/'.join(marks)
        element = cGuiElement(title, SITE_IDENTIFIER, 'play')
        element.setMediaType('video')
        if channel.get('logo'):
            element.setThumbnail(channel['logo'])
        item_params = ParameterHandler()
        item_params.setParam('channel', channel['id'])
        item_params.setParam('source', source['source_id'])
        oGui.addFolder(element, item_params, bIsFolder=False)
    oGui.setEndOfDirectory()


def show_sources(params):
    """Alle Quellen eines Kanals einzeln - manuelle Wahl (Aufgabe 3c)."""
    oGui = cGui()
    channel = catalog.get_channel(params.getValue('channel'))
    if not channel:
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return
    for source in selector.order_sources(channel, catalog.approved_sources(channel)):
        title = '%s  -  %s' % (channel['name'], selector.describe(source))
        element = cGuiElement(title, SITE_IDENTIFIER, 'play')
        element.setMediaType('video')
        if channel.get('logo'):
            element.setThumbnail(channel['logo'])
        item_params = ParameterHandler()
        item_params.setParam('channel', channel['id'])
        item_params.setParam('source', source['source_id'])
        oGui.addFolder(element, item_params, bIsFolder=False)
    oGui.setEndOfDirectory()


def _playable_url(source):
    """Adresse zum Abspielen; Pluto-Quellen bekommen erst hier ihre Sitzung."""
    if source.get('resolver') == 'pluto':
        from resources.lib.livestreams.providers import pluto
        return pluto.resolve_url(pluto.channel_id_from_url(source['url'])) or source['url']
    return source['url']


def _list_item_for(channel, source):
    """ListItem je nach Protokoll aufbauen. Unterstuetzt werden die vom Addon
    sauber abspielbaren Arten: HLS/DASH (inputstream.adaptive) und RTSP
    (inputstream.rtsp). MJPEG wird best-effort direkt versucht; JPEG-Standbilder
    laufen ueber die Slideshow (siehe play()), nicht hierueber.
    """
    protocol = source['protocol']
    url = _playable_url(source)
    list_item = xbmcgui.ListItem(path=url)
    if protocol in ('hls', 'dash'):
        list_item.setProperty('inputstream', 'inputstream.adaptive')
        if protocol == 'dash':
            list_item.setMimeType('application/dash+xml')
        else:
            list_item.setMimeType('application/vnd.apple.mpegurl')
        if source.get('headers'):
            header = urlencode(source['headers'])
            list_item.setProperty('inputstream.adaptive.stream_headers', header)
            list_item.setProperty('inputstream.adaptive.manifest_headers', header)
        list_item.setContentLookup(False)
    elif protocol == 'rtsp':
        # Kodi/VideoPlayer spielt RTSP; inputstream.rtsp wird genutzt, falls da.
        if xbmc.getCondVisibility('System.HasAddon(inputstream.rtsp)'):
            list_item.setProperty('inputstream', 'inputstream.rtsp')
        list_item.setContentLookup(False)
    elif protocol in ('udp', 'rtp'):
        # MagentaTV multicast carries MPEG-TS directly; Kodi's VideoPlayer
        # opens it through FFmpeg, without an adaptive inputstream addon.
        list_item.setMimeType('video/mp2t')
        list_item.setContentLookup(False)
    # mjpeg/mp4: Direktpfad ohne Sonderbehandlung (best effort).
    vtag = list_item.getVideoInfoTag()
    try:
        vtag.setMediaType('video')
        vtag.setTitle(str(channel['name']))
    except Exception:
        pass
    if channel.get('logo'):
        list_item.setArt({'thumb': channel['logo'], 'icon': channel['logo']})
    list_item.setProperty('IsPlayable', 'true')
    return list_item


def _play_channel(channel, forced_source_id=None, use_resolve=True):
    """Gemeinsamer Wiedergabekern: beste Quelle zuerst, Failover nur bei
    Fehlstart. ``use_resolve`` steuert, ob die erste Quelle ueber die
    aufgerufene Directory-Aktion aufgeloest wird (Klick) oder direkt gestartet
    wird (RunPlugin/Keymap, z.B. Rabbithole-„Weiter").
    """
    approved = catalog.approved_sources(channel)
    ordered = selector.order_sources(channel, approved)
    if forced_source_id:
        ordered = [s for s in ordered if s['source_id'] == forced_source_id] or ordered

    # JPEG-Standbild-Kameras laufen als Slideshow, nicht ueber den VideoPlayer.
    if ordered and ordered[0]['protocol'] == 'jpeg' and not ordered[0].get('resolver'):
        if use_resolve:
            _resolve_fail()  # kein Video aufzuloesen
        _play_jpeg_slideshow(channel, ordered[0])
        return True

    handle = cGui().pluginHandle
    from resources.lib.player import cPlayer

    resolved = False
    for index, source in enumerate(ordered):
        if source.get('resolver') == 'webcam_page':
            from resources.lib.livestreams import webcam_extract
            source = webcam_extract.resolve_source(source)
            if not source:
                continue
            if source['protocol'] == 'jpeg':
                if use_resolve:
                    _resolve_fail()
                _play_jpeg_slideshow(channel, source)
                return True
        list_item = _list_item_for(channel, source)
        logger.info('-> [livestreams.route]: play %s Quelle %s (%d/%d)'
                    % (channel['name'], source['source_id'], index + 1, len(ordered)))
        if use_resolve and not resolved and handle > 0:
            xbmcplugin.setResolvedUrl(handle, True, list_item)
            resolved = True
        else:
            xbmc.Player().play(list_item.getPath(), list_item)
        if cPlayer().startPlayer():
            selector.mark_ok(channel['id'], source['source_id'])
            return True
        selector.mark_failed(channel['id'], source['source_id'])
        if index + 1 < len(ordered):
            _notify(_label(31213, 'Quelle nicht erreichbar - versuche naechste'))
    if use_resolve and not resolved:
        _resolve_fail()
    _notify(_label(31214, 'Keine Quelle spielbar'))
    return False


def play(params):
    """Kanal abspielen (Klick/aufgeloester Directory-Eintrag)."""
    channel_id = params.getValue('channel')
    if channel_id == '__rabbithole__':
        _rabbithole_play(use_resolve=True)
        return
    channel = catalog.get_channel(channel_id)
    if not channel:
        logger.error('-> [livestreams.route]: play: Kanal nicht sichtbar/freigegeben')
        _resolve_fail()
        return
    _play_channel(channel, params.getValue('source') or None, use_resolve=True)


def _notify(text):
    xbmc.executebuiltin('Notification(%s,%s,4000,%s)'
                        % ('Baka', text, cConfig().getAddonInfo('icon')))


def _resolve_fail():
    handle = cGui().pluginHandle
    if handle > 0:
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())


def _play_jpeg_slideshow(channel, source):
    """Standbild-Kamera als sich auffrischende Vollbildanzeige (Aufgabe 6d).

    Kodi kann ein einzelnes JPEG nicht als Video loopen; wir zeigen das Bild
    per ShowPicture und laden es in einem beschraenkten Intervall neu, bis der
    Nutzer abbricht. Speicherschonend: kein Puffer, nur ein Bild.
    """
    interval = max(3, cConfig().getSettingInt('lsWebcamRefresh', 10))
    monitor = xbmc.Monitor()
    _notify('%s (%s)' % (channel['name'], _label(31220, 'Standbild-Modus')))
    if monitor.abortRequested():
        return
    # Wait until Kodi has opened the picture window before checking it.
    # Stop/Back closes that window; it does not request Kodi shutdown.
    def picture_command(url):
        if source.get('cache_bust'):
            url += ('&' if '?' in url else '?') + '_baka_ts=' + str(time.time_ns())
        return 'ShowPicture(%s)' % url
    command = picture_command(source['url'])
    xbmc.executebuiltin(command, True)
    next_refresh = time.monotonic() + interval
    while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(slideshow)'):
        remaining = next_refresh - time.monotonic()
        if remaining <= 0:
            if source.get('resolver_page'):
                from resources.lib.livestreams import webcam_extract
                fresh = webcam_extract.resolve(source['resolver_page'])
                if not fresh or fresh['protocol'] != 'jpeg':
                    break
                if monitor.abortRequested() or not xbmc.getCondVisibility('Window.IsActive(slideshow)'):
                    break
                command = picture_command(fresh['url'])
            elif source.get('cache_bust'):
                command = picture_command(source['url'])
            xbmc.executebuiltin(command, True)
            next_refresh = time.monotonic() + interval
        elif monitor.waitForAbort(min(0.25, remaining)):
            break


def _rabbithole_play_item(oGui):
    """Abspielbarer Eintrag, der die Rabbithole-Session startet."""
    element = cGuiElement(_label(31221, 'Rabbithole (zufaellige Webcam)'),
                          SITE_IDENTIFIER, 'play')
    element.setMediaType('video')
    element.setThumbnail(_art('sources.png'))
    params = ParameterHandler()
    params.setParam('channel', '__rabbithole__')
    oGui.addFolder(element, params, bIsFolder=False)


def _rabbithole_play(use_resolve, reshuffle=False):
    """Naechste, in dieser Session noch nicht gezeigte, zufaellige Webcam.

    Bei Erschoepfung: klare Meldung, danach auf Wunsch neu mischen. Es werden
    ausschliesslich sichtbare, freigegebene, kategoriegefilterte Kanaele
    verwendet (keine versteckten Eintraege als Zufallsquelle).
    """
    from resources.lib.livestreams import rabbithole
    session = rabbithole.default_session()
    if reshuffle:
        session.reshuffle()

    cid = session.next()
    if cid is None:
        if use_resolve:
            _resolve_fail()
        # Pool leer oder erschoepft?
        if not rabbithole.visible_pool_ids():
            _notify(_label(31200, 'Nichts verfuegbar'))
            return
        import xbmcgui
        if xbmcgui.Dialog().yesno('Baka', _label(31240, 'Alle gezeigt. Neu mischen?')):
            _rabbithole_play(use_resolve, reshuffle=True)
        return

    channel = catalog.get_channel(cid)
    if not channel:
        # Katalog hat sich geaendert; einfach den naechsten versuchen.
        _rabbithole_play(use_resolve)
        return
    _play_channel(channel, None, use_resolve=use_resolve)


def rabbithole_next(params):
    """Einstieg fuer Keymap/RunPlugin: naechste Rabbithole-Webcam abspielen."""
    action = params.getValue('action') or 'next'
    _rabbithole_play(use_resolve=False, reshuffle=(action == 'reshuffle'))


def rabbithole_list(params):
    """250 zufaellige Webcams als Liste (Aufgabe 8b)."""
    import random
    oGui = cGui()
    pool = [c for c in catalog.visible_channels()
            if c['section'] in ('webcam', 'weather')]
    if not pool:
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return
    count = cConfig().getSettingInt('randomItemsCount', 250)
    sample = random.sample(pool, min(count, len(pool)))
    for channel in sample:
        _channel_item(oGui, channel)
    oGui.setEndOfDirectory()


def weather(params):
    """Wetter-Bereich: Live-Wetterzeilen (mehrere Quellen) + Wetter-Webcams.

    Wetter-Webcams werden nach Land gruppiert, wenn mehrere Laender vorkommen;
    sonst direkt gelistet. Fehlt beides, sauberer Empty State.
    """
    oGui = cGui()
    from resources.lib.livestreams.providers import weather as weather_provider
    from resources.lib.livestreams import webcam_now

    # Live-Wetterzeilen je konfigurierter Stadt (Open-Meteo keyless / OWM).
    lines = weather_provider.city_lines()
    for line in lines:
        info = cGuiElement(line, SITE_IDENTIFIER, '')
        info.setThumbnail(_art('weather.png'))
        oGui.addFolder(info, ParameterHandler(), bIsFolder=False)

    channels = catalog.channels_by_section('weather')
    has_world_weather = any(webcam_now.coordinates(channel)
                            for channel in catalog.channels_by_section('webcam'))
    countries = contentgate.get_visible_countries(
        [c for c in (ch.get('country') for ch in channels) if c])

    if not lines and not channels and not has_world_weather:
        _empty_state(oGui)
        oGui.setEndOfDirectory()
        return

    if has_world_weather:
        _folder(_label(32959, 'Weather right now'), 'weather_world',
                {'section': 'webcam'}, 'weather.png')
    if channels:
        _folder(_label(32918, 'Nach Kontinent, Land und Stadt'), 'continents',
                {'section': 'weather'}, 'countries.png')
        _folder(_label(32919, 'Alle Wetterstationen'), 'channels', {'section': 'weather'}, 'weather.png')
        _folder(_label(32925, 'Themes'), 'wcategories', {'section': 'weather'}, 'genre.png')
    oGui.setEndOfDirectory()


# --- Social Media (delegierend an die offiziellen Plattform-Addons) --------

def _passthrough_item(oGui, title, url, is_folder, thumb=''):
    """Directory-Eintrag, der direkt auf eine plugin://-URL zeigt.

    Nutzt den vorhandenen sUrl-Passthrough in cGui: Ordner navigieren in das
    Ziel-Addon, abspielbare Eintraege werden vom Ziel-Addon aufgeloest. So
    laeuft Wiedergabe/Anmeldung komplett ueber das offizielle Addon.
    """
    element = cGuiElement(title, SITE_IDENTIFIER, '')
    if thumb:
        element.setThumbnail(thumb)
    if not is_folder:
        element.setMediaType('video')
    params = ParameterHandler()
    params.setParam('sUrl', url)
    oGui.addFolder(element, params, bIsFolder=is_folder)


def _info_item(oGui, text):
    element = cGuiElement(text, SITE_IDENTIFIER, '')
    element.setThumbnail(_art('social.png'))
    oGui.addFolder(element, ParameterHandler(), bIsFolder=False)


def _social(oGui):
    from resources.lib.livestreams import social
    from resources.lib.livestreams.providers import youtube, twitch

    for pid in social.enabled_platforms(cConfig()):
        if pid == 'youtube':
            if youtube.is_addon_installed():
                _folder('YouTube', 'yt_cats', {}, 'social.png')
            else:
                _info_item(oGui, _label(31310, 'YouTube-Addon nicht installiert (plugin.video.youtube)'))
        elif pid == 'twitch':
            if twitch.is_addon_installed():
                _folder('Twitch', 'tw_live', {}, 'social.png')
            else:
                _info_item(oGui, _label(31311, 'Twitch-Addon nicht installiert (plugin.video.twitch)'))

    # Zusaetzlich kuratierte Social-Kanaele aus dem Katalog (falls vorhanden).
    for channel in catalog.channels_by_section('social'):
        _channel_item(oGui, channel)


def yt_categories(params):
    from resources.lib.livestreams.providers import youtube
    oGui = cGui()
    # Ohne Key: einfach das YouTube-Addon oeffnen (Anonym-Browsing/Login dort).
    _passthrough_item(oGui, _label(31312, 'YouTube-Addon oeffnen'),
                      youtube.addon_root_url(), is_folder=True, thumb=_art('social.png'))
    if cConfig().getSetting('youtubeApiKey', ''):
        for slug, cat_id, sid, fallback in youtube.CATEGORIES:
            _folder(_label(sid, fallback), 'yt_live', {'ytcat': cat_id}, 'social.png')
    else:
        _info_item(oGui, _label(31313, 'Eigenen YouTube-API-Key in den Einstellungen fuer Kategorie-Filter'))
    oGui.setEndOfDirectory()


def yt_live(params):
    from resources.lib.livestreams.providers import youtube
    oGui = cGui()
    key = cConfig().getSetting('youtubeApiKey', '')
    region = cConfig().getSetting('youtubeRegion', '')
    entries = youtube.search_live(key, category_id=params.getValue('ytcat') or '',
                                  region_code=region) if key else []
    if not entries:
        _empty_state(oGui)
    for entry in entries:
        title = entry['title'] + (('  -  %s' % entry['channel']) if entry['channel'] else '')
        _passthrough_item(oGui, title, youtube.play_url(entry['video_id']),
                          is_folder=False, thumb=entry.get('thumb', ''))
    oGui.setEndOfDirectory()


def tw_live(params):
    from resources.lib.livestreams.providers import twitch
    oGui = cGui()
    client_id = cConfig().getSetting('twitchClientId', '')
    secret = cConfig().getSetting('twitchClientSecret', '')
    language = cConfig().getSetting('twitchLanguage', '')
    # Immer: Twitch-Addon direkt oeffnen.
    _passthrough_item(oGui, _label(31314, 'Twitch-Addon oeffnen'),
                      twitch.addon_root_url(), is_folder=True, thumb=_art('social.png'))
    entries = twitch.get_streams(client_id, secret, language) if client_id else []
    if not entries and not client_id:
        _info_item(oGui, _label(31315, 'Twitch-Client-ID in den Einstellungen fuer Live-Liste'))
    for entry in entries:
        title = '%s  -  %s' % (entry['display'], entry['title'])
        if entry.get('game'):
            title += '  [%s]' % entry['game']
        _passthrough_item(oGui, title, twitch.play_url(entry['channel']),
                          is_folder=False, thumb=entry.get('thumb', ''))
    oGui.setEndOfDirectory()


def run_refresh():
    export.refresh(force=True)
    _notify(_label(31215, 'Livestream-Listen aktualisiert'))


def run_export_hint():
    xbmcgui.Dialog().ok('Baka', export.config_hint())
