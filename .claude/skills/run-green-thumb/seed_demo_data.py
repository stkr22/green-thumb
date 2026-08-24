"""Seed a local Green Thumb instance with demo data through the real API.

Needs the backend running on :8000 with DEV_AUTH_BYPASS=true (see SKILL.md).
Goes through HTTP rather than the database so it exercises the same validation
the UI does. Re-running adds duplicates; it does not clean up after itself.

The three species cover the cases worth looking at:
  - Monstera: a tropical pace plus a spring repotting window
  - Echeveria: the succulent pace (winter watering stretched 3.5x)
  - Cyclamen: a winter grower, so its feeding is paused during summer - the
    only one of the three whose pause is visible in the northern summer
"""

import http.cookiejar
import json
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

BASE = "http://localhost:8000"

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


def call(method: str, path: str, body: dict | None = None) -> Any:
    """Make one authenticated API call, returning the decoded body (None for 204)."""
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with _opener.open(request) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def main() -> None:
    """Log in via the dev bypass and create locations, species, plants and care logs."""
    _opener.open(BASE + "/auth/dev-login")
    info = call("GET", "/api/v1/seasons")
    presets = {preset["key"]: preset["plan"] for preset in info["presets"]}
    print("season now:", info["current_season"], "| hemisphere:", info["hemisphere"])

    room = call("POST", "/api/v1/locations", {"name": "Living room", "description": "South-facing window"})

    def species(name: str, scientific: str, intervals: dict, plan: dict, windows: dict | None = None, **extra) -> dict:
        payload = {
            "name": name,
            "scientific_name": scientific,
            "default_intervals": intervals,
            "season_plan": plan,
            "default_windows": windows or {},
            **extra,
        }
        return call("POST", "/api/v1/species", payload)

    monstera = species(
        "Monstera",
        "Monstera deliciosa",
        {"watering": 7, "fertilising": 30, "repotting": 730},
        presets["tropical"],
        {"repotting": [3, 5]},
        light="Bright indirect",
        watering_hint="Let the top few cm dry out",
    )
    echeveria = species(
        "Echeveria",
        "Echeveria elegans",
        {"watering": 14, "fertilising": 60, "repotting": 730},
        presets["succulent"],
        {"repotting": [3, 5]},
        light="Full sun",
        watering_hint="Soak, then let it dry completely",
    )
    cyclamen = species(
        "Cyclamen",
        "Cyclamen persicum",
        {"watering": 5, "fertilising": 21},
        presets["winter_grower"],
        light="Cool and bright",
        watering_hint="Water from below; it rests in summer",
    )

    # Watering ages chosen to leave some overdue, some due within the week.
    for name, parent, watered_days_ago in [
        ("Monsti", monstera, 9),
        ("Big Green", monstera, 2),
        ("Rosie", echeveria, 30),
        ("Pebble", echeveria, 5),
        ("Cyril the Cyclamen", cyclamen, 4),
    ]:
        plant = call(
            "POST",
            "/api/v1/plants",
            {"name": name, "species_id": parent["id"], "location_id": room["id"], "tags": []},
        )
        logged_at = (datetime.now(UTC) - timedelta(days=watered_days_ago)).isoformat()
        call("POST", f"/api/v1/plants/{plant['id']}/logs", {"event_type": "watering", "logged_at": logged_at})
        print(f"{name:20} watered {watered_days_ago}d ago")

    dashboard = call("GET", "/api/v1/dashboard")
    print(
        f"\ndashboard: {dashboard['season']}"
        f" | seasonal pace: {dashboard['seasonal_adjusted']}"
        f" | paused: {dashboard['seasonal_paused']}"
        f" | overdue: {len(dashboard['overdue'])}"
    )


if __name__ == "__main__":
    main()
