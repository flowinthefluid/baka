# Gesammelte Änderungen

Dieser Arbeitsstand bleibt vorerst auf Baka 1.1.4. Es gibt keine neue
veröffentlichte Version. Quellcode-Commits lösen künftig keine Veröffentlichung
auf GitHub Pages aus; dafür ist eine Änderung der Addon-/Repository-Version
oder ein ausdrücklich gestarteter Veröffentlichungs-Workflow erforderlich.

## Sprachwahl und Seitensuche

Tonsprachen, Untertitel und Anbieterkataloge sind getrennte Angaben. Mit
„Auch die Sprache der Anbieterkataloge filtern“ passen Anbieter zusätzlich zu
den gewählten Ton- oder Untertitelsprachen des jeweiligen Themas. Bei rein
englischer Auswahl erscheint ein deutscher Anbieter wie HD-Filme nicht mehr,
auch wenn er einzelne englische Filme enthält. Wer solche Anbieter verwenden
möchte, kann den Katalogfilter abschalten; die Ton-/Untertitelfilter bleiben aktiv.
Live-TV behält seine unabhängige Länderauswahl.

Die Ersteinrichtung wählt nur die Kodi-Sprache vor. Originalton mit deutschen
Untertiteln ist ausdrücklich optional. Filme/Serien, Dokus und Anime bleiben
unabhängig. „Alle“ zeigt die Vereinigung der erlaubten Quellen dieser Profile
und öffnet keine ausgeschlossenen Sprachen über einen zusätzlichen Ordner.
Reine Anime- und Dokuquellen tragen ihr Profil auch aus „Alle“ weiter.

Eine Liste enthält genau eine Seitensuche. Vorhandene quellspezifische
Seitensuchen bleiben erhalten; andernfalls ergänzt Baka „Seitensuche starten
>>> Seite X von Y Seiten <<<“ mit bekanntem Gesamtwert oder „Seite X <<<“ ohne
Gesamtwert. Der zusätzliche Eintrag „Page 1“ entfällt. Auf erkennbaren späteren
Seiten ohne Next-Link bleibt der Seitensprung verfügbar. Globale Sammelsuchen
erhalten keine Seitensuche.

## Länderübersicht

Deutschland, USA, Kanada, Frankreich, Großbritannien und Japan stehen direkt
im Menü. Weitere Länder erscheinen unter Regionen. In den Kategorie-Einstellungen
lässt sich auswählen, welche Länder erscheinen und ob die Regionen einzelne
Länder oder nur eine gemeinsame Liste zeigen.

Die Listen verwenden TMDB-Herkunftsländer. Das bezeichnet keine bestätigten
Drehorte. Es gibt keinen versteckten Mindestwert von 50 Stimmen mehr: Es gelten
die eigenen Kategorie-Einstellungen. Die vorherige Mittelamerika-Abfrage lieferte
mit 50 Mindeststimmen vier Einträge, ohne diesen Wert 1.041 Katalogeinträge.
Das ist keine Zusage über verfügbare Streams. Mexiko gehört in der neuen
Regioneneinteilung gemäß UN M49 zu Mittelamerika.

## Produktionsfilter

Alle Filter sind zunächst ausgeschaltet. Es gibt einen Schalter für ganz Baka
und eine Auswahl einzelner Bereiche sowie Themenprofile für Filme/Serien,
Dokus und Anime. Der globale Schalter hat Vorrang.

* **Leicht:** Blendet Produktionen aus, deren in TMDB aufgeführte Produktionsfirmen
  ausschließlich bekannte Hollywood-Studios sind. Gemischte Koproduktionen bleiben
  sichtbar. Das ist eine bewusst eng gefasste, anhand der Daten nachvollziehbare Regel.
* **Streng:** Blendet jede erkannte Beteiligung eines Hollywood-Studios aus,
  einschließlich bekannter Mutterfirmen. Bei unklaren Metadaten werden Titel
  standardmäßig ausgeblendet; das lässt sich abschalten.

Drehort, Sprache und Staatsangehörigkeit sind keine Kriterien für diesen
Produktionsfilter. Ein unabhängiger deutscher Film in New York bleibt sichtbar.
Die Prüfung greift bei Film-/Serien-/Episodenlisten und erneut vor dem Auflösen
eines Streams. Live-TV, Sportübertragungen und Webcams sind davon ausgenommen.

Die verwendeten Firmendaten sind nicht vollständig. Informelle Zusammenarbeit,
sämtliche früheren Eigentümer und jede indirekte geschäftliche Beziehung weltweit
können damit nicht zuverlässig erkannt werden. „Streng“ bedeutet daher alle
erkannten Studio-, Koproduktions- und Mutterfirmenverbindungen, keine vollständige
historische Unternehmensprüfung.

## Schauspieler

* **Ausblenden** entfernt nur einen Eintrag aus der Schauspielerliste.
* **Boykottieren** blendet zusätzlich Filme und Serien aus, in deren hinterlegter
  Besetzung diese Person vorkommt. Bei Serien wird die Besetzung aller Staffeln
  geprüft. Beide Listen lassen sich in den Einstellungen bearbeiten und aufheben.
* Staatsangehörigkeiten lassen sich einzeln oder nach Regionen ausschließen.
  Das blendet Schauspielerlisteneinträge aus, ohne deren Filme zu boykottieren.
  Mehrfache Staatsangehörigkeiten werden berücksichtigt; unbekannte bleiben sichtbar.

Die Personenauswahl füllt innerhalb ihres begrenzten Kandidatenpools nach. Bei
umfangreichen Ausschlüssen können weniger Einträge als die eingestellte Zahl bleiben.

## Internationales Live-TV

Der mitgelieferte TV-Katalog wird um erreichbare Nicht-Sportsender aus Japan,
China, Russland, Ukraine, USA, Großbritannien, Frankreich, Mexiko, Kanada
und Europa erweitert. Auflösungs- und Feedvarianten bleiben hinter einem
Sendereintrag. HD/UHD wird bevorzugt, SD dient als Ersatz. Bereits freigegebene
Regional-Hauptquellen bleiben erhalten; Sportkataloge wurden nicht erweitert.

Live-TV kann seine Länder unabhängig von „Meine Länder“ verwenden. Der neue
Schalter steht bei den Live-TV-Länderfiltern; vorhandene Film-, Doku- und
Anime-Vorlieben werden dadurch nicht verändert. Die Länderbezeichnungen sind
auf Deutsch und Englisch vorhanden.

Umfang, Quellenprüfung und Lücken stehen in der
[internationalen Senderübersicht](SENDERLISTE-INTERNATIONAL.md).
Die Änderungen bleiben gesammelt in 1.1.4, ohne neues Release.

## Folgenliste

Ein Klick auf eine beliebige Folge genügt: Ab dieser Folge stehen die
verbleibenden Episoden in Kodis Wiedergabeliste. „Nächste Folge“ funktioniert
unabhängig vom Automatik-Schalter. „Wiedergabe automatisch fortsetzen“ steuert
nur das reguläre Ende: eingeschaltet weiterwechseln, ausgeschaltet stoppen.
Das gilt auch für Filme in einer abgespielten Watchlist.
Eine zusätzliche Zeile zum Abspielen ab Folge 1 ist nicht nötig und wurde entfernt.
Die Einträge der Wiedergabeliste enthalten Titel, Serie, Staffel und Folgennummer.

Optional lässt sich der gewählte Hoster einschließlich seiner Sprache für die
laufende Folgenliste beibehalten. Bei Stop wird diese vorübergehende Wahl gelöscht.
Die Hoster-Wahl gilt ebenfalls für manuelles Weiterwechseln bei ausgeschalteter
Automatik. Ist der Hoster in der gewählten Sprache nicht verfügbar, wird gefragt.

Ein Serienordner in einer Watchlist ist noch keine Liste einzelner Episoden.
Die Folgenliste entsteht erst beim Öffnen des Staffelordners. Sie umfasst die
angezeigten Folgen, nicht automatisch die nächste Staffel. Quellen müssen ihre
Einträge als Episoden kennzeichnen.

Quellen: [TMDB-Firmendaten](https://developer.themoviedb.org/reference/company-details),
[TMDB-Besetzung aller Serienfolgen](https://developer.themoviedb.org/reference/tv-series-aggregate-credits),
[Wikidata-Staatsangehörigkeit](https://www.wikidata.org/wiki/Property:P27),
[UN M49](https://unstats.un.org/unsd/methodology/m49/overview/).
