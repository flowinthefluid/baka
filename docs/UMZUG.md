# Geplanter Umzug zu Baka

Ein separates Kodi-Programm-Addon mit der vorgesehenen ID `script.baka.migration`
soll vorhandene Daten aus `plugin.video.gerxstream` und `plugin.video.xstream`
nach `plugin.video.baka` übertragen. Es ist noch nicht veröffentlicht. Baka selbst
startet derzeit keine automatische Übernahme und sein Sicherungsimport akzeptiert
das Format `baka-backup`.

## Veröffentlichung

Das Umzugs-Addon kann im selben GitHub-Repository auf `main` liegen, beispielsweise
unter `addons/script.baka.migration/`. Es erhält eine eigene Versionsnummer,
`addon.xml` und ZIP. Der Repository-Build muss es zusätzlich in den vorhandenen
Baka-Katalog aufnehmen. Nutzer installieren es dann aus demselben Kodi-Repository
unter **Programm-Addons**. Dafür werden weder ein weiteres Repository-Addon noch
ein eigener dauerhafter Branch benötigt. Baka und das Umzugs-Addon lassen sich
unabhängig aktualisieren.

Der Zweig `umzug-gerxstream` enthält früheren Übernahmecode als Ausgangspunkt.
Er ist keine bereits geprüfte, installierbare Umzugslösung für die aktuelle Version.

## Vorgesehener Ablauf

1. GerXStream- und xStream-Profile erkennen; bei mehreren Profilen die Quelle wählen.
2. Übertragbare Bereiche und vorhandene Baka-Daten anzeigen. Einstellungen,
   Favoriten/Watchlists, Historie und Gesehen-Markierungen getrennt auswählen;
   Konten nur nach ausdrücklicher Auswahl übernehmen.
3. Vor Änderungen den aktuellen Baka-Stand lokal sichern. Alte Profile erhalten.
4. Daten konvertieren und prüfen, anschließend den angezeigten Umfang übernehmen.
   Bestehende Baka-Daten werden erst nach entsprechender Bestätigung ersetzt oder
   zusammengeführt. Unbekannte oder beschädigte Formate führen zu einer Meldung.
5. Ergebnis je Bereich anzeigen und gegebenenfalls einen Kodi-Neustart anfordern.

## Was die Umsetzung prüfen muss

| Bereich | Erforderliche Verarbeitung |
| --- | --- |
| Einstellungen | Nur vorhandene Baka-Einstellungs-IDs übernehmen; umbenannte GerXStream-IDs zuordnen; alte Sprachwahl auf die heutigen Sprachprofile abbilden. Einstellungen über Kodis Addon-API setzen, damit Kodi keine kopierte Datei überschreibt. |
| Favoriten und Watchlists | Datenformat und Ordnerstruktur validieren; gespeicherte Plugin-Routen und eingebettete Ziele auf Baka umschreiben; Serien-/Episodenbezug erhalten. |
| Historie und Gesehen-Status | Format und IDs prüfen, veraltete Anbieterziele konvertieren, vorhandene Daten nach einer festgelegten Konfliktregel behandeln. |
| Konten | Nur kompatible Felder auf Wunsch übertragen; Zugangsdaten nicht protokollieren. |
| xStream | Die tatsächlich unterstützten xStream-Versionen und Speicherformate zuerst prüfen. Ein Austausch der Addon-ID allein belegt keine Kompatibilität. |
| Caches und temporäre Daten | Neu aufbauen; alte Caches, Queue-Kennungen und gerätespezifische Pfade nicht pauschal kopieren. |

Vor Veröffentlichung sind Tests mit repräsentativen GerXStream-/xStream-Profilen,
vorhandenen Baka-Daten, wiederholtem Aufruf, Abbruch, beschädigten Dateien und
einem tatsächlichen Kodi-Aufruf erforderlich. Der bisherige automatische Kopierer
darf dafür nicht ungeprüft wieder aktiviert werden.
