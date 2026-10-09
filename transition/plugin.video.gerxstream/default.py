# -*- coding: utf-8 -*-
# Python 3
"""GerXStream heisst jetzt Baka: leitet alte Links und Favoriten weiter.

Diese letzte GerXStream-Version setzt plugin.video.baka voraus, damit Kodi
Baka beim Update automatisch installiert. Baka uebernimmt die Daten beim
ersten Start selbst; hier wird nur weitergeleitet und einmal informiert.
"""

import os
import sys

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

NEW_ADDON_ID = 'plugin.video.baka'
NOTICE_MARKER = 'special://profile/addon_data/plugin.video.gerxstream/.baka_notice_shown'

MESSAGES = {
    'de': ('GerXStream heißt jetzt Baka',
           'Favoriten, Watchlist, Historie und Einstellungen wurden übernommen. '
           'Du findest Baka unter Video-Addons. Alte Links werden weitergeleitet; '
           'GerXStream kannst du deinstallieren, sobald keine alten Kodi-Favoriten mehr darauf zeigen.'),
    'en': ('GerXStream is now called Baka',
           'Favourites, watchlist, history and settings have been carried over. '
           'You will find Baka under video add-ons. Old links are forwarded; '
           'you can uninstall GerXStream once no old Kodi favourites point to it.'),
}


def _noticeOnce():
    marker = xbmcvfs.translatePath(NOTICE_MARKER)
    if os.path.exists(marker):
        return
    heading, message = MESSAGES['de' if xbmc.getLanguage(xbmc.ISO_639_1) == 'de' else 'en']
    xbmcgui.Dialog().ok(heading, message)
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, 'w', encoding='utf-8') as handle:
            handle.write('shown\n')
    except OSError:
        pass


def main():
    handle = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip('-').isdigit() else -1
    query = sys.argv[2] if len(sys.argv) > 2 else ''
    target = 'plugin://%s/%s' % (NEW_ADDON_ID, query)
    _noticeOnce()
    if handle < 0:
        # RunPlugin-Aufrufe, z.B. aus der Rabbithole-Tastenbelegung.
        xbmc.executebuiltin('RunPlugin(%s)' % target)
        return
    xbmcplugin.endOfDirectory(handle, succeeded=False, updateListing=False)
    xbmc.executebuiltin('Container.Update(%s,replace)' % target)


if __name__ == '__main__':
    main()
