# -*- coding: utf-8 -*-
"""GerXStream -> Baka: Daten, Sicherungen und alte Links bleiben nutzbar."""

import importlib.util
import json
import os
import sys
from pathlib import Path

from resources.lib import backup, legacy, tools
from resources.lib.config import cConfig

ROOT = Path(__file__).resolve().parents[1]


def _special_paths(monkeypatch, tmp_path):
    def translate(path):
        if path.startswith('special://'):
            return os.path.join(str(tmp_path), path.split('://', 1)[1])
        return path

    monkeypatch.setattr(tools, 'translatePath', translate)
    return tmp_path / 'home' / 'userdata' / 'addon_data'


def test_legacy_targets_are_rewritten_everywhere():
    data = {'target': 'plugin://plugin.video.gerxstream/?site=a',
            'nested': [{'action': 'Container.Update(plugin://plugin.video.xstream/?b=1,replace)'}],
            'count': 3, 'other': 'plugin://plugin.video.youtube/?c=1'}
    assert legacy.rewriteTargets(data) == {
        'target': 'plugin://plugin.video.baka/?site=a',
        'nested': [{'action': 'Container.Update(plugin://plugin.video.baka/?b=1,replace)'}],
        'count': 3, 'other': 'plugin://plugin.video.youtube/?c=1'}


def test_gerxstream_backups_stay_importable():
    payload = {'format': 'gerxstream-backup', 'format_version': 1, 'sections': {
        'epic_favorites': {'items': [{'target': 'plugin://plugin.video.gerxstream/?site=a'}]}}}
    decoded = backup._decodePayload(json.dumps(payload))
    assert decoded['sections']['epic_favorites']['items'][0]['target'] == 'plugin://plugin.video.baka/?site=a'
    assert backup._decodePayload(json.dumps(dict(payload, format='unknown-backup'))) is None
    assert backup._backupFilename('gerxstream-portable-20261009-120000-abcdef12.json')
    assert backup._backupFilename('baka-portable-20261009-120000-abcdef12.json')
    assert not backup._backupFilename('other-portable-20261009-120000-abcdef12.json')


def test_first_start_takes_over_gerxstream_data_once(monkeypatch, tmp_path):
    data = _special_paths(monkeypatch, tmp_path)
    old = data / 'plugin.video.gerxstream'
    (old / 'htmlcache').mkdir(parents=True)
    (old / 'htmlcache' / 'page').write_text('cache')
    (old / 'pluginDB').write_text('{"site": {"icon": "special://home/addons/plugin.video.gerxstream/x.png"}}')
    (old / '.gerxstream_data_migrated').write_text('old marker')
    (old / 'epic_favorites.json').write_text(json.dumps(
        {'items': [{'title': 'Carrie', 'target': 'plugin://plugin.video.gerxstream/?site=a'}]}))
    (old / 'backups').mkdir()
    (old / 'backups' / 'manual.json').write_text('{"x": 1}')
    (old / 'settings.xml').write_text(
        '<settings version="2"><setting id="prefLanguage">1</setting>'
        '<setting id="cacheTime" default="true">360</setting>'
        '<setting id="gerxstream.trailer">true</setting></settings>')
    (data / 'plugin.video.xstream').mkdir()
    (data / 'plugin.video.xstream' / 'xstream_only.json').write_text('[]')
    keymaps = tmp_path / 'profile' / 'keymaps'
    keymaps.mkdir(parents=True)
    (keymaps / 'gerxstream-rabbithole.xml').write_text(
        '<down>RunPlugin(plugin://plugin.video.gerxstream/?function=livestreamsRabbithole)</down>')

    assert tools.migrateLegacyAddonData()

    new = data / 'plugin.video.baka'
    favorites = json.loads((new / 'epic_favorites.json').read_text())
    assert favorites['items'][0]['target'] == 'plugin://plugin.video.baka/?site=a'
    assert (new / 'backups' / 'manual.json').exists()
    for skipped in ('pluginDB', 'htmlcache', 'settings.xml', '.gerxstream_data_migrated', 'xstream_only.json'):
        assert not (new / skipped).exists()
    assert cConfig().getSetting('prefLanguage') == '1'
    assert cConfig().getSetting('gerxstream.trailer') == 'true'
    assert cConfig().getSetting('cacheTime') == ''
    assert not (keymaps / 'gerxstream-rabbithole.xml').exists()
    assert 'plugin://plugin.video.baka/' in (keymaps / 'baka-rabbithole.xml').read_text()

    cConfig().setSetting('prefLanguage', '2')
    assert not tools.migrateLegacyAddonData()
    assert cConfig().getSetting('prefLanguage') == '2'


def test_first_start_without_predecessor_only_marks_migration(monkeypatch, tmp_path):
    data = _special_paths(monkeypatch, tmp_path)
    assert not tools.migrateLegacyAddonData()
    assert (data / 'plugin.video.baka' / tools.ADDON_DATA_MIGRATION_MARKER).exists()


def test_transition_addon_forwards_old_links(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        'gerxstream_transition', ROOT / 'transition' / 'plugin.video.gerxstream' / 'default.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls, ended, dialogs = [], [], []
    monkeypatch.setattr(module.xbmc, 'executebuiltin', calls.append)
    monkeypatch.setattr(module.xbmc, 'getLanguage', lambda *args: 'de', raising=False)
    monkeypatch.setattr(module.xbmc, 'ISO_639_1', 0, raising=False)
    monkeypatch.setattr(module.xbmcvfs, 'translatePath', lambda path: str(tmp_path / 'notice'), raising=False)
    monkeypatch.setattr(module.xbmcgui.Dialog, 'ok', lambda self, *args: dialogs.append(args), raising=False)
    monkeypatch.setattr(module.xbmcplugin, 'endOfDirectory',
                        lambda handle, **kwargs: ended.append((handle, kwargs)), raising=False)

    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '5', '?site=kinox&function=load'])
    module.main()
    assert calls == ['Container.Update(plugin://plugin.video.baka/?site=kinox&function=load,replace)']
    assert ended == [(5, {'succeeded': False, 'updateListing': False})]
    assert dialogs and dialogs[0][0] == 'GerXStream heißt jetzt Baka'

    calls.clear()
    monkeypatch.setattr(sys, 'argv', ['plugin://plugin.video.gerxstream/', '-1',
                                      '?function=livestreamsRabbithole&action=next'])
    module.main()
    assert calls == ['RunPlugin(plugin://plugin.video.baka/?function=livestreamsRabbithole&action=next)']
    assert len(dialogs) == 1
