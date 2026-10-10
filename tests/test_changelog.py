"""Release-note selection follows Kodi's UI, independently of audio profiles."""

from pathlib import Path
import re

import pytest

from resources.lib import tools
from resources.lib.config import cConfig


@pytest.mark.parametrize('language,expected', [('de', 'DE'), ('en', 'EN'), ('fr', 'EN')])
def test_changelog_uses_interface_language(tmp_path, monkeypatch, language, expected):
    (tmp_path / 'changelog.txt').write_text('EN', encoding='utf-8')
    german = tmp_path / 'resources/language/resource.language.de_de/changelog.txt'
    german.parent.mkdir(parents=True)
    german.write_text('DE', encoding='utf-8')
    monkeypatch.setattr(cConfig, 'getAddonInfo', lambda self, key: str(tmp_path) if key == 'path' else '1.1.2')
    monkeypatch.setattr(tools.xbmc, 'ISO_639_1', 0, raising=False)
    monkeypatch.setattr(tools.xbmc, 'getLanguage', lambda fmt: language, raising=False)
    shown = []
    monkeypatch.setattr(tools, 'textBox', lambda heading, text: shown.append(text))
    cConfig().setSetting('langAudioAllowed', 'en')
    tools.changelog()
    tools.changelog()
    assert shown == [expected]


def test_changelog_falls_back_when_translation_missing(tmp_path, monkeypatch):
    (tmp_path / 'changelog.txt').write_text('English fallback', encoding='utf-8')
    monkeypatch.setattr(cConfig, 'getAddonInfo', lambda self, key: str(tmp_path) if key == 'path' else '1.1.2')
    monkeypatch.setattr(tools.xbmc, 'ISO_639_1', 0, raising=False)
    monkeypatch.setattr(tools.xbmc, 'getLanguage', lambda fmt: 'de', raising=False)
    shown = []
    monkeypatch.setattr(tools, 'textBox', lambda heading, text: shown.append(text))
    tools.changelog()
    assert shown == ['English fallback']


def test_translated_history_retains_all_versions_and_sections():
    root = Path(__file__).resolve().parents[1]
    en = (root / 'changelog.txt').read_text(encoding='utf-8')
    de = (root / 'resources/language/resource.language.de_de/changelog.txt').read_text(encoding='utf-8')
    headings = r'^\[B\]Version: ([\d.]+)'
    assert re.findall(headings, en, re.M) == re.findall(headings, de, re.M)
    assert len(re.findall(r'^- ', en, re.M)) == len(re.findall(r'^- ', de, re.M))
