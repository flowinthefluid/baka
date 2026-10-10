# Gesammelte Änderungen

Dieser Arbeitsstand bleibt vorerst auf Baka 1.1.4. Es gibt keine neue
veröffentlichte Version. Quellcode-Commits lösen künftig keine Veröffentlichung
auf GitHub Pages aus; dafür ist eine Änderung der Addon-/Repository-Version
oder ein ausdrücklich gestarteter Veröffentlichungs-Workflow erforderlich.

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

## Folgenliste

Im Staffelordner steht „Folgenliste ab erster Folge abspielen“. Das Kontextmenü
einer Folge bietet „Ab hier als Folgenliste abspielen“. Diese ausdrückliche Aktion
legt die verbleibenden Folgen der angezeigten Liste in Kodis Video-Wiedergabeliste,
auch wenn automatisches Folgenabspielen ansonsten deaktiviert ist. Kodi kann dann
zur nächsten Folge wechseln und spielt nach dem Ende automatisch weiter.

Ein Serienordner in einer Watchlist ist noch keine Liste einzelner Episoden.
Die Folgenliste entsteht erst beim Öffnen des Staffelordners. Sie umfasst die
angezeigten Folgen, nicht automatisch die nächste Staffel. Quellen müssen ihre
Einträge als Episoden kennzeichnen.

Quellen: [TMDB-Firmendaten](https://developer.themoviedb.org/reference/company-details),
[TMDB-Besetzung aller Serienfolgen](https://developer.themoviedb.org/reference/tv-series-aggregate-credits),
[Wikidata-Staatsangehörigkeit](https://www.wikidata.org/wiki/Property:P27),
[UN M49](https://unstats.un.org/unsd/methodology/m49/overview/).
