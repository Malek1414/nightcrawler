"""Who the agent works for: the profile, and how opportunities get scored.

The profile is a TOML file you write once (examples/profile.example.toml).
It answers the questions a good assistant would ask before searching:
where are you, what are you after, what can you spend, how far will you go.

Everything here is opt-in and local. The only thing that can leave the
machine is a place name sent to OpenStreetMap for geocoding, and, only with
LOCATION_SOURCE=ip, your public IP sent to ip-api.com.

score_opportunity() is deliberately plain arithmetic, not model judgment:
the model supplies the facts it found (fee, place, deadline) and its
estimates (payoff, fit), and the cost and ranking math is done here, the same
way every time, with the breakdown shown.
"""

from __future__ import annotations

import logging
import math
import threading
import time
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
IP_LOCATION_URL = "http://ip-api.com/json/?fields=status,city,country,lat,lon"
_UA = "Nightcrawler/1.0 (personal research agent)"


class ProfileError(Exception):
    pass


@dataclass(frozen=True)
class Travel:
    ground_cost_per_km: float = 0.15
    flight_threshold_km: float = 700
    flight_base: float = 80
    flight_cost_per_km: float = 0.08
    overnight_km: float = 250
    lodging_per_night: float = 60


@dataclass(frozen=True)
class Budget:
    max_fee: float = 50
    max_total: float = 200
    max_travel_km: float = 600
    online_ok: bool = True


@dataclass(frozen=True)
class Weights:
    payoff: float = 4
    access: float = 5
    fit: float = 4
    investor_presence: float = 2


@dataclass(frozen=True)
class Profile:
    name: str = ""
    role: str = ""
    goals: tuple[str, ...] = ()
    interests: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    home_city: str = ""
    home_lat: float | None = None
    home_lon: float | None = None
    currency: str = "EUR"
    budget: Budget = field(default_factory=Budget)
    travel: Travel = field(default_factory=Travel)
    weights: Weights = field(default_factory=Weights)
    notes: str = ""

    @property
    def has_home(self) -> bool:
        return self.home_lat is not None and self.home_lon is not None


def _pick(cls, data: dict):
    known = {f for f in cls.__dataclass_fields__}
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


def load_profile(path: Path | None) -> Profile | None:
    """Read the TOML profile. None when there is no file (the agent then says
    it is ranking without personal context)."""
    if path is None or not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ProfileError(f"Profile {path} is not valid TOML: {e}") from e
    who, home = data.get("who", {}), data.get("home", {})
    return Profile(
        name=who.get("name", ""),
        role=who.get("role", ""),
        goals=tuple(who.get("goals", [])),
        interests=tuple(who.get("interests", [])),
        languages=tuple(who.get("languages", [])),
        avoid=tuple(who.get("avoid", [])),
        home_city=home.get("city", ""),
        home_lat=home.get("lat"),
        home_lon=home.get("lon"),
        currency=home.get("currency", "EUR"),
        budget=_pick(Budget, data.get("budget", {})),
        travel=_pick(Travel, data.get("travel", {})),
        weights=_pick(Weights, data.get("weights", {})),
        notes=data.get("notes", ""),
    )


def with_location(profile: Profile | None, source: str) -> Profile | None:
    """Fill in home coordinates: geocode the profile's city, or (opt-in) use
    the approximate IP location. Failures are logged, never fatal."""
    import dataclasses

    if source == "ip":
        try:
            loc = ip_location()
            base = profile or Profile()
            return dataclasses.replace(
                base, home_city=base.home_city or f"{loc['city']}, {loc['country']}",
                home_lat=loc["lat"], home_lon=loc["lon"])
        except Exception as e:
            logger.warning("IP location failed (%s), using the profile only", e)
    if profile and not profile.has_home and profile.home_city:
        try:
            lat, lon, _ = geocode(profile.home_city)
            return dataclasses.replace(profile, home_lat=lat, home_lon=lon)
        except Exception as e:
            logger.warning("Could not geocode home city '%s' (%s)", profile.home_city, e)
    return profile


def render(profile: Profile | None) -> str:
    """Profile as a prompt block. Stable text, so it stays in the prompt cache."""
    if profile is None:
        return ("\n\nUser profile: none configured. Rank opportunities on general "
                "merit, say once that personal ranking needs a profile.toml, and "
                "ask for the user's city if distance matters for the task.")
    b, c = profile.budget, profile.currency
    lines = ["", "", "User profile (who you work for; use it to decide WHAT to look for "
             "and HOW to rank it):"]
    if profile.name or profile.role:
        lines.append(f"- Who: {profile.name} {('(' + profile.role + ')') if profile.role else ''}".rstrip())
    if profile.home_city:
        coords = (f" ({profile.home_lat:.3f}, {profile.home_lon:.3f})"
                  if profile.has_home else "")
        lines.append(f"- Home base: {profile.home_city}{coords}")
    if profile.goals:
        lines.append("- Goals: " + "; ".join(profile.goals))
    if profile.interests:
        lines.append("- Interests: " + ", ".join(profile.interests))
    if profile.languages:
        lines.append("- Languages: " + ", ".join(profile.languages))
    if profile.avoid:
        lines.append("- Avoid: " + ", ".join(profile.avoid))
    lines.append(f"- Budget per opportunity: entry fee up to {b.max_fee:g} {c}, "
                 f"all-in (fee plus travel plus lodging) up to {b.max_total:g} {c}")
    lines.append(f"- Travel: up to {b.max_travel_km:g} km from home; "
                 f"online options {'welcome' if b.online_ok else 'not wanted'}")
    if profile.notes:
        lines.append(f"- Notes: {profile.notes.strip()}")
    return "\n".join(lines)


# ------------------------------------------------------------------ geography

_GEO_CACHE: dict[str, tuple[float, float, str]] = {}
_GEO_LOCK = threading.Lock()
_last_geo_call = 0.0


def geocode(place: str) -> tuple[float, float, str]:
    """Place name to (lat, lon, display name) via OpenStreetMap Nominatim.
    Their usage policy allows at most one request per second, so calls are
    serialized and spaced out, and results are cached."""
    global _last_geo_call
    key = place.strip().lower()
    with _GEO_LOCK:
        if key in _GEO_CACHE:
            return _GEO_CACHE[key]
        wait = 1.1 - (time.monotonic() - _last_geo_call)
        if wait > 0:
            time.sleep(wait)
        with httpx.Client(timeout=20, headers={"User-Agent": _UA}) as client:
            resp = client.get(NOMINATIM_URL, params={"q": place, "format": "json", "limit": 1})
        _last_geo_call = time.monotonic()
        resp.raise_for_status()
        hits = resp.json()
        if not hits:
            raise ProfileError(f"Place not found: {place}")
        result = (float(hits[0]["lat"]), float(hits[0]["lon"]), hits[0].get("display_name", place))
        _GEO_CACHE[key] = result
        return result


def ip_location() -> dict:
    """Approximate location from the public IP. Only called with LOCATION_SOURCE=ip."""
    with httpx.Client(timeout=10) as client:
        resp = client.get(IP_LOCATION_URL)
        resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise ProfileError("IP location lookup failed")
    return data


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_from_home(profile: Profile | None, place: str) -> float:
    if profile is None or not profile.has_home:
        raise ProfileError("No home location known. Set [home] city or lat/lon in profile.toml.")
    lat, lon, _ = geocode(place)
    return haversine_km(profile.home_lat, profile.home_lon, lat, lon)


# -------------------------------------------------------------------- scoring

def travel_cost(distance_km: float, t: Travel) -> tuple[float, str]:
    """Rough round-trip cost estimate. Ground travel below the flight
    threshold, a budget flight above it, plus one night when too far for a
    day trip. Deliberately simple and tunable in the profile."""
    if distance_km <= 0:
        return 0.0, "local"
    if distance_km < t.flight_threshold_km:
        cost, mode = 2 * distance_km * t.ground_cost_per_km, "ground"
    else:
        cost, mode = t.flight_base + 2 * distance_km * t.flight_cost_per_km, "flight"
    if distance_km > t.overnight_km:
        cost += t.lodging_per_night
        mode += " + 1 night"
    return round(cost, 2), mode


def score_opportunity(
    profile: Profile | None,
    title: str,
    payoff: int,
    fit: int,
    fee: float = 0.0,
    location: str = "",
    online: bool = False,
    distance_km: float | None = None,
    investor_presence: int = 0,
    deadline: str = "",
    today: date | None = None,
) -> dict:
    """Score one opportunity 0 to 100 with a visible breakdown.

    payoff: 1-5, how much it could be worth to this user (money, contacts,
            career). The model's estimate, which it must justify in the answer.
    fit:    1-5, match with the user's goals and interests.
    investor_presence: 0-3, how likely people with capital to deploy are in
            the room (0 none, 3 dedicated investor event).
    """
    p = profile or Profile()
    today = today or date.today()
    flags: list[str] = []

    if online:
        dist, travel, mode = 0.0, 0.0, "online"
    else:
        dist = distance_km
        if dist is None and location:
            try:
                dist = distance_from_home(p if profile else None, location)
            except Exception as e:
                flags.append(f"distance unknown ({e})")
        if dist is None:
            travel, mode = 0.0, "unknown"
            flags.append("travel cost not included")
        else:
            travel, mode = travel_cost(dist, p.travel)

    total = round(float(fee) + travel, 2)
    b = p.budget
    if fee > b.max_fee:
        flags.append(f"fee {fee:g} above max {b.max_fee:g}")
    if total > b.max_total:
        flags.append(f"all-in {total:g} above budget {b.max_total:g}")
    if dist is not None and not online and dist > b.max_travel_km:
        flags.append(f"{dist:.0f} km is beyond the {b.max_travel_km:g} km travel limit")
    if online and not b.online_ok:
        flags.append("online, but the profile prefers in person")
    if fee == 0 and travel == 0:
        flags.append("free to access")

    if deadline:
        try:
            days = (date.fromisoformat(deadline) - today).days
            if days < 0:
                flags.append("deadline passed")
            elif days <= 7:
                flags.append(f"deadline in {days} days")
        except ValueError:
            flags.append(f"deadline not ISO (YYYY-MM-DD): {deadline}")

    clamp = lambda v, lo, hi: max(lo, min(hi, v))  # noqa: E731
    parts = {
        "payoff": clamp(payoff, 1, 5) / 5,
        "fit": clamp(fit, 1, 5) / 5,
        # 1.0 when free and local, 0.5 when it costs exactly the whole budget.
        "access": 1 / (1 + total / max(b.max_total, 1)),
        "investor_presence": clamp(investor_presence, 0, 3) / 3,
    }
    w = p.weights
    weights = {"payoff": w.payoff, "fit": w.fit, "access": w.access,
               "investor_presence": w.investor_presence}
    score = 100 * sum(parts[k] * weights[k] for k in parts) / max(sum(weights.values()), 1e-9)
    if "deadline passed" in flags:
        score = 0.0

    return {
        "title": title,
        "score": round(score, 1),
        "cost": {"fee": fee, "travel_estimate": travel, "travel_mode": mode,
                 "all_in": total, "currency": p.currency},
        "distance_km": None if dist is None else round(dist, 1),
        "components": {k: round(v, 2) for k, v in parts.items()},
        "flags": flags,
    }
