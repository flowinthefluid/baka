"""Belegte Dubletten zusammenfassen; Regionalgruppen nur nach Freigabe."""

import copy
import json
import os

DACH = ('de', 'at', 'ch')


def regional_rules():
    from resources.lib.config import cConfig
    from xbmcvfs import translatePath
    path = os.path.join(translatePath(cConfig().getAddonInfo('path')), 'resources', 'livestreams', 'channel_merges.json')
    try:
        with open(path, encoding='utf-8') as handle:
            return json.load(handle).get('approved', [])
    except (OSError, ValueError):
        return []


def _epg_key(channel):
    value = channel.get('epg_id') or ''
    base, _, feed = value.partition('@')
    generic = ('sd', 'hd', 'uhd', '4k')
    if channel['section'] == 'sports':
        generic += ('de', 'en', 'german', 'english')
    return base if feed.lower() in generic else value


def _merge(target, channel):
    urls = {source['url'] for source in target['sources']}
    for source in channel['sources']:
        if source['url'] not in urls:
            target['sources'].append(source)
            urls.add(source['url'])
        else:
            existing = next(s for s in target['sources'] if s['url'] == source['url'])
            if existing.get('quality') == 'unknown' and source.get('quality') != 'unknown':
                existing['quality'] = source['quality']
    if not target.get('epg_id'):
        target['epg_id'] = channel.get('epg_id', '')
    target['alias_ids'] = list(dict.fromkeys(target.get('alias_ids', [target['id']])
                                           + channel.get('alias_ids', [channel['id']])))
    for field, default in (('countries', 'country'), ('epg_ids', 'epg_id')):
        target[field] = list(dict.fromkeys(target.get(field, [target.get(default, '')])
                                          + channel.get(field, [channel.get(default, '')])))
    for field in ('language', 'genre', 'sport'):
        target[field] = list(dict.fromkeys(target.get(field, []) + channel.get(field, [])))
    if channel['id'] == 'gxs:tv:de:nitro':
        target['id'], target['name'] = channel['id'], channel['name']
    if channel.get('nsfw') is not False:
        target['nsfw'] = channel.get('nsfw')


def collapse(channels, rules=None):
    result, by_epg, by_url, by_identity = [], {}, {}, {}
    for original in channels:
        channel = copy.deepcopy(original)
        if channel['section'] not in ('tv', 'sports'):
            result.append(channel)
            continue
        epg = _epg_key(channel)
        identity = (channel['section'], channel.get('publisher'), channel['name'].casefold().strip())
        urls = [source['url'] for source in channel['sources'] if source.get('active', True)]
        matches = []
        if epg and (channel['section'], epg) in by_epg:
            matches.append(by_epg[channel['section'], epg])
        if identity in by_identity and not any(by_identity[identity] is item for item in matches):
            matches.append(by_identity[identity])
        for url in urls:
            known = by_url.get((channel['section'], url))
            if known is not None and not any(known is item for item in matches):
                matches.append(known)
        if not matches:
            target = channel
            result.append(target)
        else:
            target = matches[0]
            # A new feed can connect two earlier groups. Keep one identity
            # and redirect all lookup keys, including keys of former aliases.
            for duplicate in matches[1:]:
                _merge(target, duplicate)
                result.remove(duplicate)
                for index in (by_epg, by_url, by_identity):
                    for key, value in list(index.items()):
                        if value is duplicate:
                            index[key] = target
            _merge(target, channel)
        if epg:
            by_epg[channel['section'], epg] = target
        by_identity[identity] = target
        for url in urls:
            by_url[channel['section'], url] = target
    for rule in regional_rules() if rules is None else rules:
        members = [channel for channel in result if channel['id'] in rule['members']
                   or set(channel.get('alias_ids', [])) & set(rule['members'])]
        if not members:
            continue
        primary = next((channel for channel in members if channel['id'] == rule['primary']), members[0])
        for source in primary['sources']:
            source['regional_label'] = rule.get('primary_label', primary['name'])
        primary['name'] = rule['name']
        for member in members:
            if member is primary:
                continue
            for source in member['sources']:
                source['priority'] = max(1, source.get('priority', 0))
                source['display_name'] = source.get('display_name') or member['name']
                source['regional_label'] = member['name']
            _merge(primary, member)
            result.remove(member)
    return result
