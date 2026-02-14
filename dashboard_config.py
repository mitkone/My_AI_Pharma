"""
Dashboard configuration for the Dynamic Dashboard.
Stores settings for every component; defaults all True for core features.
Load/save from session_state and optional JSON file.
"""

from pathlib import Path
from typing import Any

import streamlit as st

import config

# JSON path for persisting dashboard config (optional). WRITABLE_DIR = /tmp на Streamlit Cloud
DASHBOARD_CONFIG_PATH = config.WRITABLE_DIR / "dashboard_config.json"

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

# Page section IDs – големи секции на страницата (Dashboard, Brick, Сравнение и т.н.)
PAGE_SECTION_IDS = [
    "dashboard",
    "brick",
    "comparison",
    "last_vs_prev",
    "evolution_index",
]

PAGE_SECTION_LABELS = {
    "dashboard": "📈 Dashboard (графика + Market Share)",
    "brick": "🗺️ Разбивка по Brick",
    "comparison": "⚖️ Сравнение на региони",
    "last_vs_prev": "📅 Последно vs Предишно тримесечие",
    "evolution_index": "📊 Еволюционен Индекс",
}

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
    "show_target_tracker": False,
    "show_trend_analysis": False,
    "show_regional_ranking": False,
    "show_product_deep_dive": False,
    # Advanced visualization modules (optional)
    "show_churn_alert_table": False,
    "show_growth_leaders_table": False,
    "show_regional_growth_table": False,
    "default_comparison_period": "Quarter vs Quarter",  # or "Month vs Month"
    "component_order": list(COMPONENT_IDS),
    # Ред на главните секции на страницата (за Admin преподреждане)
    "page_section_order": list(PAGE_SECTION_IDS),
    **{f"show_section_{sid}": True for sid in PAGE_SECTION_IDS},
    # Подредба на графиките: "desc" = най-голямо→най-малко, "asc" = най-малко→най-голямо
    "chart_sort_order": "desc",
    # Размер и позиция на графиките (за mobile настройка)
    "chart_height": 500,
    "chart_margin_left": 25,
    "chart_margin_right": 65,
    "chart_margin_top": 25,
    "chart_margin_bottom": 20,
    "chart_height_evolution": 800,  # специално за EI графиката
    # Цвят на текст в лентите: "white" или "black"
    "chart_text_color": "white",
    # Ръст % графики – какво да се показва: "pct" (само %), "units" (само оп.), "both" (и двете)
    "growth_chart_display": "both",
    # EV Index таблица – кои колони да се показват (id -> видима)
    "ei_table_show_drug": True,
    "ei_table_show_sales_ref": True,
    "ei_table_show_sales_base": True,
    "ei_table_show_growth_pct": True,
    "ei_table_show_class_growth_pct": True,
    "ei_table_show_ei": True,
}

# Маппинг колони EI таблица: id -> (булгарско име, ключ в row)
EI_TABLE_COLUMNS = [
    ("drug", "Медикамент", "drug"),
    ("sales_ref", "Продажби (Ref)", "sales_ref"),
    ("sales_base", "Продажби (Base)", "sales_base"),
    ("growth_pct", "Ръст %", "growth_pct"),
    ("class_growth_pct", "Ръст клас %", "class_growth_pct"),
    ("ei", "EI", "ei"),
]


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
            valid = [c for c in data["component_order"] if c in COMPONENT_IDS]
            for c in COMPONENT_IDS:
                if c not in valid:
                    valid.append(c)
            out["component_order"] = valid
        if "page_section_order" in data and isinstance(data["page_section_order"], list):
            valid = [s for s in data["page_section_order"] if s in PAGE_SECTION_IDS]
            for s in PAGE_SECTION_IDS:
                if s not in valid:
                    valid.append(s)
            out["page_section_order"] = valid
        for sid in PAGE_SECTION_IDS:
            k = f"show_section_{sid}"
            if k in data:
                out[k] = data[k]
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


def get_chart_sort_order() -> str:
    """Връща 'desc' (най-голямо→най-малко) или 'asc' (най-малко→най-голямо)."""
    cfg = get_dashboard_config()
    return cfg.get("chart_sort_order", "desc")


def get_chart_height() -> int:
    """Височина на графиките в px (по подразбиране 500)."""
    cfg = get_dashboard_config()
    return int(cfg.get("chart_height", 500))


def get_chart_margins() -> dict:
    """Margin dict за графиките (l, r, t, b)."""
    cfg = get_dashboard_config()
    return {
        "l": int(cfg.get("chart_margin_left", 25)),
        "r": int(cfg.get("chart_margin_right", 65)),
        "t": int(cfg.get("chart_margin_top", 25)),
        "b": int(cfg.get("chart_margin_bottom", 20)),
    }


def get_chart_height_evolution() -> int:
    """Височина на EI графиката в px (по подразбиране 800)."""
    cfg = get_dashboard_config()
    return int(cfg.get("chart_height_evolution", 800))


def get_growth_chart_display() -> str:
    """Какво да се показва на Ръст % графиките: 'pct', 'units' или 'both'."""
    cfg = get_dashboard_config()
    v = cfg.get("growth_chart_display", "both")
    return v if v in ("pct", "units", "both") else "both"


def get_chart_text_color() -> str:
    """Цвят на текст в лентите: 'white' или 'black'."""
    cfg = get_dashboard_config()
    c = cfg.get("chart_text_color", "white")
    return c if c in ("white", "black") else "white"


def get_ei_table_visible_columns() -> list:
    """Връща списък от (col_id, label, row_key) за видимите колони в EI таблицата."""
    cfg = get_dashboard_config()
    visible = []
    for col_id, label, row_key in EI_TABLE_COLUMNS:
        key = f"ei_table_show_{col_id}"
        if cfg.get(key, True):
            visible.append((col_id, label, row_key))
    return visible if visible else [(c[0], c[1], c[2]) for c in EI_TABLE_COLUMNS[:1]]  # fallback: поне Медикамент


def show_component_enabled(cfg: dict, component_id: str) -> bool:
    """Return True if the component should be shown (show_<id> key)."""
    key = f"show_{component_id}"
    return cfg.get(key, True)
