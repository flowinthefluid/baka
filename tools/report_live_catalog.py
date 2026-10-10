"""Generate the local broadcaster review list without Kodi or network access."""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resources.lib.livestreams import curation, model, sports


def main():
    raw = []
    imported = {}
    for path in sorted((ROOT / 'resources/livestreams/sources').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        raw.extend(data.get('channels', []))
        if path.name in ('tv_iptv_org_1080i.json', 'sports_iptv_org_de_en.json'):
            imported[path.name] = data
    rules = json.loads((ROOT / 'resources/livestreams/channel_merges.json').read_text(encoding='utf-8'))['approved']
    channels = curation.collapse([c for c in map(model.normalize_channel, raw) if c], rules)
    # Match the default rights/adult gate; personal country/genre settings
    # and dynamically fetched Pluto channels intentionally are not simulated.
    visible = [c for c in channels if c['nsfw'] is False and any(
        s['active'] and s['rights_status'] == model.RIGHTS_APPROVED for s in c['sources'])]
    tv = sorted((c for c in visible if c['section'] == 'tv'), key=lambda c: c['name'].casefold())
    sport = [c for c in visible if c['section'] == 'sports']
    lines = ['# Baka: lokale Senderliste', '',
        'Stand: %s. Nur lokale Änderungen; keine Übertragung auf die TV-Box.' % date.today().strftime('%d.%m.%Y'), '',
        '## Freigegebene Regionalgruppen', '',
        '| Anzeige | Hauptquelle (nur in Quelleninformationen) |', '|---|---|']
    lines += ['| %s | %s |' % (r['name'], r['primary_label']) for r in rules]
    lines += ['', 'Andere freigegebene Varianten bleiben als Ersatzquellen hinter dem Sender. '
        'ZDF, ZDFneo, ZDFinfo, ORF III, ORF Kids, SRF 1 und SRF zwei sind eigenständige Programme; '
        'sie werden nicht miteinander verschmolzen.', '',
        'Weitere lokale Programme wie die verschiedenen Offenen Kanäle, Regio TV und Sachsen Fernsehen '
        'werden nicht allein wegen eines ähnlichen Namens zusammengelegt. Für zusätzliche Regionalgruppen '
        'wäre eine eigene Freigabe nötig.', '',
        '## Fernsehen: Deutschland / Österreich / Schweiz', '',
        '%d sichtbare, mitgelieferte Sendereinträge nach dem Zusammenführen. '
        'Persönliche Filter und die dynamische Pluto-Liste können die Anzeige verändern.' % len(tv), '',
        '| Sender | Zuordnung | Aktive Quellen |', '|---|---|---:|']
    for c in tv:
        lines.append('| %s | %s | %d |' % (c['name'], ', '.join(c.get('countries') or [c['country']]).upper(),
                     sum(s['active'] and s['rights_status'] == model.RIGHTS_APPROVED for s in c['sources'])))
    lines += ['', '## Sport nach Sportarten', '',
        '%d sichtbare, mitgelieferte Sportsender insgesamt. Gemischte Sender stehen unter '
        '„Weitere / gemischte Sportarten“. Die neuen IPTV-org-Quellen werden anhand der tatsächlichen '
        'Feed-Sprache Deutsch/Englisch ausgewählt; das Herkunftsland allein reicht nicht aus.' % len(sport)]
    for kind, _, label, _pattern in sports.SPORTS:
        group = sorted((c for c in sport if kind in sports.kinds(c)), key=lambda c: c['name'].casefold())
        if group:
            lines += ['', '### ' + label, '', '| Sender | Sprache |', '|---|---|']
            lines += ['| %s | %s |' % (c['name'], ', '.join(c['language']).upper() or 'nicht angegeben') for c in group]
    tv_import = imported['tv_iptv_org_1080i.json']['channels']
    sport_import = imported['sports_iptv_org_de_en.json']['channels']
    lines += ['', '## Einrichtung und EPG', '',
        '- Drei unabhängige Sprachwahlen: Filme/Serien, Dokus, Animes. Reihenfolge: „Nicht anzeigen“, '
        '„Englisch“, „Deutsch“, danach die übrigen Sprachen.',
        '- Die Auswahl bleibt in Kodis Addon-Einstellungen gespeichert (`langSetupDone` und `langProfile_*`). '
        'Die Sprachabfrage erscheint nur einmal bei der Ersteinrichtung, nicht erneut bei Updates. '
        'Bestehende Einstellungen bleiben erhalten.',
        '- Nachträgliche Änderungen: Einstellungen → Sprachen & Regionen → Sprachen je Thema.',
        '- Anime: Deutsch sowie japanischer Originalton mit deutschen Untertiteln können gemeinsam ausgewählt werden. '
        'Englische Synchros werden dadurch nicht freigeschaltet. Quellen ohne Sprachangabe bleiben erkennbar ungefiltert.',
        '- Jede TV-/Sportsenderliste beginnt mit „EPG – diese Sender“. Die Ansicht verwendet genau dieselben Filter '
        'und die vorhandene XMLTV-Datei. Ohne konfigurierte XMLTV-Quelle oder passende Sendungsdaten erscheint '
        '„Keine Programmdaten verfügbar“.', '', '## Prüfstand', '',
        'Der aktuelle Import enthält %d DACH-Einträge mit %d Quellen und %d DE/EN-Sporteinträge mit %d Quellen, '
        % (len(tv_import), sum(len(c['sources']) for c in tv_import),
           len(sport_import), sum(len(c['sources']) for c in sport_import)) +
        'jeweils vor dem Zusammenführen mit dem bisherigen Katalog. HTTP-Stream-Playlists wurden am 10.10.2026 '
        'abgerufen. Das beweist keine Wiedergabe in Kodi und keine Verfügbarkeit aus jeder Region.', '',
        'Der [1080i-Filter](https://iptv-org.github.io/?q=format%3A1080i) betrifft die Sender-Metadaten. '
        'Die verfügbare Internetquelle kann eine andere Auflösung haben. '
        'Magenta-Multicast bleibt deaktiviert; NITRO verwendet die vom Nutzer bestätigte ANTIK-SD-Quelle.', '']
    target = ROOT / 'docs/SENDERLISTE-LOKAL.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    print('%s: %d TV, %d sports' % (target, len(tv), len(sport)))


if __name__ == '__main__':
    main()
