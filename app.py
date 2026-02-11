"""
Pharma Analytics 2026 – Professional mobile-first Streamlit app.

- Landing: Welcome + Team Selector
- Post-selection: Navigation (Dashboard | Evolution Index)
- Admin (sidebar): analytics, data upload, master_data.csv
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import pandas as pd
from pathlib import Path

import config
from analytics import track_visit, get_analytics, reset_analytics
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
from comparison_tools import create_period_comparison, create_regional_comparison
from evolution_index import render_evolution_index_tab

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None

# ============================================================================
# PAGE CONFIG & MOBILE-FIRST CSS
# ============================================================================

st.set_page_config(
    page_title="Pharma Analytics 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MOBILE_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}
a[href*="manage"] {display: none;}
.stRadio > div {flex-direction: row !important;}
.stRadio label {margin-right: 1rem;}
.analytics-card {
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
    border: 1px solid #1e293b;
}
.section-header { font-size: 1.1rem; font-weight: 600; margin: 1rem 0 0.5rem 0; padding-bottom: 0.4rem; border-bottom: 2px solid #334155; }
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ============================================================================
# ADMIN SIDEBAR (password 1234)
# ============================================================================

is_admin = False
with st.sidebar:
    st.markdown("### 🔐 Admin")
    pw = st.text_input("Парола", type="password", key="admin_pw")
    if st.button("Влез"):
        if pw == "1234":
            st.session_state["is_admin"] = True
            st.rerun()
        else:
            st.error("Грешна парола")
    if st.session_state.get("is_admin", False):
        is_admin = True
        if st.button("🚪 Изход от Admin"):
            st.session_state["is_admin"] = False
            st.rerun()
        st.success("Admin режим")
        st.markdown("---")
        st.markdown("**Качване на данни**")
        admin_team = st.selectbox("Екип", ["Team 1", "Team 2", "Team 3"], key="admin_team")
        uploaded = st.file_uploader("📤 Excel файл", type=["xlsx", "xls"], key="admin_upload")
        if uploaded and st.button("✅ Обработи и добави"):
            with st.spinner("Обработка..."):
                try:
                    from create_master_data import robust_clean_excel
                    from data_processing import extract_source_name
                    excel_path = config.DATA_DIR / uploaded.name
                    with open(excel_path, "wb") as f:
                        f.write(uploaded.getbuffer())
                    source_name = extract_source_name(uploaded.name)
                    df_new = robust_clean_excel(excel_path, source_name)
                    if not df_new.empty:
                        df_new["Team"] = admin_team
                        master_path = config.DATA_DIR / "master_data.csv"
                        if master_path.exists():
                            df_master = pd.read_csv(master_path)
                            if "Team" not in df_master.columns:
                                df_master["Team"] = "Team 2"
                            df_updated = pd.concat([df_master, df_new], ignore_index=True)
                        else:
                            df_updated = df_new
                        subset = [c for c in ["Region", "Drug_Name", "District", "Quarter", "Source", "Team"] if c in df_updated.columns]
                        df_updated = df_updated.drop_duplicates(subset=subset, keep="last")
                        df_updated.to_csv(master_path, index=False, encoding="utf-8-sig")
                        from data_processing import load_all_excel_files, load_data
                        load_all_excel_files.clear()
                        load_data.clear()
                        st.success(f"✅ Добавени {len(df_new)} реда. Rerun.")
                    else:
                        st.error("Файлът е празен.")
                except Exception as e:
                    st.error(f"Грешка: {e}")
        st.markdown("---")
        st.markdown("**Статистика**")
        a = get_analytics()
        st.metric("Team 1", a["visits"].get("Team 1", 0))
        st.metric("Team 2", a["visits"].get("Team 2", 0))
        st.metric("Team 3", a["visits"].get("Team 3", 0))
        st.metric("Общо", a.get("total", 0))
        if st.button("🔄 Нулирай статистика"):
            reset_analytics()
            st.success("Нулирано.")
            st.rerun()

# ============================================================================
# DATA LOAD & TEAM FILTER
# ============================================================================

df_raw = load_data()
if df_raw.empty:
    st.warning("Няма данни. Добави Excel файлове или master_data.csv.")
    st.stop()

if "Team" not in df_raw.columns:
    df_raw["Team"] = "Team 2"

# Landing – Welcome + Team Selector
selected_team = st.session_state.get("selected_team", "")
if not selected_team:
    st.title("Pharma Analytics 2026")
    st.markdown("---")
    st.markdown("**Избери екип**")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Team 1", use_container_width=True, type="primary", key="t1"):
            st.session_state["selected_team"] = "Team 1"
            st.rerun()
    with c2:
        if st.button("Team 2", use_container_width=True, type="primary", key="t2"):
            st.session_state["selected_team"] = "Team 2"
            st.rerun()
    with c3:
        if st.button("Team 3", use_container_width=True, type="primary", key="t3"):
            st.session_state["selected_team"] = "Team 3"
            st.rerun()
    st.stop()

# Global team filter
selected_team = st.session_state["selected_team"]
df_raw = df_raw[df_raw["Team"] == selected_team].copy()
if df_raw.empty:
    st.warning("Няма данни за този екип.")
    if st.button("← Назад"):
        del st.session_state["selected_team"]
        st.rerun()
    st.stop()

# Track visit (exclude Admin)
track_visit(selected_team, is_admin=is_admin)

# ============================================================================
# NAVIGATION: Dashboard | Evolution Index
# ============================================================================

st.markdown("---")
col_nav, col_back = st.columns([4, 1])
with col_back:
    if st.button("🔄 Смени екип"):
        del st.session_state["selected_team"]
        st.rerun()
with col_nav:
    nav = st.radio(
        "Навигация",
        ["Dashboard", "Evolution Index"],
        horizontal=True,
        key="main_nav",
        label_visibility="collapsed",
    )

# ============================================================================
# DASHBOARD
# ============================================================================

if nav == "Dashboard":
    import re
    def _is_atc(d):
        if pd.isna(d): return False
        return bool(re.match(r"^[A-Z]\d{2}[A-Z]\d", str(d).strip()))

    drugs = sorted([d for d in df_raw["Drug_Name"].dropna().unique() if not _is_atc(d)])
    st.markdown("### 🔍 Търсене на медикамент")
    search_val = st.text_input("Пиши име", placeholder="напр. Lip, Crestor...", key="drug_search") or ""
    search_lower = search_val.strip().lower()
    filtered = [d for d in drugs if search_lower in (d or "").lower()] if search_lower else []
    sel_drug = st.session_state.get("quick_drug", drugs[0] if drugs else "")

    if filtered:
        cols = st.columns(2)
        for i, d in enumerate(filtered[:16]):
            with cols[i % 2]:
                if st.button(d, key=f"qd_{d}", use_container_width=True):
                    st.session_state["quick_drug"] = d
                    st.rerun()
    if not sel_drug and drugs:
        sel_drug = drugs[0]

    if not sel_drug:
        st.info("Избери медикамент за да видиш dashboard.")
        st.stop()

    st.session_state["quick_drug"] = sel_drug
    st.success(f"✅ **{sel_drug}**")

    filters = create_filters(df_raw, default_product=sel_drug, use_sidebar=False)
    df_filtered = apply_filters(df_raw, filters)
    metric, _ = create_metric_selector()
    products = [filters["product"]] + [c for c in filters["competitors"] if c != filters["product"]]
    periods = get_sorted_periods(df_raw)
    df_chart = df_filtered[df_filtered["Drug_Name"].isin(products)].copy()

    # Key metrics
    sp = df_filtered[df_filtered["Drug_Name"] == filters["product"]]
    if not sp.empty and len(periods) >= 2:
        lp, pp = periods[-1], periods[-2]
        lu = sp[sp["Quarter"] == lp]["Units"].sum()
        pu = sp[sp["Quarter"] == pp]["Units"].sum()
        gp = ((lu - pu) / pu * 100) if pu > 0 else 0
        st.markdown("### 📊 Ключови показатели")
        k1, k2, k3 = st.columns(3)
        with k1: st.metric("Продажби", f"{int(lu):,}", f"{gp:+.1f}%")
        with k2: st.metric("Региони", sp[sp["Quarter"] == lp]["Region"].nunique(), None)
        with k3: st.metric("Период", lp, None)

    # Timeline + Market Share
    st.markdown("### 📈 Dashboard")
    df_agg, y_col, y_label = calculate_metric_data(
        df=df_filtered, products_list=products, periods=periods,
        metric=metric, df_full=df_raw,
    )
    create_timeline_chart(
        df_agg=df_agg, y_col=y_col, y_label=y_label, periods=periods,
        sel_product=filters["product"], competitors=filters["competitors"],
    )
    if df_agg is not None:
        if filters["region"] == "Всички":
            show_market_share_table(df_agg, period_col="Quarter", is_national=True, key_suffix="dash_nat")
        else:
            df_reg = calculate_regional_market_share(df=df_filtered, products_list=products, periods=periods, period_col="Quarter")
            if not df_reg.empty:
                show_market_share_table(df_reg, period_col="Quarter", is_national=False, key_suffix="dash_reg")

    # Brick
    st.markdown("### 🗺️ Разбивка по Brick")
    create_brick_charts(
        df=df_raw, products_list=products, sel_product=filters["product"],
        competitors=filters["competitors"], periods=periods,
        selected_region=filters.get("region"),
    )

    # Comparison
    lvl = "Национално ниво" if filters["region"] == "Всички" else f"Регионално: {filters['region']}"
    st.markdown("### ⚖️ Сравнение")
    create_period_comparison(df=df_filtered, products_list=products, periods=periods, level_label=lvl)
    if periods:
        create_regional_comparison(df=df_raw, products_list=products, period=periods[-1], level_label=lvl)

    # Last vs Prev
    st.markdown("### 📅 Последно vs Предишно тримесечие")
    render_last_vs_previous_quarter(df_raw, selected_product=filters["product"], period_col="Quarter")

# ============================================================================
# EVOLUTION INDEX
# ============================================================================

else:
    drugs_ev = sorted([d for d in df_raw["Drug_Name"].dropna().unique()])[:1]
    default_ev = drugs_ev[0] if drugs_ev else None
    filters = create_filters(df_raw, default_product=default_ev, use_sidebar=False)
    df_filtered = apply_filters(df_raw, filters)
    periods = get_sorted_periods(df_raw)
    render_evolution_index_tab(
        df_filtered=df_filtered,
        df_national=df_raw,
        periods=periods,
        filters=filters,
        period_col="Quarter",
    )
