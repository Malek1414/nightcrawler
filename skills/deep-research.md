---
name: deep-research
description: Gründliche mehrstufige Recherche mit Quellen-Querprüfung, für wichtige Fragen, Referate und Entscheidungen
agents: research
quelle: adaptiert aus daymade/claude-code-skills deep-research (MIT)
---
# Deep Research

## 0. Sofort anfangen
- Keine Rückfrage, keine Auftragsbestätigung, kein "soll ich?". Unklarheiten werden als Annahme notiert und in der Antwort genannt.
- Der Gegencheck (Abschnitt 4) ersetzt die Rückfrage: lieber doppelt prüfen als einmal nachfragen.

## 1. Frage zerlegen
- Zerlege den Auftrag in 3 bis 5 unabhängige Teilfragen (Was genau? Wer sagt was? Was sind Zahlen und Fakten? Was ist umstritten?).
- Pro Teilfrage einen Suchfächer aus 3 Anfragen, alle im selben Zug abschicken (sie laufen gleichzeitig): wörtlicher Begriff, Synonym oder Fachbegriff, englische Variante.
- Trefferlisten vergleichen, bevor du liest: Welche Formulierung bringt frische, offizielle, konkrete Quellen? Nur diese Spur wird verfeinert, die schwachen Formulierungen werden nicht wiederholt.
- Markiere je Teilfrage: DEEP (Volltext mit read_page lesen) oder SCAN (Suchtreffer reichen).

## 2. Quellen sammeln (Register führen)
- Ziel: mindestens 6 bis 8 unterschiedliche Quellen aus mindestens 4 verschiedenen Domains, davon mindestens 6 wirklich mit read_page gelesen.
- Auch read_page mehrere pro Zug aufrufen, nicht eine Seite nach der anderen.
- Keine einzelne Quelle darf den Großteil der Belege stellen.
- Jede Quelle einordnen: Offiziell, Wissenschaft, Journalismus, Community. Und das Publikationsdatum notieren.
- Alte Quellen abwerten. Nenne in der Antwort das Stand-Datum ("Stand: TT.MM.JJJJ").

## 3. Belegen
- Jede Faktenaussage bekommt eine Quellen-Nummer [1], [2], und so weiter.
- Was du nicht belegen kannst: als [unbestätigt] kennzeichnen, nicht weglassen und niemals erfinden.
- NIE URLs erfinden. Nur Links nennen, die du in dieser Recherche wirklich geöffnet oder in Treffern gesehen hast.

## 4. Gegencheck (Pflicht vor der Antwort)
- Jede Zahl, jedes Datum, jeder Preis, jeder Termin und jeder Name wird gegen eine ZWEITE, unabhängige Quelle geprüft: andere Domain, nicht dieselbe Pressemitteilung abgeschrieben.
- Widersprechen sich zwei Quellen: beide Werte mit Quelle nennen, nicht selbst einen auswählen.
- Formuliere die Gegenthese und suche einmal gezielt danach ("Kritik an X", "X widerlegt").
- Aussagen, die nur an EINER Quelle hängen: zweite Quelle suchen oder als [unbestätigt] markieren.
- Prüfe: Ist eine wichtige Perspektive (offizielle Stelle, Betroffene, Fachleute) gar nicht vertreten?
- Abbruchkriterium: erst aufhören, wenn eine weitere Runde nur noch Bekanntes bringt.

## 5. Antwortformat
- Kernergebnis zuerst (2 bis 3 Sätze), dann Details in kurzen Absätzen.
- Nummerierte Quellenliste ans Ende, mit Datum.
- Bei save_research: vollständige Notiz mit allen Quellen ablegen, in der Antwort nur die Kurzfassung plus Hinweis auf die Notiz.
