import os
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# Зареждане на .env файл за API ключове
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None 

# Локални модули
import config
from dashboard_config import (
    get_dashboard_config,
    show_component_enabled,
    DEFAULT_DASHBOARD_CONFIG,
    COMPONENT_IDS,
    COMPONENT_LABELS,
    PAGE_SECTION_IDS,
    PAGE_SECTION_LABELS,
    save_config_to_json,
)
from data_processing import load_data, get_sorted_periods
from ui_components import (
    create_filters,
    apply_filters,
    create_metric_selector,
    calculate_metric_data,
    create_timeline_chart,
    create_brick_charts,
    show_market_share_table,
    calculate_regional_market_share,
    render_last_vs_previous_quarter,
)
from ai_analysis import render_ai_analysis_tab
from comparison_tools import create_period_comparison, create_regional_comparison
from evolution_index import render_evolution_index_tab
from logic import compute_last_vs_previous_rankings, compute_ei_rows_and_overall
from advanced_viz import (
    render_churn_alert_table,
    render_growth_leaders_table,
    render_regional_growth_table,
)

# ============================================================================
# TRACKING – ДЕАКТИВИРАН ЗА СТАБИЛНОСТ В ОБЛАКА
# ============================================================================

def track_visit(section_name: str) -> None:
    """Деактивирано записване, за да не крашва Streamlit Cloud."""
    pass

def reset_analytics() -> None:
    """Деактивирано нулиране."""
    pass

# ============================================================================
# AI INSIGHTS SUMMARY
# ============================================================================

def display_ai_insights(df_raw: pd.DataFrame, df_filtered: pd.DataFrame, filters: dict, periods: list) -> None:
    product = filters.get("product")
    if not product or df_filtered.empty or not periods or len(periods) < 2:
        return

    best_region = best_growth = worst_region = worst_growth = None
    try:
        last_prev = compute_last_vs_previous_rankings(df_raw, product, "Quarter", tuple(periods))
        if last_prev is not None:
            merged = last_prev["merged"]
            if not merged.empty:
                best_row = merged.sort_values("Growth_%", ascending=False).iloc[0]
                best_region = best_row["Region"]; best_growth = float(best_row["Growth_%"])
                worst_row = merged.sort_values("Growth_%", ascending=True).iloc[0]
                worst_region = worst_row["Region"]; worst_growth = float(worst_row["Growth_%"])
    except: pass

    avg_ei = None
    try:
        ref_period, base_period = periods[-1], periods[-2]
        _, overall_ei = compute_ei_rows_and_overall(df_filtered, (product,), ref_period, base_period, "Quarter")
        avg_ei = float(overall_ei) if overall_ei is not None else None
    except: pass

    with st.container():
        st.markdown(f"""
            <div style="border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; background: linear-gradient(90deg, #0f172a, #020617); border: 1px solid #1f2937;">
              <h3 style="margin: 0 0 6px 0; font-size: 18px;">🧠 AI Insights Summary</h3>
              <p style="margin: 0 0 10px 0; font-size: 13px; opacity: 0.8;">Briefing за <b>{product}</b></p>
        """, unsafe_allow_html=True)
        if best_region: st.write(f"✅ **Най-добър регион:** {best_region} ({best_growth:+.1f}%)")
        if worst_region: st.write(f"⚠️ **Най-слаб регион:** {worst_region} ({worst_growth:+.1f}%)")
        if avg_ei: st.write(f"📈 **Среден EI:** {avg_ei:.1f}")
        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(page_title="Pharma Analytics 2026", page_icon="🚀", layout="wide")

st.markdown('''
<style>
#MainMenu, footer, header, .stDeployButton {visibility: hidden; display: none;}
[data-testid="stToolbar"], [data-testid="stDecoration"] {display: none;}
.pharmalyze-card { border-radius: 12px; padding: 1rem; margin-bottom: 1rem; background: #0f172a; border: 1px solid #1e293b; }
.section-header { font-size: 1.1rem; font-weight: 600; margin: 1rem 0; color: #38bdf8; }
</style>
''', unsafe_allow_html=True)

# ============================================================================
# ADMIN LOGIC
# ============================================================================
if "is_admin" not in st.session_state: st.session_state["is_admin"] = False

col_admin, col_logo = st.columns([1, 4])
with col_admin:
    if not st.session_state["is_admin"]:
        with st.expander("🔐 Admin"):
            pw = st.text_input("Парола", type="password")
            if st.button("Влез"):
                if pw == "110215":
                    st.session_state["is_admin"] = True
                    st.rerun()
    else:
        if st.button("🚪 Изход"):
            st.session_state["is_admin"] = False
            st.rerun()

st.title("📱 Pharma Analytics 2026")
df_raw = load_data()

if df_raw.empty:
    st.warning("Няма данни. Качи Excel в папките на екипите.")
    st.stop()

# ============================================================================
# TEAM SELECTION
# ============================================================================
if "selected_team" not in st.session_state:
    st.subheader("Избери екип")
    c1, c2, c3 = st.columns(3)
    for i, team in enumerate(["Team 1", "Team 2", "Team 3"]):
        with [c1, c2, c3][i]:
            if st.button(f"**{team}**", use_container_width=True):
                st.session_state["selected_team"] = team
                st.rerun()
    st.stop()

selected_team = st.session_state["selected_team"]
df_filtered_team = df_raw[df_raw["Team"] == selected_team].copy()

if st.button(f"🔄 Смени екип (сега: {selected_team})"):
    del st.session_state["selected_team"]; st.rerun()

# ============================================================================
# DASHBOARD CORE
# ============================================================================
st.markdown('<p class="section-header">🔍 Търсене на медикамент</p>', unsafe_allow_html=True)
_all_drugs = sorted(df_filtered_team["Drug_Name"].dropna().unique())
drug_search = st.text_input("Пиши име...", placeholder="напр. Lip, Crestor...", key="search")

if not drug_search:
    st.info("👆 Въведи име на медикамент, за да започнеш.")
    st.stop()

filters = create_filters(df_filtered_team, default_product=drug_search, use_sidebar=False)
df_display = apply_filters(df_filtered_team, filters)
metric, _ = create_metric_selector()
periods = get_sorted_periods(df_raw)

# Рендиране на основните графики
st.markdown('<p class="section-header">📈 Тренд Продажби</p>', unsafe_allow_html=True)
products = [filters["product"]] + filters["competitors"]
df_agg, y_col, y_label = calculate_metric_data(df_display, products, periods, metric, df_raw)
create_timeline_chart(df_agg, y_col, y_label, periods, filters["product"], filters["competitors"])

# Секции
with st.expander("🗺️ Разбивка по Brick", expanded=False):
    create_brick_charts(df_raw, products, filters["product"], filters["competitors"], periods, filters.get("region"))

with st.expander("📊 Еволюционен Индекс", expanded=False):
    render_evolution_index_tab(df_display, df_raw, periods, filters, "Quarter")

st.success(f"Приложението е стабилно. Текущ екип: {selected_team}")
