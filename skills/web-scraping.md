---
name: web-scraping
description: Daten aus Websites ziehen statt Prosa: offene Datensätze, JSON im HTML, versteckte Endpunkte, Paginierung, Grenzen
agents: research
quelle: Muster nach dumkydewilde "Ultimate Web Scraping" (Gist) und Scrapfly "How to Scrape Hidden APIs", neu formuliert und auf die Werkzeuge dieses Agents zugeschnitten
---
# Web-Scraping

Wenn du aus einer Website DATEN brauchst (Listen, Preise, Termine, Adressen)
statt Fließtext. Die Grundregel: **parse kein HTML, solange es einen
strukturierten Weg gibt.** Fast jede moderne Seite holt ihre Inhalte selbst als
JSON. Findest du das JSON, hast du sauberere Daten, weniger Abrufe und keine
Selektoren, die morgen brechen.

Reihenfolge, immer von leicht nach schwer:

1. Gibt es die Daten offiziell?
2. Liegt das JSON schon im ausgelieferten HTML?
3. Gibt es einen Endpunkt, den man einfach aufrufen kann?
4. Erst danach: sichtbaren Text parsen.

## 1. Gibt es die Daten offiziell?

Prüf 30 Sekunden lang, ob jemand sie freiwillig herausgibt. Schneller,
vollständiger und sauberer als jeder Scrape.

- **CKAN-Portale**: `<portal>/api/3/action/package_search?q=<begriff>` liefert
  Datensätze samt Download-URLs. Läuft auf sehr vielen Verwaltungs- und
  Forschungsportalen.
- **Socrata-Portale**: `https://api.us.socrata.com/api/catalog/v1?q=<begriff>`
  durchsucht alle Socrata-Portale auf einmal. Einzelner Datensatz dann über
  `<domain>/resource/<id>.json`.
- **Ämter und Behörden** haben fast immer eine API oder wenigstens CSV. Einmal
  gezielt nach "<Behörde> API" oder "<Thema> Datensatz csv" suchen.

Ein Datensatz schlägt hundert gescrapte Seiten. Findest du einen, sag das in
der Antwort, auch wenn du zusätzlich gescrapt hast.

## 2. Liegt das JSON schon im HTML?

Der häufigste Gewinn. Der komplette Datensatz liegt oft im ausgelieferten
HTML, nur in einem script-Tag statt im sichtbaren Text.

| Framework | Marker im HTML | Wo die Daten liegen |
|---|---|---|
| Next.js | `<script id="__NEXT_DATA__" type="application/json">` | `props.pageProps` |
| Nuxt | `window.__NUXT__=` oder `<script id="__NUXT_DATA__">` | direkt |
| Remix | `window.__remixContext =` | `state.loaderData` |
| SvelteKit | `<script type="application/json" data-sveltekit-fetched>` | direkt |
| Gatsby | `/*! gatsby-page-data */`, dazu `/page-data/<pfad>/page-data.json` | `result.data` |
| Vue SSR | `window.__INITIAL_STATE__=` | direkt |
| Angular | `<script id="serverApp-state" type="application/json">` | direkt |
| beliebig | `<script type="application/ld+json">` | JSON-LD, typisiert |

JSON-LD ist der unterschätzte Fall: Event, Product, Article, Recipe,
Organization, Öffnungszeiten, Preise. SEO-Daten sind saubere, strukturierte,
vom Betreiber selbst gepflegte Daten.

**Achtung bei deinem Werkzeug:** read_page liefert normalerweise gerenderten
Text über Jina, und der wirft script-Tags weg. Die Blobs siehst du nur, wenn
Jina ausfällt und der rohe Weg greift. Findest du den Marker also nicht, heißt
das nicht, dass er nicht da ist. Dann geh über Schritt 3.

## 3. Endpunkte, die es fast immer gibt

Direkt mit read_page probieren. Kostet einen Abruf, spart im Erfolgsfall zwanzig.

| Plattform | Endpunkt | Erkennungszeichen |
|---|---|---|
| WordPress | `/wp-json/wp/v2/posts?per_page=100&_fields=title,date,link` | `<link rel="https://api.w.org/">`, `/wp-content/` |
| WordPress | `/wp-json/wp/v2/pages`, `/wp-json/wp/v2/categories` | dito |
| Shopify | `/products.json?limit=250`, `/collections/all/products.json` | `cdn.shopify.com` im Quelltext |
| Drupal | `/jsonapi/node/article?page[limit]=50` | `/sites/default/files/` |
| Ghost | `/ghost/api/content/posts/?key=<key>` | `ghost` im Quelltext |
| Squarespace | beliebige URL plus `?format=json` | `squarespace` im Quelltext |
| Wix | Pfade unter `/_api/` | `wix.com` im Quelltext |
| Next.js | `/_next/data/<buildId>/<pfad>.json` | `__NEXT_DATA__` im HTML |
| allgemein | `/api/`, `/api/v1/`, `/ajax/`, `/json/`, `/feed`, `/rss` | Pfade im Seitentext und in Links |

`_fields=` bei WordPress ist Gold wert: du holst die drei Felder, die du
brauchst, statt jedes Mal den kompletten Artikelinhalt.

**Paginierung und Limits abtasten**, statt zwanzig Seiten einzeln zu ziehen:

- Muster: `?page=2`, `?offset=20&limit=20`, `?cursor=...`, `?per_page=100`
- Limit abtasten: 50, dann 100, dann 250. Die meisten APIs deckeln irgendwo und
  geben still weniger zurück, statt zu meckern. Zähl also nach.
- Ende der Liste ist ein leeres Array oder ein Fehlerobjekt. Beides ist ein
  sauberes Abbruchsignal, rate nicht.
- `total`, `count` oder `X-WP-TotalPages` sagt dir vorher, wie viel es gibt.
  Stehen da 4000 Einträge und du brauchst 20, hol 20.

**Endpunkt verifizieren, bevor du ihm glaubst:** Vergleich zwei, drei Werte
gegen die sichtbare Seite. Kommt HTML statt JSON, ist es eine Fehlerseite, kein
Endpunkt. Ist die Antwort verdächtig kurz, hat der Bot-Schutz geantwortet.

## 4. Erst danach: sichtbaren Text

Der langsamste und brüchigste Weg, nicht der erste. `.ics`-Feeds (Marker
`BEGIN:VCALENDAR`) sind der sauberste Weg zu Terminen; auf der Seite nach
"ical", "ics", "Kalender abonnieren" suchen. `.xml.gz` kannst du nicht lesen,
das ist gepackt.

## Grenzen deines Werkzeugs, und was du dann sagst

read_page macht einen normalen GET. Kein POST, keine eigenen Header, kein
JavaScript. Konkret:

- **GraphQL** (`/graphql`, `/api/graphql`) braucht fast immer POST mit Query-Body.
- **Algolia, Elastic und ähnliche** brauchen App-ID und API-Key im Header.
- **Endpunkte mit Pflicht-Header** (Referer, X-Token, Cookie) antworten mit
  401, 403 oder einer leeren Liste.
- **Infinite Scroll ohne erkennbaren Endpunkt** braucht einen echten Browser.

Dann nicht tricksen, nicht raten, nichts erfinden. Sag in einem Satz, welcher
Endpunkt es wäre, woran es scheitert und was der beste manuelle Weg ist
(Entwicklertools, Netzwerk-Tab, XHR filtern). Ein präziser Hinweis ist mehr
wert als ein erfundener Datensatz.

## Robustheit

- Ergebnisse stichprobenartig gegen die sichtbare Seite prüfen.
- Zahlenformate: 1.200,50 (deutsch) ist nicht 1200.50 (englisch). Beim Datum
  kann 03.04. der 3. April oder der 4. März sein, je nach Seite.
- Verdächtig runde oder über viele Datensätze gleiche Werte sind meistens ein
  Parsing-Fehler, kein Fund.
- Für wiederkehrende Datenquellen: sag, dass sich eine feste Anbindung lohnt,
  statt jedes Mal zu scrapen.

## Anstand

- robots.txt und Nutzungsbedingungen respektieren. Was dort ausgeschlossen ist,
  rufst du nicht ab, auch wenn es technisch ginge.
- Keine Bot-Schutz-, Login- oder Paywall-Umgehung.
- Ein paar gezielte Anfragen, keine Serien gegen dieselbe Domain.
- Keine personenbezogenen Daten mitnehmen, die für die Aufgabe nicht gebraucht
  werden, auch wenn die API sie mitliefert.

## Wenn das hier nicht reicht

- Du brauchst viele Seiten derselben Domain, nicht eine: Skill `seiten-index`.
- Die Seite ist tot, gesperrt oder hat sich geändert: Skill `archiv-recherche`.
- Du findest die richtige Seite gar nicht erst: Skill `such-operatoren`.
