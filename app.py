"""
Pharma Data Viz - Главно Streamlit приложение (рефакторирано).

Това е чисто UI приложение - цялата бизнес логика е разделена в отделни модули:
- data_processing.py: Зареждане и обработка на данни
- ui_components.py: UI елементи (филтри, графики)
- ai_analysis.py: AI анализ с OpenAI
- drug_molecules.py: Маппинг на медикаменти към молекули
- config.py: Конфигурация
"""

import os
from pathlib import Path

# Зареждане на .env файл за API ключове
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st
import pandas as pd

try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None  # fallback: ще използваме st.text_input

# Локални модули
import config
from data_processing import (
    load_all_excel_files,
    prepare_data_for_display,
    get_sorted_periods,
)
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


# ============================================================================
# КЕШИРАНЕ НА ДАННИ
# ============================================================================

@st.cache_data(ttl=config.CACHE_TTL)
def get_cached_data():
    """
    Зарежда и кешира данните за подобряване на производителността.
    Кешът се обновява на всеки 5 минути (ttl=300) или при натискане на бутон.
    """
    df = load_all_excel_files()
    return prepare_data_for_display(df)


# ============================================================================
# СТРАНИЦА - КОНФИГУРАЦИЯ
# ============================================================================

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT
)


# ============================================================================
# ЗАГЛАВИЕ И ЗАРЕЖДАНЕ НА ДАННИ
# ============================================================================

st.title("📊 STADA Rx Sales Data")
st.markdown(
    "**Регион** → **Медикамент** → **Brick** – "
    "избери медикамент от общата база"
)

# Зареждане на данни
df_raw = get_cached_data()

# Проверка дали има данни
if df_raw.empty:
    st.warning(
        "Няма Excel файлове (.xlsx) в папката. "
        "Добави ги и рестартирай приложението."
    )
    st.stop()


# ============================================================================
# SIDEBAR - ACCESS CONTROL & ОПЦИИ
# ============================================================================

st.sidebar.header("🔐 Достъп")

# Password protection за Admin Panel
admin_password = st.sidebar.text_input(
    "Admin Password",
    type="password",
    placeholder="Въведи парола за admin",
    help="Само admin може да качва нови файлове"
)

is_admin = (admin_password == "1234")

# Показване на роля
if is_admin:
    st.sidebar.success("✅ Admin режим")
else:
    st.sidebar.info("👤 User режим")

st.sidebar.divider()

# ===== ADMIN PANEL (само за admin) =====
if is_admin:
    st.sidebar.header("⚙️ Admin Panel")
    
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
                        # Зареждаме съществуващия master_data.csv
                        master_path = config.DATA_DIR / "master_data.csv"
                        
                        if master_path.exists():
                            df_master = pd.read_csv(master_path)
                            # Добавяме новите данни
                            df_updated = pd.concat([df_master, df_new], ignore_index=True)
                        else:
                            df_updated = df_new
                        
                        # Премахваме дупликати
                        df_updated = df_updated.drop_duplicates(
                            subset=["Region", "Drug_Name", "District", "Quarter", "Source"],
                            keep="last"  # Запазваме най-новите
                        )
                        
                        # Запазваме обновения master_data.csv
                        df_updated.to_csv(master_path, index=False, encoding="utf-8-sig")
                        
                        st.sidebar.success(f"✅ Добавени {len(df_new)} нови реда!")
                        st.sidebar.info("Моля рестартирай апликацията за да заредиш новите данни.")
                        
                        # Бутон за рестартиране
                        if st.sidebar.button("🔄 Рестартирай сега"):
                            st.rerun()
                    else:
                        st.sidebar.error("Файлът е празен след обработка!")
                
                except Exception as e:
                    st.sidebar.error(f"Грешка: {e}")
    
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
if _filter and not selected_drug:
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
# KPI МЕТРИКИ (Mobile-First: Първото нещо което се вижда)
# ============================================================================

# Изчисляване на ключови метрики за избрания продукт
selected_product_data = df_filtered[df_filtered["Drug_Name"] == filters["product"]].copy()

if not selected_product_data.empty and len(periods) >= 2:
    # Последни 2 периода
    last_period = periods[-1]
    prev_period = periods[-2]
    
    # Units за последния период
    last_units = selected_product_data[selected_product_data["Quarter"] == last_period]["Units"].sum()
    prev_units = selected_product_data[selected_product_data["Quarter"] == prev_period]["Units"].sum()
    
    # % Ръст
    growth_pct = ((last_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
    
    # Market Share (само ако има Source колона)
    market_share_pct = 0
    if "Source" in df_raw.columns:
        # Намираме класа за избрания продукт
        product_source = selected_product_data["Source"].iloc[0] if len(selected_product_data) > 0 else None
        if product_source:
            # ATC клас проверка
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
                        (df_classes["Drug_Name"] == class_name) & 
                        (df_classes["Quarter"] == last_period)
                    ]["Units"].sum()
                    
                    national_product_last = df_raw[
                        (df_raw["Drug_Name"] == filters["product"]) & 
                        (df_raw["Quarter"] == last_period)
                    ]["Units"].sum()
                    
                    market_share_pct = (national_product_last / class_last * 100) if class_last > 0 else 0
    
    # Брой региони с продажби
    regions_count = selected_product_data[selected_product_data["Quarter"] == last_period]["Region"].nunique()
    
    # Показваме метриките (Mobile-First: вертикално)
    st.markdown("### 📊 Ключови показатели")
    
    region_label = filters["region"] if filters["region"] != "Всички" else "Всички региони"
    brick_label = filters["district"] if filters.get("district") and filters["district"] != "Всички" else "Всички Брикове"
    st.info(f"📍 **Анализ за:** {region_label} | **Брик:** {brick_label}")
    
    st.metric(
        label=f"Продажби {last_period}",
        value=f"{int(last_units):,} опак.",
        delta=f"{growth_pct:+.1f}%"
    )
    
    st.metric(
        label="Market Share (национално)",
        value=f"{market_share_pct:.2f}%",
        delta=None
    )
    
    st.metric(
        label="Активни региони",
        value=f"{regions_count}",
        delta=None
    )
    
    # Ръст в опаковки
    growth_units = int(last_units - prev_units)
    st.metric(
        label="Промяна опаковки",
        value=f"{abs(growth_units):,}",
        delta=f"{'↑' if growth_units > 0 else '↓'} {abs(growth_pct):.1f}%"
    )
    
    st.markdown("---")


# ============================================================================
# ТАБОВЕ - ДИНАМИЧНИ СПОРЕД РОЛЯ
# ============================================================================

# Табове – всички потребители виждат Dashboard, Brick, Сравнение, Last vs Previous, EI и AI Analyst
tab_timeline, tab_brick, tab_comparison, tab_quarter, tab_ei, tab_ai = st.tabs([
    "📈 Dashboard",
    "🗺️ По Brick (райони)",
    "⚖️ Сравнение",
    "📅 Последно vs Предишно",
    "📊 Еволюционен Индекс",
    "🤖 AI Analyst"
])

# --- ТАБ 1: ПО ТРИМЕСЕЧИЕ ---
with tab_timeline:
    # Изчисляване на метриката
    df_agg, y_col, y_label = calculate_metric_data(
        df=df_filtered,  # Филтриран по регион/brick (за графиката)
        products_list=products_on_chart,
        periods=periods,
        metric=metric,
        df_full=df_raw,  # Пълен национален dataset (за Market Share)
    )
    
    # Създаване на линейна графика и Market Share таблица
    df_agg_result = create_timeline_chart(
        df_agg=df_agg,
        y_col=y_col,
        y_label=y_label,
        periods=periods,
        sel_product=filters["product"],
        competitors=filters["competitors"],
    )
    
    # Показване на Market Share таблици под графиката
    if df_agg_result is not None:
        show_market_share_table(df_agg_result, period_col="Quarter", is_national=True, key_suffix="national")
        if filters["region"] != "Всички":
            st.markdown("---")
            df_regional_share = calculate_regional_market_share(
                df=df_filtered,
                products_list=products_on_chart,
                periods=periods,
                period_col="Quarter"
            )
            if not df_regional_share.empty and "Market_Share_%" in df_regional_share.columns:
                show_market_share_table(df_regional_share, period_col="Quarter", is_national=False, key_suffix="regional")


# --- ТАБ 2: ПО BRICK ---
with tab_brick:
    create_brick_charts(
        df=df_raw,  # Използваме пълните данни, не филтрираните
        products_list=products_on_chart,
        sel_product=filters["product"],
        competitors=filters["competitors"],
        periods=periods,
    )


# --- ТАБ 3: СРАВНЕНИЕ ---
with tab_comparison:
    # Period comparison
    create_period_comparison(
        df=df_filtered,
        products_list=products_on_chart,
        periods=periods,
    )
    
    st.divider()
    
    # Regional comparison за последния период
    if periods:
        create_regional_comparison(
            df=df_raw,
            products_list=products_on_chart,
            period=periods[-1],
        )


# --- ТАБ 4: ПОСЛЕДНО VS ПРЕДИШНО ТРИМЕСЕЧИЕ ---
with tab_quarter:
    render_last_vs_previous_quarter(df_raw, period_col="Quarter")


# --- ТАБ 5: ЕВОЛЮЦИОНЕН ИНДЕКС ---
with tab_ei:
    render_evolution_index_tab(
        df_filtered=df_filtered,
        df_national=df_raw,
        periods=periods,
        filters=filters,
        period_col="Quarter",
    )


# --- ТАБ 6: AI ANALYST ---
with tab_ai:
    render_ai_analysis_tab(
        df=df_filtered,
        sel_product=filters["product"],
        competitors=filters["competitors"],
    )


# ============================================================================
# ЕКСПОРТ НА ДАННИ
# ============================================================================

with st.expander("📋 Данни"):
    st.dataframe(df_chart, use_container_width=True, height=300)

csv = df_chart.to_csv(index=False)
st.download_button(
    "📥 Download CSV",
    data=csv,
    file_name="pharma_export.csv",
    mime="text/csv"
)
