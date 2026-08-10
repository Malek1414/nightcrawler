---
name: such-operatoren
description: Suchanfragen verengen, wenn der Suchfächer nur Werbung und Blograuschen bringt (Domain-Filter, Dateityp, exakte Phrase)
agents: research
---
# Such-Operatoren

Der Suchfächer aus dem Prompt ist die Breite. Das hier ist die Tiefe: was du
machst, wenn drei Formulierungen dasselbe Rauschen bringen. Symptome: nur
Vergleichsportale, nur SEO-Texte, nur Werbung, keine einzige Primärquelle.

## Der stärkste Hebel: das Feld `domains`

web_search hat einen Parameter `domains`. Der filtert serverseitig und ist
zuverlässiger als jeder Operator im Suchtext:

    web_search(query="Mietspiegel Methodik", domains="destatis.de, bund.de")

Wann du ihn ziehst:

- **Amtliches**: `bund.de`, `destatis.de`, `europa.eu`, `gesetze-im-internet.de`,
  die Seiten von Ministerien, Landesämtern und Kammern.
- **Wissenschaft**: `pubmed.ncbi.nlm.nih.gov`, `arxiv.org`, `doaj.org`,
  `scholar.archive.org`.
- **Der Anbieter selbst**: Wenn du wissen willst, was eine Firma sagt, frag ihre
  Domain, nicht die Presse über sie. Für den Gegencheck brauchst du danach
  genau umgekehrt eine Domain, die NICHT ihre ist.

Wichtig: Damit hast du einseitig gesucht. Ein Ergebnis, das nur aus einer
Domain stammt, erfüllt den Gegencheck nicht. Der Filter ist ein Werkzeug, um
eine bestimmte Perspektive zu holen, nicht um sich eine auszusuchen.

## Operatoren im Suchtext

Die klassischen Google-Operatoren wirken je nach Anbieter unterschiedlich stark.
Sie sind kein Vertrag, sondern ein Versuch. Bringt der Versuch nichts, war es
der falsche Weg, nicht die falsche Schreibweise.

- `"exakte Phrase"` findet Fachbegriffe und Zitate, die sonst zerlegt werden.
- `-wort` schließt aus. `-shop -preisvergleich -kaufen` räumt bei
  Produktfragen sofort auf.
- `filetype:pdf` ist der direkte Weg zu Studien, Gutachten, Geschäftsberichten
  und Behördenpapieren. Der Volltext hinter einem PDF ist meistens die
  Primärquelle, über die alle anderen nur schreiben.
- `filetype:xlsx`, `filetype:csv` führt zu Rohdaten statt zu Artikeln über
  Rohdaten.
- `inurl:presse`, `inurl:jahresbericht` trifft strukturelle Seiten.
- `intitle:` verlangt den Begriff im Titel, nicht irgendwo im Text.
- Jahreszahl mitgeben (`Mietspiegel 2026`) ist oft wirksamer als jeder
  Datumsfilter.

## Ein wichtiger Vorbehalt

Nicht jeder Suchanbieter arbeitet mit Stichwörtern. Semantische Suchen
verstehen die Bedeutung deiner Anfrage und ignorieren Operatoren teilweise.
Dort wirkt etwas anderes viel stärker: **die Sprache der Quelle sprechen, die
du finden willst.**

- Suchst du eine Studie, formulier wie ein Abstract, nicht wie eine Frage.
- Suchst du eine Behördenseite, nimm den Verwaltungsbegriff, nicht den
  Alltagsbegriff.
- Suchst du eine Firma, nimm ihre Produktbezeichnung.

Das ist der eigentliche Trick, und er gilt bei jedem Anbieter.

## Reihenfolge

1. Suchfächer wie im Prompt, drei Formulierungen breit.
2. Trefferlisten vergleichen. Kommt eine brauchbare Spur? Dann verfeinern und
   fertig, dieser Skill wird nicht gebraucht.
3. Nur wenn alles rauscht: verengen. Erst `domains` auf den Quellentyp, den du
   willst. Dann `filetype:` wenn du ein Dokument suchst. Dann Ausschlüsse.
4. Immer noch nichts: Die Frage ist vielleicht mit einer Websuche nicht zu
   beantworten. Sag das, statt den zehnten Versuch zu starten. Nenn dabei, was
   du probiert hast und wo die Antwort wahrscheinlich liegt (Register, Amt,
   Datenbank, Ansprechpartner).

## Wenn du Rohdaten gefunden hast

Ein `filetype:csv`-Treffer oder ein Datenportal ist ein Fund, kein Zwischenschritt.
Wie du an solche Datensätze systematisch kommst, steht im Skill `web-scraping`,
Abschnitt "Gibt es die Daten offiziell?".
