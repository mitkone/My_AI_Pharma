"""
Smart Analytics – track visits in analytics.json.
Exclude Admin users from counts. Track per Team and total.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import config

ANALYTICS_PATH = config.DATA_DIR / "analytics.json"

DEFAULT_ANALYTICS = {
    "visits": {"Team 1": 0, "Team 2": 0, "Team 3": 0},
    "total": 0,
}


def _load_analytics() -> dict:
    if not ANALYTICS_PATH.exists():
        return DEFAULT_ANALYTICS.copy()
    try:
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        v = data.get("visits", {})
        for t in ["Team 1", "Team 2", "Team 3"]:
            if t not in v:
                v[t] = 0
        return {"visits": v, "total": data.get("total", 0)}
    except Exception:
        return DEFAULT_ANALYTICS.copy()


def _save_analytics(data: dict) -> None:
    try:
        ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def track_visit(team: str, is_admin: bool = False) -> None:
    """Log a visit. Does nothing if user is Admin."""
    if is_admin:
        return
    data = _load_analytics()
    team_key = team if team in data["visits"] else "Team 2"
    data["visits"][team_key] = data["visits"].get(team_key, 0) + 1
    data["total"] = data.get("total", 0) + 1
    _save_analytics(data)


def get_analytics() -> dict:
    return _load_analytics()


def reset_analytics() -> None:
    _save_analytics(DEFAULT_ANALYTICS.copy())
