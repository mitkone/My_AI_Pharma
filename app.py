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
    """
    Логва посещение на секция: (Timestamp_minute, Section_Name).
    Използва session_state, за да не пише повече от веднъж на минута за дадена секция.
    """
    now_minute = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    key = f"last_visit_{section_name}"
    if st.session_state.get(key) == now_minute:
        return
    st.session_state[key] = now_minute

    try:
        is_new = not VISIT_LOG_PATH.exists()
        VISIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with VISIT_LOG_PATH.open("a", encoding="utf-8") as f:
            if is_new:
                f.write("timestamp,section\n")
            f.write(f"{now_minute},{section_name}\n")
    except Exception:
        # Не прекъсваме приложението при грешка в логването
        pass


def reset_analytics() -> None:
    """Изтрива файловете с аналитика (activity_log, visits_log и стария section_visits)."""
    for path in ANALYTICS_FILES:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            # Ако не можем да изтрием, не спираме приложението
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
            .pharmalyze-card {
                border-radius: 12px;
                padding: 1rem 1.25rem;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
                border: 1px solid #1e293b;
                box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            }
            </style>
            '''
st.markdown(hide_st_style, unsafe_allow_html=True)


# ============================================================================
# ЗАГЛАВИЕ И ЗАРЕЖДАНЕ НА ДАННИ
# ============================================================================

st.title("📱 Pharma Analytics 2026")
st.markdown(
    "Мобилен dashboard за екипи по продажби – "
    "избери екип и медикамент за дълбок анализ."
)

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
# LANDING – Welcome & Team selection (скрива dashboard-а до избор на екип)
# ============================================================================

# Retro-fix: ако в master_data няма Team колона, маркираме всички редове като Team 2
if "Team" not in df_raw.columns:
    df_raw["Team"] = "Team 2"

team_options = ["Избери екип...", "Team 1", "Team 2", "Team 3", "All Teams"]
selected_team_label = st.selectbox("Екип", team_options, index=0, key="landing_team")

if selected_team_label == "Избери екип...":
    st.info("Моля, избери екип (Team 1, 2, 3 или All Teams), за да продължиш.")
    st.stop()

st.session_state["selected_team"] = selected_team_label

if selected_team_label != "All Teams":
    df_raw = df_raw[df_raw["Team"] == selected_team_label].copy()

if df_raw.empty:
    st.warning("Няма налични данни за избрания екип.")
    st.stop()


# ============================================================================
# ADMIN LOGIN – sidebar се показва само за admin
# ============================================================================

is_admin = st.session_state.get("is_admin", False)

with st.expander("🔐 Admin login"):
    admin_password = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Въведи парола за admin",
        key="admin_password_main",
    )
    if st.button("Влез като Admin", key="admin_login_btn"):
        if admin_password == "1234":
            st.session_state["is_admin"] = True
            st.success("Влезе в Admin режим. Sidebar Admin Panel е активен.")
            st.experimental_rerun()
        else:
            st.error("Грешна парола.")

is_admin = st.session_state.get("is_admin", False)

# Скриваме sidebar за не-admin потребители (mobile-first, чист landing)
if not is_admin:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===== ADMIN PANEL (само за admin, в sidebar) =====
if is_admin:
    # Логваме влизане в Admin секцията (веднъж на минута)
    track_visit("Admin")

    st.sidebar.header("⚙️ Admin Panel")

    # Team selector за качвания
    admin_team = st.sidebar.selectbox(
        "Team за този файл",
        ["Team 1", "Team 2", "Team 3"],
        index=1,
        key="admin_upload_team",
        help="Всеки качен файл ще бъде тагнат към избрания екип.",
    )

    # File uploader за нови Excel файлове
    uploaded_file = st.sidebar.file_uploader(
        "📤 Качи нов Excel файл",
        type=["xlsx", "xls"],
        help="Качи Excel файл с фармацевтични данни (същият формат като другите)"
    )
    
    if uploaded_file is not None:
        # Обработка на качения файл
        st.sidebar.info(f"Качен: {uploaded_file.name}")
        
        if st.sidebar.button("✅ Обработи и добави към master_data.csv", type="primary"):
            from process_excel_hierarchy import process_pharma_excel
            from create_master_data import robust_clean_excel
            from data_processing import extract_source_name
            import io
            
            with st.spinner("Обработка на новия файл..."):
                try:
                    # Запазваме файла временно
                    excel_path = config.DATA_DIR / uploaded_file.name
                    with open(excel_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Обработваме файла
                    source_name = extract_source_name(uploaded_file.name)
                    df_new = robust_clean_excel(excel_path, source_name)

                    if not df_new.empty:
                        # Добавяме Team колона за този upload
                        df_new["Team"] = admin_team

                        # Зареждаме съществуващия master_data.csv
                        master_path = config.DATA_DIR / "master_data.csv"

                        if master_path.exists():
                            df_master = pd.read_csv(master_path)
                            # Retro-fix: ако няма Team колона, маркираме старите данни като Team 2
                            if "Team" not in df_master.columns:
                                df_master["Team"] = "Team 2"
                            # Добавяме новите данни
                            df_updated = pd.concat([df_master, df_new], ignore_index=True)
                        else:
                            df_updated = df_new

                        # Премахваме дупликати
                        subset_cols = ["Region", "Drug_Name", "District", "Quarter", "Source", "Team"]
                        subset_cols = [c for c in subset_cols if c in df_updated.columns]
                        df_updated = df_updated.drop_duplicates(
                            subset=subset_cols,
                            keep="last"  # Запазваме най-новите
                        )

                        # Запазваме обновения master_data.csv
                        df_updated.to_csv(master_path, index=False, encoding="utf-8-sig")

                        # Изчистваме кеша на данните, за да се заредят новите редове веднага
                        try:
                            from data_processing import load_all_excel_files, load_data
                            load_all_excel_files.clear()
                            load_data.clear()
                        except Exception:
                            pass

                        st.sidebar.success(f"✅ Добавени {len(df_new)} нови реда!")
                        st.sidebar.info("Моля, натисни „Rerun\" в приложението, за да заредиш новите данни.")
                    else:
                        st.sidebar.error("Файлът е празен след обработка!")
                
                except Exception as e:
                    st.sidebar.error(f"Грешка: {e}")

    # Dashboard Configuration (Admin only)
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Dashboard Configuration")
    cfg = get_dashboard_config()

    st.sidebar.caption("Toggle features (apply instantly)")
    cfg["show_performance_cards"] = st.sidebar.toggle("Show Performance Cards", value=cfg.get("show_performance_cards", True), key="cfg_perf")
    cfg["show_ai_insights"] = st.sidebar.toggle("Show AI Insights", value=cfg.get("show_ai_insights", True), key="cfg_ai")
    cfg["show_market_share"] = st.sidebar.toggle("Show Market Share", value=cfg.get("show_market_share", True), key="cfg_ms")
    cfg["show_evolution_index"] = st.sidebar.toggle("Show Evolution Index", value=cfg.get("show_evolution_index", True), key="cfg_ei")
    cfg["show_target_tracker"] = st.sidebar.toggle("Show Targets", value=cfg.get("show_target_tracker", True), key="cfg_tt")
    st.sidebar.caption("Optional modules")
    cfg["show_trend_analysis"] = st.sidebar.toggle("Trend Analysis Graph", value=cfg.get("show_trend_analysis", False), key="cfg_trend")
    cfg["show_regional_ranking"] = st.sidebar.toggle("Regional Ranking Table", value=cfg.get("show_regional_ranking", False), key="cfg_reg")
    cfg["show_product_deep_dive"] = st.sidebar.toggle("Product Deep Dive", value=cfg.get("show_product_deep_dive", False), key="cfg_pdd")
    st.sidebar.caption("Advanced visualizations")
    cfg["show_churn_alert_table"] = st.sidebar.toggle("Churn Alert Table", value=cfg.get("show_churn_alert_table", False), key="cfg_churn")
    cfg["show_growth_leaders_table"] = st.sidebar.toggle("Top Growth Table", value=cfg.get("show_growth_leaders_table", False), key="cfg_growth_leaders")
    cfg["show_regional_growth_table"] = st.sidebar.toggle("Regional Growth Table", value=cfg.get("show_regional_growth_table", False), key="cfg_reg_growth")

    cfg["default_comparison_period"] = st.sidebar.selectbox(
        "Default Comparison Period",
        ["Quarter vs Quarter", "Month vs Month"],
        index=0 if cfg.get("default_comparison_period") == "Quarter vs Quarter" else 1,
        key="cfg_period",
    )

    order_labels = [COMPONENT_LABELS.get(cid, cid) for cid in COMPONENT_IDS]
    current_order = cfg.get("component_order", list(COMPONENT_IDS))
    current_order_labels = [COMPONENT_LABELS.get(cid, cid) for cid in current_order]
    selected_order_labels = st.sidebar.multiselect(
        "Component order (select in display order)",
        order_labels,
        default=current_order_labels,
        key="cfg_order_multiselect",
    )
    if selected_order_labels:
        label_to_id = {v: k for k, v in COMPONENT_LABELS.items()}
        cfg["component_order"] = [label_to_id.get(lb, lb) for lb in selected_order_labels]
        for cid in COMPONENT_IDS:
            if cid not in cfg["component_order"]:
                cfg["component_order"].append(cid)

    if st.sidebar.button("💾 Save config to file", key="cfg_save_btn"):
        save_config_to_json(cfg)
        st.sidebar.success("Config saved.")

    # Admin статистика: System Analytics
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 System Analytics")
    if VISIT_LOG_PATH.exists():
        try:
            df_visits = pd.read_csv(VISIT_LOG_PATH)
            if not df_visits.empty and "section" in df_visits.columns:
                counts = df_visits["section"].value_counts().reset_index()
                counts.columns = ["Section", "Visits"]
                import plotly.express as px
                fig_admin = px.bar(
                    counts,
                    x="Visits",
                    y="Section",
                    orientation="h",
                    title="Most Visited Sections",
                    text="Visits",
                )
                fig_admin.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=40, b=10),
                    dragmode=False,
                )
                st.sidebar.plotly_chart(fig_admin, use_container_width=True, config=config.PLOTLY_CONFIG)
            else:
                st.sidebar.caption("Няма записани посещения.")
        except Exception:
            st.sidebar.caption("Грешка при четене на лог файла.")
    else:
        st.sidebar.caption("Няма записани посещения.")

    # Reset Statistics
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Reset statistics**")
    confirm_reset = st.sidebar.checkbox("Are you sure?", key="confirm_reset_stats")
    if st.sidebar.button("Reset Statistics", type="primary", key="reset_stats_btn"):
        if confirm_reset:
            reset_analytics()
            st.sidebar.success("Statistics have been reset successfully!")
            st.rerun()
        else:
            st.sidebar.warning("Моля, отбележи „Are you sure?\" преди да нулираш статистиката.")

    st.sidebar.divider()

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

st.markdown("### 🔍 Търсене на медикамент")
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
# SIDEBAR - ФИЛТРИ (само след избор на медикамент)
# ============================================================================

st.sidebar.header("📊 Филтри")

# Reset All Filters бутон
FILTER_KEYS = ["sb_region", "sb_product", "sb_product_search", "sb_district", "sb_competitors", "quick_search_drug", "drug_search_filter", "drug_suggest_radio"]
with st.sidebar.container():
    if st.button("🔄 Изчисти всички филтри", use_container_width=True, type="secondary", key="reset_filters_btn"):
        for k in FILTER_KEYS:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
st.sidebar.markdown("")  # малък разстояние

# Показване на заредените категории
if "Source" in df_raw.columns:
    sources = sorted(df_raw["Source"].unique())
    st.sidebar.caption(f"Заредени: {', '.join(sources)}")

# Създаване на филтри (с default от Quick Search ако има)
filters = create_filters(df_raw, default_product=st.session_state.get('quick_search_drug'))

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
                st.markdown("### 📊 Ключови показатели")
                region_label = filters["region"] if filters["region"] != "Всички" else "Всички региони"
                brick_label = filters["district"] if filters.get("district") and filters["district"] != "Всички" else "Всички Брикове"
                st.info(f"📍 **Анализ за:** {region_label} | **Брик:** {brick_label}")
                st.metric(label=f"Продажби {last_period}", value=f"{int(last_units):,} опак.", delta=f"{growth_pct:+.1f}%")
                st.metric(label="Market Share (национално)", value=f"{market_share_pct:.2f}%", delta=None)
                st.metric(label="Активни региони", value=f"{regions_count}", delta=None)
                st.metric(label="Промяна опаковки", value=f"{abs(growth_units):,}", delta=f"{'↑' if growth_units > 0 else '↓'} {abs(growth_pct):.1f}%")

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
# НАВИГАЦИЯ – mobile-first: Dashboard / Evolution Index / AI Analyst
# ============================================================================

nav_choice = st.radio(
    "Избери секция",
    ["📈 Dashboard", "📊 Evolution Index", "🤖 AI Analyst"],
    horizontal=True,
    key="main_nav",
)

if nav_choice == "📈 Dashboard":
    st.markdown("## 📈 Dashboard")
    # Основен timeline + Market Share
    track_visit("Dashboard")
    df_agg, y_col, y_label = calculate_metric_data(
        df=df_filtered,
        products_list=products_on_chart,
        periods=periods,
        metric=metric,
        df_full=df_raw,
    )
    df_agg_result = create_timeline_chart(
        df_agg=df_agg,
        y_col=y_col,
        y_label=y_label,
        periods=periods,
        sel_product=filters["product"],
        competitors=filters["competitors"],
    )
    if df_agg_result is not None and cfg.get("show_market_share", True):
        show_market_share_table(
            df_agg_result, period_col="Quarter", is_national=True, key_suffix="national"
        )
        if filters["region"] != "Всички":
            st.markdown("---")
            df_regional_share = calculate_regional_market_share(
                df=df_filtered, products_list=products_on_chart, periods=periods, period_col="Quarter"
            )
            if not df_regional_share.empty and "Market_Share_%" in df_regional_share.columns:
                show_market_share_table(
                    df_regional_share,
                    period_col="Quarter",
                    is_national=False,
                    key_suffix="regional",
                )

    # Brick view
    st.markdown("---")
    st.markdown("### 🗺️ По Brick (райони)")
    create_brick_charts(
        df=df_raw,
        products_list=products_on_chart,
        sel_product=filters["product"],
        competitors=filters["competitors"],
        periods=periods,
    )

    # Comparison view
    st.markdown("---")
    st.markdown("### ⚖️ Сравнение по периоди и региони")
    create_period_comparison(df=df_filtered, products_list=products_on_chart, periods=periods)
    st.divider()
    if periods:
        create_regional_comparison(df=df_raw, products_list=products_on_chart, period=periods[-1])

    # Last vs Previous
    st.markdown("---")
    st.markdown("### 📅 Последно vs Предишно тримесечие")
    render_last_vs_previous_quarter(df_raw, selected_product=filters["product"], period_col="Quarter")

elif nav_choice == "📊 Evolution Index":
    st.markdown("## 📊 Evolution Index")
    track_visit("Evolution Index")
    render_evolution_index_tab(
        df_filtered=df_filtered,
        df_national=df_raw,
        periods=periods,
        filters=filters,
        period_col="Quarter",
    )

elif nav_choice == "🤖 AI Analyst":
    st.markdown("## 🤖 AI Analyst")
    render_ai_analysis_tab(
        df=df_filtered,
        sel_product=filters["product"],
        competitors=filters["competitors"],
    )


# ============================================================================
# ЕКСПОРТ НА ДАННИ (само таблица; без отделен таб)
# ============================================================================

with st.expander("📋 Данни"):
    st.dataframe(df_chart, use_container_width=True, height=300)

csv = df_chart.to_csv(index=False)
st.download_button(
    "📥 Download CSV",
    data=csv,
    file_name="pharma_export.csv",
    mime="text/csv",
)
