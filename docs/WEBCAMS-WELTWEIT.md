# Mit Baka um die Welt

Unter **Live → Webcams** führen zwei Wege zu den Kameras:

- **Kontinent → Land → Stadt/Standort:** Orte auf allen sieben Kontinenten.
- **Themen:** unter anderem Berge, Rocky Mountains, Strände, Häfen, Tiere,
  Städte, Seen, Flüsse, Wasserfälle und Vulkane.

Dieselbe Kamera darf in mehreren Themen stehen. Der Ortsweg und die Themen
verweisen auf ihren gemeinsamen Eintrag. Nachweislich identische Player werden
zusammengeführt; unterschiedliche Blickwinkel bleiben erhalten.
Die Filmsprachen und Film-Länderauswahl schränken diese Weltreise nicht ein.

## Verzeichnisse und Wiedergabe

Der Katalog übernimmt öffentliche Kameraseiten aus
[WorldCam](https://worldcam.eu/),
[SkylineWebcams](https://www.skylinewebcams.com/),
[Panoramablick](https://www.panoramablick.com/),
[EarthCam](https://www.earthcam.com/) und
[LiveWorldWebcams](https://liveworldwebcams.com/).
Die Verzeichnisadressen bleiben zur Herkunftskontrolle gespeichert.
Explizit verlinkte Betreiber und eingebettete Player werden berücksichtigt.

HLS-Streams und Videos laufen im Videoplayer. Kameras mit Einzelbildern
erscheinen als automatisch aktualisierte Vollbildansicht. Stop/Zurück beendet
die Ansicht, auch wenn gerade ein neues Bild angefordert wird.
YouTube-Kameras verwenden das offizielle Kodi-Addon **plugin.video.youtube**;
es muss installiert und funktionsfähig eingerichtet sein.

Viele Stream-Adressen enthalten kurzlebige Sitzungstoken. Baka liest die
aktuelle Adresse erst beim Öffnen der Kamera aus. Vorschaubilder, historische
Filmaufnahmen und normale Verzeichnislinks werden nicht als Livekameras
übernommen. Browsergebundene Player ohne auslesbare Medienquelle bleiben aus.

## Offizielle Wetterstationen

Im Bereich **Wetter** erscheinen Kameras nur mit einer ausdrücklich belegten
Stationszuordnung. Name und Betreiber-Nachweis gehören zum Datensatz.
Ein Wetterwidget, Temperaturtext oder der Name „Wetter-Webcam“ reicht nicht.

Das [Sonnblick-Observatorium](https://www.geosphere.at/de/daten/datengrundlage/observatorien)
ist eine meteorologische Station der GeoSphere Austria. Der Betreiber
[führt seine Kameras als wissenschaftliches Monitoring](https://www.sonnblick.net/de/daten/webcams/).
Die Sonnblick-Kamera erscheint bei Wetter und bei den Webcams.
Die Zugspitzbahn-Panoramakamera bleibt unter Webcams; ihre bisherige interne ID
bleibt für vorhandene Favoriten erhalten.

## Umfang und Prüfung

Der gesammelte Stand enthält **3.305 unterschiedliche Kameraeinträge** nach
Zusammenführung, verteilt auf **115 Länder/Gebiete** und alle sieben Kontinente.
Bewegliche Kameras kommen unter „Weitere Standorte“ hinzu. Die fünf neuen
Verzeichnisse liefern 3.360 Einträge vor Zusammenführung: SkylineWebcams 2.156,
LiveWorldWebcams 1.053, Panoramablick 121, EarthCam 17 und WorldCam 13.
Die bereits vorhandenen Panoramakameras und Sonnblick ergänzen diesen Bestand.

Dies ist ein wachsender Katalog, kein vollständiger Spiegel der fünf Websites.
Skyline-Einträge stammen aus öffentlichen Länderlisten; deren konkrete Player
werden bei der Wiedergabe aufgelöst. Bei den anderen Verzeichnissen wurde eine
Medienquelle aus dem Player beziehungsweise der aktuellen Kameraaufnahme
ausgelesen. Ein Listenfund ist kein bestätigter Wiedergabetest jeder Kamera.
Auch ausgelesene Streams können später offline gehen oder ihren Player ändern.

Stichproben prüfen HTTP-Antworten, HLS-Playlists und nachgelagerte Medien.
Kodi-Wiedergabetests werden separat dokumentiert. Der Build unterscheidet
`listed-public-player` und `extracted-media`; Listenfunde bekommen keinen
erfundenen Medien-Prüfzeitpunkt.

Der Import ist mit `python tools/build_world_webcams.py` wiederholbar.
`--worldcam-pages` erweitert die Zahl der Länderlisten-Seiten;
`--directories` und `--out` erlauben getrennte Durchläufe.
Er speichert gelesene Seiten im ignorierten `.cache`-Verzeichnis und beachtet
den von Panoramablick angegebenen Crawl-Abstand. Für Kamerakoordinaten wird
beim Build nötigenfalls [Natural Earth](https://www.naturalearthdata.com/about/)
verwendet; diese öffentlich verfügbaren Geodaten sind gemeinfrei.
Unsichere Länderzuordnungen bleiben offen, bewegliche Kameras ohne festen
Standort erscheinen unter „Weitere Standorte“.

Die Erweiterung wird zunächst gesammelt. Die veröffentlichte Version 1.1.6
bleibt unverändert; ein Quellcode-Push allein veröffentlicht kein Kodi-Update.

## Themen und aktuelle Weltansicht

Die Themen enthalten unter anderem Berglandschaften, Rocky Mountains, Strände,
Wüsten, Küsten, Inseln, Wälder, Autobahnen und Straßen, Sportstätten, Flughäfen,
Eisenbahnen sowie Schneelandschaften. Die Zuordnung basiert auf Katalogmetadaten,
nicht auf einer automatischen Bildanalyse. Eine Sportstätten-Webcam erweitert
nicht den Sportsender-Katalog. Schnee ist in einer Landschaft nicht ganzjährig
garantiert; „Aktueller Schneefall“ ist eine separate datenbasierte Auswahl.

**Around the World Right Now** verlinkt Kameras nahe Sonnenaufgang und
Sonnenuntergang, bei Tageslicht, bei Nacht, in der goldenen oder blauen Stunde
und in der Dämmerung. Diese Zuordnung wird aus UTC-Zeit und genauen
Kamerakoordinaten mit der mitgelieferten Bibliothek Astral 3.2 (Apache 2.0) berechnet.
Polartag und Polarnacht werden berücksichtigt. Gruppen können sich überschneiden.
Die Berechnung beschreibt den Sonnenstand, nicht aktuelle Bewölkung oder ob der
Kamerastream gerade online ist. Es wird keine Kartendarstellung vorgetäuscht;
der Ortszugriff öffnet Kontinente, Länder und Städte in Kodi.

**1.011 eindeutige Kameras** besitzen belegte Koordinaten. Bei den übrigen wird
keine Position aus dem Land oder Stadtnamen erfunden; sie stehen zusätzlich unter
„Ohne genaue Koordinaten“. Die Statistik zählt Kameras, Länder/Gebiete, Standorte,
Quellenlinks und belegte Wetterstationen. Themenzahlen und die fünf Verzeichnisse
werden ebenfalls angezeigt. Mehrfachverlinkungen erhöhen die Kameragesamtzahl
nicht. Die Statistik unterscheidet den Katalogumfang von aktuell sichtbaren Kameras.

## Wetterlagen

Unter **Aktuelles Wetter** werden nach Kontinent und Land aktuelle Stürme und
Gewitter, Schneefall, Regen/Schauer, Nebel, klarer Himmel und Bewölkung angeboten. Im
eigentlichen Wetterbereich bleibt die Auswahl auf belegte Wetterstationen
beschränkt, einschließlich der Sonnblick-Schneelandschaft. Allgemeine Reisekameras
haben zusätzlich dieselbe Wetterauswahl im Webcam-Bereich.

Open-Meteo liefert die Wetterdaten für nachgewiesene Koordinaten. WMO-Codes
95/96/99 oder Windböen ab 75 km/h zählen als Sturm/Gewitter; dies sind
modellbasierte Wetterbedingungen, keine amtlichen Sturmwarnungen. Ein Treffer
garantiert nicht, dass die Wetterlage im Kamerabild zu sehen ist. Daten über eine
Stunde alt, fehlende Koordinaten und Abruffehler werden nicht als aktuelle Lage
ausgegeben. Wetterdaten werden 30 Minuten zwischengespeichert, pro Land und in
gebündelten Anfragen geladen. Der Webcam-Hauptordner ruft kein Weltwetter ab.

## Geprüfter Arbeitsstand

Der Quellcode wurde mit 1.274 Tests geprüft. Der Katalogcheck meldet keine
ungültigen Einträge oder doppelten IDs. Der lokale Kodi-Build trägt weiterhin
Version 1.1.6; Paketintegrität und Python-3.8-Syntax sind geprüft.

Auf dem ausdrücklich freigegebenen USB-Tablet wurden die sieben neuen Menüwege
im nativen Kodi4Android erreicht. Die Weltzeitansicht wurde visuell geprüft.
Das Sonnblick-Fotobild wurde tatsächlich angezeigt; Zurück schließt die Ansicht,
ohne dass sie sich beim folgenden Wetteraufruf wieder öffnet. Die Wetterabfrage
lieferte dort aktuelle WMO-Daten (Code 2, Bewölkung). Vom Entwicklungsrechner kam
dagegen HTTP 503; die API ist deshalb nicht als überall erreichbar ausgegeben.

Vor der Installation wurden Addon und gesamtes Baka-Profil gesichert. Die 233
installierten Laufzeitdateien wurden per SHA-256 abgeglichen; alle Profildateien
blieben beim Austausch bytegleich und die Einstellungen auch nach dem Start.
Backups und Screenshots liegen ausschließlich lokal im ignorierten dist-Bereich.
Die LEAP-S1 wurde nicht verändert. Die übrigen Kameras sind nicht einzeln auf
dem Gerät getestet; Verzeichnisfund oder Extraktor-Test ist kein Abspielnachweis.
