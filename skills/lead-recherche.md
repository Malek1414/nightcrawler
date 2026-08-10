---
name: lead-recherche
description: Leads suchen und gegen die eigene Zielgruppen-Notiz prüfen, damit nichts Unpassendes in der Liste landet
agents: research
---
# Lead-Recherche

Für jeden Auftrag, bei dem Adressen, Einrichtungen, Firmen oder Ansprechpartner gesucht werden: "such mir Leads", "wen können wir anschreiben", "finde Anbieter in X", "Liste für den Outreach".

## Schritt 1: Zielgruppe aus den Notizen holen, immer zuerst

Bevor du auch nur eine Suchanfrage stellst:

    read_note("Zielgruppe.md")

Der genaue Pfad steht in der .env unter `LEADS_TARGET_NOTE`. Diese Notiz ist die Quelle der Wahrheit. Sie enthält die Positivliste, die Ausschlussliste und die Grenzfälle. Sie wird geändert, ohne dass jemand Code anfasst, also verlasse dich nie auf dein Gedächtnis und nie auf diesen Skill allein.

Gibt es zur Region oder zum Timing eine eigene Notiz (etwa Zeitfenster, Saison, Messetermine), lies sie zusätzlich. Wann angeschrieben wird, entscheidet oft mehr als wen.

Findest du die Notiz nicht, suche mit `search_notes("Zielgruppe")`. Existiert sie wirklich nicht, arbeite mit der Beschreibung aus dem Auftrag, sag das am Ende in einem Satz und schlag vor, die Notiz anzulegen.

## Schritt 2: Gezielt suchen statt breit

Suche mit den Begriffen aus der Positivliste, nicht mit Oberbegriffen. Ein Oberbegriff zieht genau die Treffer an, die du hinterher aussortieren musst; ein konkreter Fachbegriff nicht.

- Gut: der Fachbegriff der Branche plus Ort plus Leistung
- Schlecht: "Firmen in Berlin", "Einrichtungen für X"
- Verzeichnisse und Übersichtsseiten sind mehr wert als Einzeltreffer: Verbände, Kammern, Branchenverzeichnisse, amtliche Register. Solche Seiten mit `read_page` auslesen, dann hast du zehn Leads statt einem. Wie du an die Daten kommst, steht im Skill `web-scraping`, und wenn du das ganze Verzeichnis auf einmal willst, im Skill `seiten-index`.

## Schritt 3: Jeden Treffer prüfen, bevor er in die Liste kommt

**Harter Ausschluss über den Namen.** Enthält der Name eines der Ausschlusswörter aus der Zielgruppen-Notiz, fliegt der Treffer sofort raus, ohne dass du die Seite öffnest. Das spart die meisten Abrufe.

**Prüfung auf der Seite.** Bei allem, was durchkommt und nicht offensichtlich passt, `read_page` auf die Website und auf die Signale achten, die die Notiz als Treffer bzw. als Ausschluss definiert (Leistungen, Zielgruppe, Altersangaben, Öffnungszeiten, Preise).

Im Zweifel gilt: **lieber aussortieren als reinschreiben.** Eine kurze saubere Liste ist mehr wert als eine lange, die hinterher von Hand nachsortiert werden muss. Grenzfälle nicht wegwerfen, sondern als Grenzfall markieren.

## Schritt 3b: Widersprich, wenn du einen Grund hast

Die Zielgruppen-Notiz ist der Stand von heute, kein Denkverbot. Du bist derjenige, der die Treffer wirklich gesehen hat, also darfst du besser wissen als die Liste. Zwei Fälle:

- **Etwas fehlt.** Dir begegnet ein Typ von Einrichtung oder Firma, der offensichtlich passt, aber in der Positivliste nicht vorkommt (etwa ein Verband oder eine Plattform, über die man viele auf einmal erreicht).
- **Ein Ausschluss trägt nicht.** Du findest einen konkreten Beleg, der gegen eine Ausschlussregel spricht. Dann ist nicht die Regel falsch, aber dieser Fall fällt nicht darunter.

So gehst du damit um, und nur so:

1. **Nicht in die Liste aufnehmen.** Kein stilles Dazuschmuggeln, auch nicht "nur die eine". Die Liste bleibt sauber nach der Notiz.
2. **Am Ende einen eigenen Block "Vorschlag" schreiben.** Was du aufnehmen würdest, warum, mit dem Beleg von der Seite, und wie viele Leads dadurch ungefähr dazukämen.
3. **Direkt fragen**, ob das aufgenommen werden soll. Eine Frage, keine drei.
4. Bei Ja: Die Notiz ändern kann dieser Agent nicht (er legt nur neue an). Sag also in einem Satz, dass der Eintrag unter "Vorschläge, noch offen" in die Zielgruppen-Notiz gehört. Nachrecherchieren kannst du dann sofort.

Zurückhaltung: höchstens zwei Vorschläge pro Recherche, und nur solche, die du am konkreten Fall belegen kannst. "Man könnte auch mal X probieren" ohne Fund ist kein Vorschlag, sondern Rauschen.

## Schritt 4: Kontaktdaten nur abschreiben, nie raten

Mail-Adressen und Telefonnummern kommen aus Impressum oder Kontaktseite der echten Seite. Erfinde niemals ein Muster wie info@irgendwas.de. Findest du keinen Kontakt, schreib "kein Kontakt gefunden" in die Zeile und lass den Lead trotzdem drin, mit der URL.

## Schritt 5: Ergebnis liefern

Eine Tabelle, je Zeile ein Lead:

| Name | Typ | Ort | Kontakt | Website | Warum passt |

"Warum passt" ist EIN Satz mit dem Beleg von der Seite, nicht deine Vermutung.

Danach zwei Zeilen, die nie fehlen dürfen:

- **Aussortiert:** wie viele und warum, nach Kategorie zusammengefasst, zum Beispiel "14 aussortiert: 11 falsche Zielgruppe, 3 außerhalb der Region". So ist sichtbar, dass gefiltert wurde, und es fällt auf, wenn der Filter zu scharf steht.
- **Grenzfälle:** die markierten Fälle mit je einem Satz, damit entschieden werden kann.

Dazu, falls du einen hast, der Block aus Schritt 3b.

Ab etwa zehn Leads oder wenn die Recherche aufwendig war: das Ergebnis mit `save_research` ablegen, Titel im Format "Leads <Zielgruppe> <Ort> <Datum>". In der Antwort dann nur die Kurzfassung plus Hinweis, wo die volle Liste liegt.

## Was du nicht tust

- Keine Liste ohne vorherigen Blick in die Zielgruppen-Notiz.
- Nichts eigenmächtig aufnehmen, was die Notiz ausschließt, egal wie gut dein Grund ist. Der Grund gehört in den Vorschlag, nicht in die Tabelle.
- Umgekehrt aber auch nicht schweigen, wenn dir etwas auffällt. Eine stumme Liste, die eine offensichtliche Chance auslässt, ist auch ein Fehler.
- Keine Adressen aus dem Gedächtnis oder aus reinen Suchsnippets. Was in der Liste steht, hast du auf einer Seite gesehen.
- Keine Massenabrufe gegen dieselbe Domain, ein paar gezielte Anfragen reichen.
- Keine fertigen Anschreiben, außer es wird danach gefragt. Deine Aufgabe hier ist die Liste.
