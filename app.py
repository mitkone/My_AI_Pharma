"""
Pharma Data Viz - Главно Streamlit приложение.

- data_processing: load_data() зарежда данните веднъж (кеширани).
- logic: изчисления (EI, Rankings, Top 3) – векторни операции, @st.cache_data.
- ui_components, evolution_index, comparison_tools, ai_analysis: UI и визуализации.
- config: конфигурация.
"""

import os

# Зареждане на .env файл за API ключове
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None  # fallback: ще използваме st.text_input

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
# TRACKING – лог на посещения по секции
# ============================================================================

VISIT_LOG_PATH = config.DATA_DIR / "visits_log.csv"
ANALYTICS_FILES = [
    config.DATA_DIR / "activity_log.csv",
    VISIT_LOG_PATH,
    config.DATA_DIR / "section_visits.csv",  # старият файл, ако съществува
]


def track_visit(section_name: str) -> None:
    pass  # Това спира записването и предотвратява NameError-а от снимката ти



def reset_analytics() -> None:
    """Оптимизирана версия: Не трие нищо, за да не чупи сървъра."""
    pass



# ============================================================================
# AI INSIGHTS SUMMARY – изпълнителен обзор
# ============================================================================

def display_ai_insights(
    df_raw: pd.DataFrame,
    df_filtered: pd.DataFrame,
    filters: dict,
    periods: list,
) -> None:
    """
    Показва кратък AI Insights Summary за текущия продукт:
    - най-добър регион по % ръст (Units, последно vs предишно тримесечие)
    - най-слаб регион
    - среден Еволюционен Индекс (EI) за продукта по текущите филтри
    """
    product = filters.get("product")
    if not product or df_filtered.empty or not periods or len(periods) < 2:
        with st.container():
            st.info("Няма достатъчно данни за AI Insights за текущите филтри.")
        return

    # Growth % по региони за последните 2 периода
    best_region = best_growth = worst_region = worst_growth = None
    try:
        last_prev = compute_last_vs_previous_rankings(
            df_raw, product, "Quarter", tuple(periods)
        )
        if last_prev is not None:
            merged = last_prev["merged"]
            if not merged.empty:
                # Най-добър (по-висок Growth_%)
                best_row = merged.sort_values("Growth_%", ascending=False).iloc[0]
                best_region = best_row["Region"]
                best_growth = float(best_row["Growth_%"])
                # Най-слаб
                worst_row = merged.sort_values("Growth_%", ascending=True).iloc[0]
                worst_region = worst_row["Region"]
                worst_growth = float(worst_row["Growth_%"])
    except Exception:
        pass

    # Среден EI за продукта – последно vs предишно тримесечие, по текущите филтри
    avg_ei = None
    try:
        ref_period = periods[-1]
        base_period = periods[-2]
        rows_ei, overall_ei = compute_ei_rows_and_overall(
            df_filtered, (product,), ref_period, base_period, "Quarter"
        )
        avg_ei = float(overall_ei) if overall_ei is not None else None
    except Exception:
        pass

    # Ако нямаме нито един показател – показваме информативно съобщение
    if best_region is None and avg_ei is None:
        with st.container():
            st.info("AI Insights Summary: Няма достатъчно данни за анализ за текущите филтри.")
        return

    # UI контейнер – Executive Briefing
    with st.container():
        st.markdown(
            f"""
            <div style="
                border-radius: 10px;
                padding: 16px 20px;
                margin-bottom: 16px;
                background: linear-gradient(90deg, #0f172a, #020617);
                border: 1px solid #1f2937;
            ">
              <h3 style="margin: 0 0 6px 0; font-size: 18px;">
                🧠 AI Insights Summary
              </h3>
              <p style="margin: 0 0 10px 0; font-size: 13px; opacity: 0.8;">
                Executive briefing за <b>{product}</b> на база последните данни.
              </p>
            """,
            unsafe_allow_html=True,
        )

        # Съдържание – използваме обикновен markdown за по-лесно форматиране
        lines = []
        if best_region is not None:
            lines.append(f"- **Най-добър регион (ръст Units):** {best_region} ({best_growth:+.1f}%)")
        if worst_region is not None:
            lines.append(f"- **Най-слаб регион (ръст Units):** {worst_region} ({worst_growth:+.1f}%)")
        if avg_ei is not None:
            lines.append(f"- **Среден Еволюционен Индекс (EI):** {avg_ei:.1f}")

        if lines:
            st.markdown("\n".join(lines))
        else:
            st.markdown("_Няма достатъчно данни за изчисляване на показателите._")

        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================================
# СТРАНИЦА - КОНФИГУРАЦИЯ
# ============================================================================

st.set_page_config(
    page_title="Pharma Analytics 2026",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

hide_st_style = '''
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
[data-testid="stToolbar"] {display: none;}
[data-testid="stDecoration"] {display: none;}
.pharmalyze-card {
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
    border: 1px solid #1e293b;
}
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1rem 0 0.5rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #334155;
}
.team-btn { font-size: 1.2rem; padding: 1rem 2rem; }
</style>
'''
st.markdown(hide_st_style, unsafe_allow_html=True)

# Допълнителен блок за скриване на Manage app (както поиска потребителят)
hide_st_style_extra = '''
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display:none;}
</style>
'''
st.markdown(hide_st_style_extra, unsafe_allow_html=True)

# ============================================================================
# ЗАГЛАВИЕ И ADMIN (горе в ляво)
# ============================================================================
col_admin, col_logo = st.columns([1, 4])
with col_admin:
    is_admin = st.session_state.get("is_admin", False)
    if not is_admin:
        with st.expander("🔐 Admin", expanded=False):
            pw = st.text_input("Парола", type="password", key="admin_pw")
            if st.button("Влез"):
                if pw == "110215":
                    st.session_state["is_admin"] = True
                    st.rerun()
                else:
                    st.error("Грешна парола")
    else:
        if st.button("🚪 Изход от Admin"):
            st.session_state["is_admin"] = False
            st.rerun()
with col_logo:
    st.title("📱 Pharma Analytics 2026")

# Един път зареждане; df_raw се подава по референция към всички табове
df_raw = load_data()

# Проверка дали има данни
if df_raw.empty:
    st.warning(
        "Няма Excel файлове (.xlsx) в папката. "
        "Добави ги и рестартирай приложението."
    )
    st.stop()


# ============================================================================
# LANDING – 3 големи бутона Team 1 / 2 / 3
# ============================================================================

if "Team" not in df_raw.columns:
    df_raw["Team"] = "Team 2"

selected_team_label = st.session_state.get("selected_team", "")
if not selected_team_label:
    st.markdown("**Избери екип**")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("**Team 1**", use_container_width=True, key="btn_t1", type="primary"):
            st.session_state["selected_team"] = "Team 1"
            st.rerun()
    with c2:
        if st.button("**Team 2**", use_container_width=True, key="btn_t2", type="primary"):
            st.session_state["selected_team"] = "Team 2"
            st.rerun()
    with c3:
        if st.button("**Team 3**", use_container_width=True, key="btn_t3", type="primary"):
            st.session_state["selected_team"] = "Team 3"
            st.rerun()

    # Admin панел – видим и на екрана за избор на екип, ако си логнат
    if st.session_state.get("is_admin", False):
        st.markdown("---")
        with st.expander("⚙️ Admin", expanded=True):
            st.caption("Файловете се пазят в папки data/Team 1/, Team 2/, Team 3/. Всеки екип си има папка – данните не се губята.")
            admin_team_landing = st.selectbox("Екип за този файл", ["Team 1", "Team 2", "Team 3"], index=1, key="admin_team_landing")
            uploaded_landing = st.file_uploader("📤 Качи Excel файл", type=["xlsx", "xls"], key="admin_upload_landing")
            if uploaded_landing is not None:
                st.caption(f"Качен: {uploaded_landing.name}")
                if st.button("✅ Запази в папка на екипа", type="primary", key="admin_process_landing"):
                    with st.spinner("Записвам..."):
                        try:
                            team_dir = config.DATA_DIR / admin_team_landing
                            team_dir.mkdir(parents=True, exist_ok=True)
                            excel_path = team_dir / uploaded_landing.name
                            with open(excel_path, "wb") as f:
                                f.write(uploaded_landing.getbuffer())
                            from data_processing import load_all_excel_files, load_data
                            load_all_excel_files.clear()
                            load_data.clear()
                            st.success(f"✅ Файлът е запазен в {admin_team_landing}/. Натисни Rerun.")
                        except Exception as e:
                            st.error(f"Грешка: {e}")
            st.markdown("**Статистика**")
            uv, tv = 0, 0
            if VISIT_LOG_PATH.exists():
                try:
                    df_v = pd.read_csv(VISIT_LOG_PATH)
                    if not df_v.empty and "section" in df_v.columns:
                        uv, tv = df_v["section"].nunique(), len(df_v)
                except Exception:
                    pass
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.metric("Уникални гледания", uv)
            with sc2: st.metric("Общо гледания", tv)
            with sc3:
                if st.button("🔄 Нулирай брояча", key="reset_landing"):
                    reset_analytics()
                    st.success("Нулирано.")
                    st.rerun()

    st.stop()

selected_team_label = st.session_state["selected_team"]
df_raw = df_raw[df_raw["Team"] == selected_team_label].copy()

if df_raw.empty:
    st.warning("Няма данни за избрания екип.")
    if st.button("← Назад"):
        del st.session_state["selected_team"]
        st.rerun()
    st.stop()

# Малък бутон за смяна на екип
if st.button(f"🔄 Смени екип (сега: {selected_team_label})"):
    del st.session_state["selected_team"]
    st.rerun()

is_admin = st.session_state.get("is_admin", False)

st.markdown(
    '<style>[data-testid="stSidebar"]{display:none;} .stDeployButton{display:none;}</style>',
    unsafe_allow_html=True,
)

# ===== ADMIN PANEL – на главната страница (само за admin) =====
if is_admin:
    track_visit("Admin")

    with st.expander("⚙️ Admin", expanded=True):
        st.caption("Файловете се пазят в папки data/Team 1/, Team 2/, Team 3/. Премести Excel за Team 2 в data/Team 2/, за да продължат да се виждат.")
        admin_team = st.selectbox(
            "Екип за този файл",
            ["Team 1", "Team 2", "Team 3"],
            index=1,
            key="admin_upload_team",
        )
        uploaded_file = st.file_uploader(
            "📤 Качи Excel файл",
            type=["xlsx", "xls"],
            key="admin_file_upload",
        )
        if uploaded_file is not None:
            st.caption(f"Качен: {uploaded_file.name}")
            if st.button("✅ Запази в папка на екипа", type="primary", key="admin_process_btn"):
                with st.spinner("Записвам..."):
                    try:
                        team_dir = config.DATA_DIR / admin_team
                        team_dir.mkdir(parents=True, exist_ok=True)
                        excel_path = team_dir / uploaded_file.name
                        with open(excel_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        from data_processing import load_all_excel_files, load_data
                        load_all_excel_files.clear()
                        load_data.clear()
                        st.success(f"✅ Файлът е запазен в {admin_team}/. Натисни Rerun.")
                    except Exception as e:
                        st.error(f"Грешка: {e}")

        st.markdown("---")
        st.markdown("**Статистика**")
        unique_views = total_views = 0
        if VISIT_LOG_PATH.exists():
            try:
                df_v = pd.read_csv(VISIT_LOG_PATH)
                if not df_v.empty and "section" in df_v.columns:
                    unique_views = df_v["section"].nunique()
                    total_views = len(df_v)
            except Exception:
                pass
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Уникални гледания", unique_views, help="Брой различни секции")
        with c2:
            st.metric("Общо гледания", total_views, help="Общ брой посещения")
        with c3:
            if st.button("🔄 Нулирай брояча", key="admin_reset_btn"):
                reset_analytics()
                st.success("Нулирано.")

        st.markdown("---")
        st.markdown("**Подредба на секции** – галочка = видима, ↑↓ = ред")
        cfg = get_dashboard_config()

        def _save_section_config():
            c = get_dashboard_config()
            for s in PAGE_SECTION_IDS:
                k = f"admin_show_{s}"
                if k in st.session_state:
                    c[f"show_section_{s}"] = st.session_state[k]
            save_config_to_json(c)
            st.rerun()

        order = cfg.get("page_section_order", list(PAGE_SECTION_IDS))
        for i, sid in enumerate(order):
            row = st.columns([3, 1, 1])
            with row[0]:
                vis = st.checkbox(
                    PAGE_SECTION_LABELS.get(sid, sid),
                    value=cfg.get(f"show_section_{sid}", True),
                    key=f"admin_show_{sid}",
                    on_change=_save_section_config,
                )
                cfg[f"show_section_{sid}"] = vis
            with row[1]:
                if st.button("↑", key=f"admin_up_{sid}", disabled=(i == 0)):
                    order[i], order[i - 1] = order[i - 1], order[i]
                    cfg["page_section_order"] = order
                    for s in PAGE_SECTION_IDS:
                        k = f"admin_show_{s}"
                        if k in st.session_state:
                            cfg[f"show_section_{s}"] = st.session_state[k]
                    save_config_to_json(cfg)
                    st.rerun()
            with row[2]:
                if st.button("↓", key=f"admin_down_{sid}", disabled=(i == len(order) - 1)):
                    order[i], order[i + 1] = order[i + 1], order[i]
                    cfg["page_section_order"] = order
                    for s in PAGE_SECTION_IDS:
                        k = f"admin_show_{s}"
                        if k in st.session_state:
                            cfg[f"show_section_{s}"] = st.session_state[k]
                    save_config_to_json(cfg)
                    st.rerun()

cfg = get_dashboard_config()

# ============================================================================
# QUICK SEARCH – автокомплит: пиши и избирай от предложенията
# ============================================================================

import re
def _is_atc_class(drug_name):
    if pd.isna(drug_name):
        return False
    return bool(re.match(r'^[A-Z]\d{2}[A-Z]\d', str(drug_name).strip()))

_all_drugs = sorted([
    d for d in df_raw["Drug_Name"].dropna().unique()
    if not _is_atc_class(d)
])

st.markdown('<p class="section-header">🔍 Търсене на медикамент</p>', unsafe_allow_html=True)
# Поле за търсене: при всяко натискане се обновява (без Enter), ако е инсталиран streamlit-keyup
if st_keyup:
    drug_filter = st_keyup(
        "Пиши име на медикамент",
        placeholder="напр. Lip, Crestor...",
        key="drug_search_filter",
        debounce=150,
    )
else:
    drug_filter = st.text_input(
        "Пиши име на медикамент",
        placeholder="напр. Lip, Crestor... (натисни Enter за предложения)",
        key="drug_search_filter",
        help="Почни да пишеш – ще се появят предложения; избери с клик.",
    )
_filter = (drug_filter or "").strip().lower()
filtered_drugs = [d for d in _all_drugs if _filter in (d or "").lower()] if _filter else []

# Избран медикамент: от сесия (след клик) или от текущ избор
selected_drug = st.session_state.get("quick_search_drug", "")
# Предложенията се показват винаги при въведен текст – и при смяна на медикамент (без да се изчистват филтрите)
if _filter:
    if filtered_drugs:
        st.caption("Избери медикамент с клик:")
        cols = st.columns(2)
        for i, drug in enumerate(filtered_drugs[:24]):
            with cols[i % 2]:
                if st.button(drug, key=f"qs_drug_{drug}", use_container_width=True):
                    st.session_state["quick_search_drug"] = drug
                    st.rerun()
    else:
        st.caption("Няма съвпадения – опитай друго име")
elif not _filter:
    if "quick_search_drug" in st.session_state:
        del st.session_state["quick_search_drug"]

# Докато не е избран медикамент – показваме само търсенето, без dashboard
if not selected_drug:
    st.info("👆 Започни да пишеш име на медикамент и избери един от предложенията, за да видиш dashboard-а.")
    st.stop()

st.session_state["quick_search_drug"] = selected_drug
st.session_state["sb_product"] = selected_drug
st.session_state["sb_product_search"] = selected_drug
st.success(f"✅ Избран: **{selected_drug}**")
periods_temp = get_sorted_periods(df_raw)
drug_data = df_raw[df_raw["Drug_Name"] == selected_drug].copy()
if not drug_data.empty and len(periods_temp) >= 2:
    last_period = periods_temp[-1]
    prev_period = periods_temp[-2]
    last_units = drug_data[drug_data["Quarter"] == last_period]["Units"].sum()
    prev_units = drug_data[drug_data["Quarter"] == prev_period]["Units"].sum()
    growth_pct = ((last_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
    regions_count = drug_data[drug_data["Quarter"] == last_period]["Region"].nunique()
    growth_emoji = "📈" if growth_pct > 0 else "📉"
    st.info(
        f"{growth_emoji} **Продажби {last_period}**: {int(last_units):,} опак. ({growth_pct:+.1f}% vs {prev_period})  \n"
        f"🗺️ **Региони**: {regions_count} | **Общо периоди**: {len(drug_data['Quarter'].unique())}"
    )

st.markdown("---")

# ============================================================================
# ФИЛТРИ – Регион, Brick, Медикамент, Конкуренти (sb_product вече синхронизиран с quick search)
# ============================================================================
st.markdown('<p class="section-header">🔧 Филтри</p>', unsafe_allow_html=True)
FILTER_KEYS = [
    "sb_region",
    "sb_product",
    "sb_product_search",
    "sb_district",
    "sb_competitors",
    "quick_search_drug",
    "drug_search_filter",
    "drug_suggest_radio",
]
col_reset, col_info = st.columns([1, 3])
with col_reset:
    if st.button("🔄 Изчисти всички филтри", type="secondary", key="reset_filters_btn"):
        for k in FILTER_KEYS:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
with col_info:
    if "Source" in df_raw.columns:
        sources = sorted(df_raw["Source"].unique())
        st.caption(f"Заредени: {', '.join(sources)}")

# Създаване на филтри (с default от Quick Search ако има) – в основното тяло, не в sidebar
filters = create_filters(df_raw, default_product=st.session_state.get("quick_search_drug"), use_sidebar=False)

# Прилагане на филтрите
df_filtered = apply_filters(df_raw, filters)

# Селектор за метрика
metric, share_in_molecule = create_metric_selector()


# ============================================================================
# ПОДГОТОВКА НА ДАННИ ЗА ВИЗУАЛИЗАЦИЯ
# ============================================================================

# Продукти за показване: основен + конкуренти (вече включва класовете)
products_on_chart = [filters["product"]] + [
    c for c in filters["competitors"] if c != filters["product"]
]

# Филтриране само на избраните продукти
# Класовете вече са в df_raw като отделни Drug_Name редове
df_chart = df_filtered[df_filtered["Drug_Name"].isin(products_on_chart)].copy()

# Сортиране на периодите
periods = get_sorted_periods(df_raw)

# ============================================================================
# DYNAMIC DASHBOARD – настройки от Admin Panel, подредба по component_order
# ============================================================================

cfg = get_dashboard_config()
selected_product_data = df_filtered[df_filtered["Drug_Name"] == filters["product"]].copy()

# Рендиране на компоненти в избрания ред (само тези над табовете; market_share / evolution_index са в табовете)
for comp_id in cfg.get("component_order", list(COMPONENT_IDS)):
    if comp_id in ("market_share", "evolution_index"):
        continue  # те са в табовете
    if not show_component_enabled(cfg, comp_id):
        continue
    use_card = comp_id in ("trend_analysis", "regional_ranking", "product_deep_dive")
    with st.container():
        if use_card:
            st.markdown('<div class="pharmalyze-card">', unsafe_allow_html=True)

        if comp_id == "performance_cards":
            if not selected_product_data.empty and len(periods) >= 2:
                last_period = periods[-1]
                prev_period = periods[-2]
                last_units = selected_product_data[selected_product_data["Quarter"] == last_period]["Units"].sum()
                prev_units = selected_product_data[selected_product_data["Quarter"] == prev_period]["Units"].sum()
                growth_pct = ((last_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
                market_share_pct = 0
                if "Source" in df_raw.columns:
                    product_source = selected_product_data["Source"].iloc[0] if len(selected_product_data) > 0 else None
                    if product_source:
                        def is_atc_class(drug_name):
                            if pd.isna(drug_name):
                                return False
                            parts = str(drug_name).split()
                            if not parts:
                                return False
                            first_word = parts[0]
                            return (
                                len(first_word) >= 4 and len(first_word) <= 7 and
                                first_word[0].isalpha() and any(c.isdigit() for c in first_word) and
                                first_word.isupper() and len(parts) >= 2 and
                                drug_name not in ["GRAND TOTAL", "Grand Total"] and
                                not drug_name.startswith("Region")
                            )
                        df_classes = df_raw[df_raw["Drug_Name"].apply(is_atc_class)].copy()
                        if len(df_classes) > 0:
                            matching_classes = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
                            if len(matching_classes) > 0:
                                class_name = matching_classes[0]
                                class_last = df_classes[
                                    (df_classes["Drug_Name"] == class_name) & (df_classes["Quarter"] == last_period)
                                ]["Units"].sum()
                                national_product_last = df_raw[
                                    (df_raw["Drug_Name"] == filters["product"]) & (df_raw["Quarter"] == last_period)
                                ]["Units"].sum()
                                market_share_pct = (national_product_last / class_last * 100) if class_last > 0 else 0
                regions_count = selected_product_data[selected_product_data["Quarter"] == last_period]["Region"].nunique()
                growth_units = int(last_units - prev_units)
                region_label = filters["region"] if filters["region"] != "Всички" else "Всички региони"
                brick_label = filters["district"] if filters.get("district") and filters["district"] != "Всички" else "Всички Брикове"
                st.markdown('<p class="section-header">📊 Ключови показатели</p>', unsafe_allow_html=True)
                st.caption(f"📍 **{region_label}** | **Брик:** {brick_label}")
                k1, k2, k3, k4 = st.columns(4)
                with k1: st.metric("Продажби", f"{int(last_units):,}", f"{growth_pct:+.1f}%")
                with k2: st.metric("MS", f"{market_share_pct:.2f}%", None)
                with k3: st.metric("Региони", str(regions_count), None)
                with k4: st.metric("Промяна", f"{abs(growth_units):,}", f"{'↑' if growth_units > 0 else '↓'} {abs(growth_pct):.1f}%")

        elif comp_id == "ai_insights":
            display_ai_insights(df_raw, df_filtered, filters, periods)

        elif comp_id == "target_tracker":
            st.markdown("### 🎯 Target Tracker")
            if not selected_product_data.empty and len(periods) >= 2:
                last_p = periods[-1]
                last_u = selected_product_data[selected_product_data["Quarter"] == last_p]["Units"].sum()
                st.metric("Текущи продажби (последен период)", f"{int(last_u):,} опак.", last_p)
            else:
                st.caption("Няма данни за целеви показатели.")

        elif comp_id == "trend_analysis":
            st.markdown("### 📈 Trend Analysis Graph")
            if not df_chart.empty and len(periods) > 0:
                try:
                    import plotly.express as px
                    trend_df = df_chart.groupby("Quarter", as_index=False)["Units"].sum()
                    fig_t = px.line(trend_df, x="Quarter", y="Units", title="Тренд по периоди (избрани продукти)")
                    fig_t.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10), dragmode=False)
                    st.plotly_chart(fig_t, use_container_width=True, config=config.PLOTLY_CONFIG)
                except Exception:
                    st.caption("Недостатъчно данни за графика.")
            else:
                st.caption("Изберете продукт и филтри за тренд графика.")

        elif comp_id == "regional_ranking":
            st.markdown("### 🗺️ Regional Ranking Table")
            if not df_filtered.empty and periods and "Region" in df_filtered.columns:
                last_p = periods[-1]
                reg = df_filtered[df_filtered["Quarter"] == last_p].groupby("Region")["Units"].sum().sort_values(ascending=False).reset_index()
                reg.columns = ["Region", "Units"]
                st.dataframe(reg, use_container_width=True, height=280)
            else:
                st.caption("Няма регионни данни за последния период.")

        elif comp_id == "product_deep_dive":
            st.markdown("### 🔬 Product Deep Dive")
            if not df_chart.empty:
                by_drug = df_chart.groupby("Drug_Name")["Units"].sum().sort_values(ascending=False).head(10).reset_index()
                by_drug.columns = ["Медикамент", "Общо опаковки"]
                st.dataframe(by_drug, use_container_width=True, height=220)
            else:
                st.caption("Няма данни за детайлен преглед.")

        if use_card:
            st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# ADVANCED VISUALIZATIONS – само ако съответният toggle е True (за производителност)
# ============================================================================
if (
    cfg.get("show_churn_alert_table")
    or cfg.get("show_growth_leaders_table")
    or cfg.get("show_regional_growth_table")
):
    st.markdown("---")
    st.markdown("#### 📊 Advanced Visualizations")
    if cfg.get("show_churn_alert_table"):
        with st.container():
            st.markdown('<div class="pharmalyze-card">', unsafe_allow_html=True)
            render_churn_alert_table(df_raw, periods, "Quarter", top_n=10)
            st.markdown("</div>", unsafe_allow_html=True)
    if cfg.get("show_growth_leaders_table"):
        with st.container():
            st.markdown('<div class="pharmalyze-card">', unsafe_allow_html=True)
            render_growth_leaders_table(df_raw, periods, "Quarter", top_n=10)
            st.markdown("</div>", unsafe_allow_html=True)
    if cfg.get("show_regional_growth_table"):
        with st.container():
            st.markdown('<div class="pharmalyze-card">', unsafe_allow_html=True)
            render_regional_growth_table(df_raw, filters["product"], periods, "Quarter")
            st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ============================================================================
# ГЛАВНИ СЕКЦИИ – ред от Admin (page_section_order)
# ============================================================================
section_order = cfg.get("page_section_order", list(PAGE_SECTION_IDS))
comp_level = "Национално ниво" if filters["region"] == "Всички" else f"Регионално: {filters['region']}"

for sid in section_order:
    if not cfg.get(f"show_section_{sid}", True):
        continue
    if sid == "dashboard":
        st.markdown('<p class="section-header">📈 Dashboard</p>', unsafe_allow_html=True)
        track_visit("Dashboard")
        df_agg, y_col, y_label = calculate_metric_data(
            df=df_filtered, products_list=products_on_chart, periods=periods,
            metric=metric, df_full=df_raw,
        )
        df_agg_result = create_timeline_chart(
            df_agg=df_agg, y_col=y_col, y_label=y_label, periods=periods,
            sel_product=filters["product"], competitors=filters["competitors"],
        )
        if df_agg_result is not None and cfg.get("show_market_share", True):
            if filters["region"] == "Всички":
                show_market_share_table(df_agg_result, period_col="Quarter", is_national=True, key_suffix="national")
            else:
                df_regional_share = calculate_regional_market_share(
                    df=df_filtered, products_list=products_on_chart, periods=periods, period_col="Quarter"
                )
                if not df_regional_share.empty and "Market_Share_%" in df_regional_share.columns:
                    show_market_share_table(df_regional_share, period_col="Quarter", is_national=False, key_suffix="regional")
    elif sid == "brick":
        st.markdown('<p class="section-header">🗺️ Разбивка по Brick (райони)</p>', unsafe_allow_html=True)
        create_brick_charts(
            df=df_raw, products_list=products_on_chart, sel_product=filters["product"],
            competitors=filters["competitors"], periods=periods,
            selected_region=filters.get("region"),
        )
    elif sid == "comparison":
        st.markdown('<p class="section-header">⚖️ Сравнение по периоди и региони</p>', unsafe_allow_html=True)
        create_period_comparison(df=df_filtered, products_list=products_on_chart, periods=periods, level_label=comp_level)
        st.divider()
        if periods:
            create_regional_comparison(df=df_raw, products_list=products_on_chart, period=periods[-1], level_label=comp_level)
    elif sid == "last_vs_prev":
        st.markdown('<p class="section-header">📅 Последно vs Предишно тримесечие</p>', unsafe_allow_html=True)
        render_last_vs_previous_quarter(df_raw, selected_product=filters["product"], period_col="Quarter")
    elif sid == "evolution_index":
        st.markdown('<p class="section-header">📊 Еволюционен Индекс</p>', unsafe_allow_html=True)
        track_visit("Evolution Index")
        render_evolution_index_tab(
            df_filtered=df_filtered, df_national=df_raw, periods=periods,
            filters=filters, period_col="Quarter",
        )
