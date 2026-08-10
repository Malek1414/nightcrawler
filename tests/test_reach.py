"""Recherche-Werkzeuge: nur die reinen Textfunktionen, kein Netz."""

from __future__ import annotations

from integrations import reach


def test_strip_html_wirft_script_und_style_raus():
    roh = """
    <html><head><style>body{color:red}</style></head>
    <body><script>var x = 1;</script><h1>Titel</h1><p>Text &amp; mehr</p></body></html>
    """
    text = reach._strip_html(roh)
    assert "Titel" in text and "Text & mehr" in text
    assert "var x" not in text and "color:red" not in text


def test_strip_html_behaelt_json_ld_inhalte_nicht():
    """Bewusst dokumentiert: das Strippen entfernt auch script-Blobs.

    Wer an __NEXT_DATA__ oder JSON-LD will, arbeitet auf dem rohen HTML,
    nicht auf dem gestrippten Text. Genau das sagt skills/web-scraping.md.
    """
    roh = '<script type="application/ld+json">{"name":"Event"}</script><p>Hallo</p>'
    assert "Event" not in reach._strip_html(roh)


def test_truncate_haengt_hinweis_an():
    assert reach._truncate("abcdef", 100) == "abcdef"
    gekuerzt = reach._truncate("abcdef", 3)
    assert gekuerzt.startswith("abc") and "gekürzt" in gekuerzt


def test_parse_vtt_entfernt_zeitmarken_und_dubletten():
    vtt = """WEBVTT
Kind: captions
Language: de

00:00:01.000 --> 00:00:03.000
Hallo zusammen

00:00:03.000 --> 00:00:05.000
Hallo zusammen
heute geht es um <c>Scraping</c>
"""
    text = reach._parse_vtt(vtt)
    assert text == "Hallo zusammen heute geht es um Scraping"
    assert "-->" not in text and "WEBVTT" not in text


def test_domain_liste_raeumt_die_eingabe_auf():
    assert reach._domain_list("destatis.de, bund.de") == ["destatis.de", "bund.de"]
    assert reach._domain_list("*.europa.eu") == ["europa.eu"]
    assert reach._domain_list("") == []
    assert reach._domain_list(" , ") == []


def test_ohne_tavily_key_wandert_der_domainfilter_in_die_anfrage(monkeypatch):
    """Exa kann nicht serverseitig filtern. Statt den Filter still fallen zu
    lassen, hängt er als site:-Operator an die Anfrage."""
    gesehen = {}
    monkeypatch.setattr(reach, "exa_search",
                        lambda query, n=5: gesehen.setdefault("q", query) or "ok")

    reach.web_search("Mietspiegel", domains="destatis.de, bund.de")
    assert "site:destatis.de OR site:bund.de" in gesehen["q"]


def test_ohne_domains_bleibt_die_anfrage_unveraendert(monkeypatch):
    gesehen = {}
    monkeypatch.setattr(reach, "exa_search",
                        lambda query, n=5: gesehen.setdefault("q", query) or "ok")

    reach.web_search("Mietspiegel")
    assert gesehen["q"] == "Mietspiegel"


def test_youtube_transcript_ohne_ytdlp_sagt_das_klar(monkeypatch):
    monkeypatch.setattr(reach.shutil, "which", lambda _: None)
    antwort = reach.youtube_transcript("https://youtu.be/xyz")
    assert "yt-dlp" in antwort and "nicht installiert" in antwort
