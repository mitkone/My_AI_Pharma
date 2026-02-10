"""
Dashboard configuration for the Dynamic Dashboard.
Stores settings for every component; defaults all True for core features.
Load/save from session_state and optional JSON file.
"""

from pathlib import Path
from typing import Any

import streamlit as st

import config

# JSON path for persisting dashboard config (optional)
DASHBOARD_CONFIG_PATH = config.DATA_DIR / "dashboard_config.json"

# Component IDs used in component_order and show_* keys
COMPONENT_IDS = [
    "performance_cards",
    "ai_insights",
    "market_share",
    "evolution_index",
    "target_tracker",
    "trend_analysis",
    "regional_ranking",
    "product_deep_dive",
]

# Human-readable labels for Admin UI
COMPONENT_LABELS = {
    "performance_cards": "Performance cards (KPI)",
    "ai_insights": "AI Insights",
    "market_share": "Market Share",
    "evolution_index": "Evolution Index",
    "target_tracker": "Target Tracker",
    "trend_analysis": "Trend Analysis Graph",
    "regional_ranking": "Regional Ranking Table",
    "product_deep_dive": "Product Deep Dive",
}

# Default config: core features True, optional modules False
DEFAULT_DASHBOARD_CONFIG: dict[str, Any] = {
    "show_ai_insights": True,
    "show_market_share": True,
    "show_evolution_index": True,
    "show_performance_cards": True,
    "show_target_tracker": True,
    "show_trend_analysis": False,
    "show_regional_ranking": False,
    "show_product_deep_dive": False,
    # Advanced visualization modules (optional)
    "show_churn_alert_table": False,
    "show_growth_leaders_table": False,
    "show_regional_growth_table": False,
    "default_comparison_period": "Quarter vs Quarter",  # or "Month vs Month"
    "component_order": list(COMPONENT_IDS),
}


def load_config_from_json() -> dict | None:
    """Load dashboard config from JSON file if it exists."""
    if not DASHBOARD_CONFIG_PATH.exists():
        return None
    try:
        import json
        with open(DASHBOARD_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all keys from default exist
        out = DEFAULT_DASHBOARD_CONFIG.copy()
        for k, v in data.items():
            if k in out:
                out[k] = v
        if "component_order" in data and isinstance(data["component_order"], list):
            # Keep only valid ids, append missing
            valid = [c for c in data["component_order"] if c in COMPONENT_IDS]
            for c in COMPONENT_IDS:
                if c not in valid:
                    valid.append(c)
            out["component_order"] = valid
        return out
    except Exception:
        return None


def save_config_to_json(cfg: dict) -> None:
    """Persist dashboard config to JSON."""
    try:
        import json
        DASHBOARD_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_dashboard_config() -> dict:
    """Get current dashboard config: session_state or JSON or default."""
    if "dashboard_config" not in st.session_state:
        loaded = load_config_from_json()
        st.session_state["dashboard_config"] = loaded if loaded else DEFAULT_DASHBOARD_CONFIG.copy()
    return st.session_state["dashboard_config"]


def show_component_enabled(cfg: dict, component_id: str) -> bool:
    """Return True if the component should be shown (show_<id> key)."""
    key = f"show_{component_id}"
    return cfg.get(key, True)
