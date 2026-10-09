# -*- coding: utf-8 -*-
# Python 3
"""Fruehere Addon-Kennungen und das Umschreiben gespeicherter Ziele.

Baka hiess bis 1.0.38 GerXStream (plugin.video.gerxstream), davor xStream.
Favoriten, Historie, Episoden-Warteschlangen und Sicherungen speichern
plugin://-Ziele mit der damaligen Kennung. Diese Ziele zeigen nach der
Uebernahme auf Baka, sonst wuerden sie am alten Addon haengen bleiben.
"""

CURRENT_ADDON_ID = 'plugin.video.baka'
# Neuester Vorgaenger zuerst: von ihm werden Daten bevorzugt uebernommen.
LEGACY_ADDON_IDS = ('plugin.video.gerxstream', 'plugin.video.xstream')
LEGACY_BACKUP_FORMATS = ('gerxstream-backup',)

_CURRENT_PREFIX = 'plugin://%s/' % CURRENT_ADDON_ID
_LEGACY_PREFIXES = tuple('plugin://%s/' % addon_id for addon_id in LEGACY_ADDON_IDS)


def rewriteTarget(value):
    """Ersetzt fruehere Addon-Kennungen in plugin://-Zielen eines Textes."""
    if isinstance(value, str):
        for prefix in _LEGACY_PREFIXES:
            value = value.replace(prefix, _CURRENT_PREFIX)
    return value


def rewriteTargets(data):
    """Schreibt alle plugin://-Ziele in verschachtelten JSON-Daten um."""
    if isinstance(data, dict):
        return {key: rewriteTargets(value) for key, value in data.items()}
    if isinstance(data, list):
        return [rewriteTargets(value) for value in data]
    return rewriteTarget(data)
