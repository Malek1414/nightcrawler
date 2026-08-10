---
name: seiten-index
description: Alle relevanten URLs einer Website auf einmal finden, statt sie durchzuklicken (robots.txt, Sitemaps, Wayback-Index)
agents: research
---
# Seiten-Index

Wenn du nicht EINE Seite brauchst, sondern wissen musst, was es auf einer
Domain überhaupt gibt: alle Pressemitteilungen, alle Standorte, alle
Stellenanzeigen, alle Artikel zu einem Thema. Klick dich nicht durch die
Navigation. Websites veröffentlichen ihr Inhaltsverzeichnis freiwillig, weil
Suchmaschinen es brauchen.

## Schritt 1: robots.txt lesen

`<domain>/robots.txt` ist der billigste Abruf der ganzen Recherche und liefert
zwei Dinge:

- **`Sitemap:`-Zeilen** mit den vollständigen Inhaltsverzeichnissen. Große
  Seiten haben mehrere, oft thematisch getrennt (News, Videos, Archiv, Plus).
- **`Disallow:`-Zeilen** verraten nebenbei die Struktur der Seite, inklusive
  interner Pfade wie `/api/` oder `/suche/`. Was dort ausgeschlossen ist,
  rufst du nicht ab. Es zu lesen ist erlaubt, es zu ignorieren nicht.

## Schritt 2: Sitemap holen

Steht keine `Sitemap:`-Zeile drin, probier die üblichen Pfade direkt:

- `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap-index.xml`
- `/wp-sitemap.xml` (WordPress ab 5.5), `/sitemap_index.xml` (Yoast)
- `/news-sitemap.xml`, `/sitemaps/news-de.xml` (Nachrichtenseiten)

Was du bekommst:

- Eine **Sitemap-Index-Datei** verweist auf weitere Sitemaps. Nimm die, deren
  Name zu deiner Frage passt, nicht alle.
- Eine **normale Sitemap** listet URLs, oft mit `<lastmod>`. Damit siehst du
  ohne einen einzigen weiteren Abruf, was zuletzt geändert wurde.
- Eine **News-Sitemap** enthält nur die letzten rund 48 Stunden, dafür mit
  Titel und Erscheinungsdatum. Der schnellste Weg zu "was gab es diese Woche
  bei X".

**Grenze:** `.xml.gz` kannst du nicht lesen, das ist gepackt. Dann über
Schritt 3 gehen oder die ungepackte Variante ohne `.gz` probieren.

## Schritt 3: Wayback als Vollindex

Wenn eine Seite keine brauchbare Sitemap hat, hat das Internet Archive
trotzdem eine Liste aller URLs, die es je gesehen hat. Der CDX-Index ist eine
ganz normale URL, die du mit read_page abrufen kannst:

```
https://web.archive.org/cdx/search/cdx?url=<domain>/*&output=json&fl=original&collapse=urlkey&limit=500
```

- `url=<domain>/*` nimmt alles unter der Domain, `url=<domain>/presse/*` nur
  einen Pfad. Genau das willst du meistens.
- `collapse=urlkey` wirft Dubletten raus, sonst bekommst du jede Fassung jeder
  Seite einzeln.
- `limit=` immer setzen. Ohne Limit kann die Antwort riesig werden.
- `filter=urlkey:.*presse.*` verengt zusätzlich, wenn der Pfad nicht sauber
  getrennt ist.

Das ist auch der Weg zu Seiten, die es heute nicht mehr gibt. Wie du die dann
liest, steht im Skill `archiv-recherche`.

## Schritt 4: Aus dem Index gezielt lesen

Jetzt hast du eine Liste. Lies nicht alles.

- Sortier nach dem, was die Frage beantwortet: Datum, Pfadmuster, Titel.
- Lies fünf bis zehn Seiten mit read_page, mehrere pro Zug.
- Ist die Liste sehr lang: sag in der Antwort, wie viele URLs es insgesamt gibt
  und nach welchem Kriterium du ausgewählt hast. Eine Auswahl ohne genanntes
  Kriterium liest sich wie Vollständigkeit und ist keine.

## Wann sich das lohnt

- Verzeichnisse, Mitgliederlisten, Standortlisten
- Presse- und Newsrooms ("was hat X seit Januar veröffentlicht")
- Stellenanzeigen
- Alles, wo du sonst zwanzig Mal auf "weiter" klicken würdest

## Wann nicht

- Eine einzelne konkrete Frage. Dann ist die normale Suche schneller.
- Seiten, die ihre Inhalte gar nicht in die Sitemap legen (viele Shops,
  Login-Bereiche). Dann geh über den Skill `web-scraping`.
