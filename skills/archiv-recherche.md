---
name: archiv-recherche
description: Tote, geänderte oder nicht erreichbare Seiten über das Internet Archive holen und alte Stände gegen den heutigen vergleichen
agents: research
---
# Archiv-Recherche

Drei Fälle, in denen die Recherche sonst endet, das Archiv sie aber rettet:

1. **Die Seite ist weg.** Eine Quelle verlinkt auf etwas, das 404 gibt.
2. **Die Seite hat sich geändert.** Der Preis, die Zahl, die Zusage stand mal
   anders da. Genau das ist oft die eigentliche Geschichte.
3. **Die Seite lässt dich nicht rein.** Der Abruf scheitert, im Archiv liegt
   aber eine Fassung.

Das Archiv ist damit nicht nur ein Notnagel, sondern ein eigenes
Rechercheinstrument: es macht die Zeitachse sichtbar.

## Werkzeug 1: Welche Stände gibt es?

Der CDX-Index ist eine normale URL und funktioniert mit read_page:

```
https://web.archive.org/cdx/search/cdx?url=<url>&output=json&fl=timestamp,original,statuscode&collapse=timestamp:6&limit=50
```

- `fl=` wählt die Felder. Verfügbar sind `urlkey`, `timestamp`, `original`,
  `mimetype`, `statuscode`, `digest`, `length`.
- `collapse=timestamp:4` fasst pro Jahr zusammen, `:6` pro Monat, `:8` pro Tag.
  Ohne das bekommst du hunderte fast identische Einträge.
- `collapse=digest` zeigt nur Stände, bei denen sich der Inhalt wirklich
  geändert hat. Das ist der Trick, wenn du wissen willst, WANN etwas
  umgeschrieben wurde.
- `from=2023&to=2024` grenzt den Zeitraum ein, Format `yyyyMMddhhmmss`,
  gekürzt erlaubt.
- `filter=statuscode:200` wirft die Fehlversuche raus.
- `limit=-5` gibt die fünf JÜNGSTEN Stände statt der ältesten.

Der `timestamp` sieht aus wie `20240317114532`, also Jahr, Monat, Tag, Zeit.

## Werkzeug 2: Einen Stand lesen

```
https://web.archive.org/web/<timestamp>/<url>
```

Also zum Beispiel `https://web.archive.org/web/20240317114532/https://example.com/preise`.

Kurzformen, die du dir sparen kannst zu berechnen:

- `.../web/2023/<url>` springt auf den Stand, der 2023 am nächsten liegt.
- `.../web/2/<url>` nimmt den ältesten verfügbaren.

## Vorgehen

1. Erst die normale URL versuchen. Das Archiv ist der zweite Weg, nicht der erste.
2. Scheitert sie oder brauchst du die Zeitachse: CDX abfragen, Stände ansehen.
3. Den passenden Stand mit read_page lesen.
4. In der Antwort IMMER kennzeichnen: "Stand des Internet Archive vom
   TT.MM.JJJJ". Ein archivierter Stand ist niemals der heutige Stand, und ihn
   als aktuell auszugeben ist ein Fehler, kein Detail.

## Für den Gegencheck

Wenn zwei Quellen unterschiedliche Zahlen nennen, ist die häufigste Erklärung
nicht, dass eine lügt, sondern dass sie verschieden alt sind. Das Archiv
entscheidet das:

- Steht der alte Wert in einem alten Stand und der neue in einem neuen, hast du
  keinen Widerspruch, sondern eine Änderung mit Datum. Das gehört so in die
  Antwort.
- Wurde ein Wert still geändert, ohne dass die Seite ein Änderungsdatum zeigt,
  ist genau das die belegbare Aussage.
- `collapse=digest` zeigt dir die Änderungszeitpunkte, ohne dass du jeden Stand
  einzeln lesen musst.

## Grenzen, die du kennen und nennen musst

- Nicht alles ist archiviert. Kleine Seiten oft gar nicht, dynamische Inhalte
  meist unvollständig.
- Seiten, die stark auf JavaScript setzen, liegen im Archiv oft als leeres
  Gerüst. Wenig Text im Ergebnis heißt hier nicht, dass die Seite leer war.
- Manche Betreiber lassen ihre Seite nachträglich aus dem Archiv entfernen.
  Dann ist da nichts, und das ist eine Antwort, kein Fehler.
- Andere Archive gibt es auch (archive.today, Bibliotheks- und
  Behördenarchive). Wenn das Internet Archive nichts hat, ist das einen
  gezielten Suchversuch wert, bevor du aufgibst.

## Was du nicht tust

- Keine Paywall über das Archiv umgehen. Wenn der archivierte Stand ein
  Bezahlartikel ist, zitierst du ihn nicht als frei zugänglich.
- Keine Fassung zitieren, die du nicht wirklich geöffnet hast.
- Keinen Archiv-Stand ohne Datum in die Antwort schreiben.
