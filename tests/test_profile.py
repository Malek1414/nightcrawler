"""User profile and opportunity scoring. No network: distances are passed in."""

from __future__ import annotations

from datetime import date

import pytest

from integrations import profile as prof

TODAY = date(2026, 10, 1)


def _user(**kw):
    base = dict(home_city="Berlin", home_lat=52.52, home_lon=13.405,
                budget=prof.Budget(max_fee=50, max_total=200, max_travel_km=600))
    base.update(kw)
    return prof.Profile(**base)


def test_example_profile_parses():
    from core.config import ROOT

    p = prof.load_profile(ROOT / "examples" / "profile.example.toml")
    assert p.home_city.startswith("Berlin")
    assert p.budget.max_total == 250 and p.weights.access == 5
    assert p.goals and p.avoid
    assert "volunteer" in p.notes          # top-level key, not swallowed by [weights]


def test_missing_profile_is_none(tmp_path):
    assert prof.load_profile(tmp_path / "nope.toml") is None


def test_invalid_toml_raises(tmp_path):
    bad = tmp_path / "p.toml"
    bad.write_text("[who\nname=", encoding="utf-8")
    with pytest.raises(prof.ProfileError):
        prof.load_profile(bad)


def test_haversine_berlin_paris():
    assert 870 < prof.haversine_km(52.52, 13.405, 48.857, 2.352) < 890


def test_travel_cost_bands():
    t = prof.Travel()
    assert prof.travel_cost(0, t) == (0.0, "local")
    cost, mode = prof.travel_cost(100, t)
    assert mode == "ground" and cost == 2 * 100 * t.ground_cost_per_km
    cost, mode = prof.travel_cost(1000, t)
    assert mode.startswith("flight") and "night" in mode


def test_free_local_beats_expensive_far():
    u = _user()
    near = prof.score_opportunity(u, "Local meetup", payoff=3, fit=4, fee=0,
                                  distance_km=5, today=TODAY)
    far = prof.score_opportunity(u, "Big conference", payoff=3, fit=4, fee=400,
                                 distance_km=1500, today=TODAY)
    assert near["score"] > far["score"]
    assert any("above budget" in f for f in far["flags"])
    assert any("travel limit" in f for f in far["flags"])


def test_online_and_free_is_flagged_free():
    r = prof.score_opportunity(_user(), "Webinar", payoff=2, fit=3, online=True, today=TODAY)
    assert r["cost"]["all_in"] == 0 and "free to access" in r["flags"]


def test_investor_presence_raises_score():
    u = _user()
    a = prof.score_opportunity(u, "A", payoff=4, fit=4, online=True, investor_presence=0, today=TODAY)
    b = prof.score_opportunity(u, "B", payoff=4, fit=4, online=True, investor_presence=3, today=TODAY)
    assert b["score"] > a["score"]


def test_passed_deadline_scores_zero():
    r = prof.score_opportunity(_user(), "Grant", payoff=5, fit=5, online=True,
                               deadline="2026-09-01", today=TODAY)
    assert r["score"] == 0 and "deadline passed" in r["flags"]


def test_close_deadline_is_flagged():
    r = prof.score_opportunity(_user(), "Grant", payoff=5, fit=5, online=True,
                               deadline="2026-10-05", today=TODAY)
    assert "deadline in 4 days" in r["flags"]


def test_inputs_are_clamped():
    r = prof.score_opportunity(_user(), "X", payoff=99, fit=-3, online=True, today=TODAY)
    assert 0 <= r["score"] <= 100


def test_without_profile_still_scores_and_says_travel_unknown():
    r = prof.score_opportunity(None, "X", payoff=3, fit=3, location="Paris", today=TODAY)
    assert 0 <= r["score"] <= 100
    assert "travel cost not included" in r["flags"]


def test_unknown_travel_is_not_free_and_never_beats_known_cheap():
    """Unknown distance used to count as zero travel: a 9000 km event got
    'free to access' and the best possible access score."""
    u = _user()
    unknown = prof.score_opportunity(u, "Far?", payoff=3, fit=3, fee=0, today=TODAY)
    local = prof.score_opportunity(u, "Local", payoff=3, fit=3, fee=0,
                                   distance_km=3, today=TODAY)
    assert "free to access" not in unknown["flags"]
    assert unknown["components"]["access"] <= 0.5
    assert local["score"] > unknown["score"]


def test_ip_location_without_profile_is_not_a_profile(monkeypatch):
    """IP mode with no profile.toml must not present default budgets as the
    user's own limits."""
    monkeypatch.setattr(prof, "ip_location", lambda: {
        "city": "Cairo", "country": "Egypt", "lat": 30.04, "lon": 31.24})
    p = prof.with_location(None, "ip")
    text = prof.render(p)
    assert "none configured" in text and "Cairo" in text
    assert "Budget per opportunity" not in text


def test_ip_mode_replaces_city_and_coordinates_together(monkeypatch):
    monkeypatch.setattr(prof, "ip_location", lambda: {
        "city": "Frankfurt", "country": "Germany", "lat": 50.11, "lon": 8.68})
    p = prof.with_location(_user(), "ip")
    assert p.home_city.startswith("Frankfurt") and p.home_lat == 50.11
    assert "Berlin" not in prof.render(p)


def test_geocode_results_persist_on_disk(tmp_path, monkeypatch):
    cache = tmp_path / "geo.json"
    monkeypatch.setattr(prof, "GEO_CACHE_FILE", cache)
    monkeypatch.setattr(prof, "_GEO_CACHE", {})
    monkeypatch.setattr(prof, "_disk_loaded", False)
    monkeypatch.setattr(prof.time, "sleep", lambda s: None)

    class Resp:
        def raise_for_status(self): pass
        def json(self): return [{"lat": "1.5", "lon": "2.5", "display_name": "X"}]

    class Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, *a, **k):
            calls.append(1)
            return Resp()
    calls = []
    monkeypatch.setattr(prof.httpx, "Client", Client)
    assert prof.geocode("Somewhere") == (1.5, 2.5, "X")
    # A fresh process: memory cache empty, disk cache present, no HTTP call.
    monkeypatch.setattr(prof, "_GEO_CACHE", {})
    monkeypatch.setattr(prof, "_disk_loaded", False)
    assert prof.geocode("somewhere ") == (1.5, 2.5, "X")
    assert calls == [1]


def test_render_mentions_budget_and_home():
    text = prof.render(_user(goals=("find clients",)))
    assert "Berlin" in text and "find clients" in text and "200" in text
