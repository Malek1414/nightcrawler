# Zielgruppe

Vorlage. Kopiere diese Datei in deinen Notiz-Ordner (NOTES_DIR) und trage
deine eigenen Kriterien ein. Der Agent liest sie vor jeder Lead-Recherche und
richtet sich danach. Der Pfad steht in der .env unter `LEADS_TARGET_NOTE`.

Der Sinn: Was hier drinsteht, muss niemand im Code ändern und niemand in jeden
Auftrag neu hineinschreiben. Du änderst die Notiz, die nächste Recherche
arbeitet danach.

## Positivliste

Wen suchen wir? So konkret wie möglich, mit den Fachbegriffen, unter denen
diese Anbieter sich selbst beschreiben. Genau diese Begriffe benutzt der Agent
als Suchanfragen.

- Beispiel: <Branchenbegriff> mit <Leistung> in <Region>
- Beispiel: <Verbandsname>, <Kammer>, <Branchenverzeichnis> als Sammelquelle
-

## Ausschlussliste

Wörter, die im Namen sofort zum Ausschluss führen, ohne dass die Seite
geöffnet wird. Das spart die meisten Abrufe. Sei hier ruhig streng.

- Beispiel: <Wort>, <Wort>, <Wort>
-

## Signale auf der Seite

Woran erkennt man beim Lesen der Website, ob es passt?

**Spricht dafür:** <Leistung>, <Zielgruppe>, <Fachwort>
**Spricht dagegen:** <Leistung, die nicht passt>, <falsche Altersgruppe>, <falsche Region>

## Grenzfälle

Fälle, bei denen du selbst entscheiden willst. Der Agent nimmt sie nicht in
die Liste auf, sondern markiert sie als Grenzfall.

-

## Vorschläge, noch offen

Hier trägst du ein, was der Agent vorgeschlagen hat und was du noch prüfen
willst. Der Agent schreibt hier nicht selbst rein, er darf nur neue Notizen
anlegen, keine bestehenden ändern.

-
