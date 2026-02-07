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
)
from ai_analysis import render_ai_analysis_tab
from drug_molecules import add_drug_to_cache
from comparison_tools import create_period_comparison, create_regional_comparison


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

st.title("📊 Pharma Sales Data")
st.markdown(
    "**Регион** → **Медикамент** → **Молекула** → **Brick** – "
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
# SIDEBAR - ОПЦИИ И ФИЛТРИ
# ============================================================================

st.sidebar.header("Опции")

# Показване на заредените категории
if "Source" in df_raw.columns:
    sources = sorted(df_raw["Source"].unique())
    st.sidebar.caption(f"Заредени: {', '.join(sources)}")

# Бутон за обновяване на данните
if st.sidebar.button("Обнови данните", help="При добавяне на нови Excel файлове"):
    get_cached_data.clear()
    st.rerun()

# Статистика
st.success(
    f"**{len(df_raw):,}** реда | "
    f"{df_raw['Region'].nunique()} региона | "
    f"{df_raw['Drug_Name'].nunique()} продукта | "
    f"{df_raw['Source'].nunique()} категории"
)

# Създаване на филтри
filters = create_filters(df_raw)

# Прилагане на филтрите
df_filtered = apply_filters(df_raw, filters)

# Селектор за метрика
metric, share_in_molecule = create_metric_selector()

# Добавяне на молекула (за админи)
with st.sidebar.expander("➕ Добави молекула"):
    new_drug = st.text_input("Препарат", placeholder="LIPOCANTE")
    new_mol = st.text_input("Молекула", placeholder="Pitavastatin")
    if st.button("Добави") and new_drug and new_mol:
        add_drug_to_cache(new_drug.strip(), new_mol.strip())
        st.success(f"Добавено: {new_drug} → {new_mol}")
        st.rerun()


# ============================================================================
# ПОДГОТОВКА НА ДАННИ ЗА ВИЗУАЛИЗАЦИЯ
# ============================================================================

# Продукти за показване: основен + конкуренти
products_on_chart = [filters["product"]] + [
    c for c in filters["competitors"] if c != filters["product"]
]

# Филтриране само на избраните продукти
df_chart = df_filtered[df_filtered["Drug_Name"].isin(products_on_chart)].copy()

# Сортиране на периодите
periods = get_sorted_periods(df_raw)


# ============================================================================
# ТАБОВЕ - ОСНОВНИ ВИЗУАЛИЗАЦИИ
# ============================================================================

tab_home, tab_timeline, tab_brick, tab_comparison, tab_ai = st.tabs([
    "🏠 Начало",
    "📈 По тримесечие",
    "🗺️ По Brick (райони)",
    "⚖️ Сравнение",
    "🤖 AI Анализ"
])

# --- ТАБ 0: НАЧАЛО (DASHBOARD) ---
with tab_home:
    st.header("📊 Преглед на данните")
    st.markdown("Бърз поглед към ключовите показатели и трендове на **STADA продуктите**.")
    
    # Филтрирай само STADA продукти за dashboard
    df_stada = df_raw[df_raw["Drug_Name"].isin(config.STADA_PRODUCTS)].copy()
    
    if df_stada.empty:
        st.warning("Няма данни за STADA продукти.")
    else:
        # Key Metrics - Cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_units = df_stada["Units"].sum()
            st.metric(
                "STADA продажби",
                f"{total_units:,.0f} опак.",
                help="Общо продадени опаковки за всички STADA продукти"
            )
        
        with col2:
            total_products = df_stada["Drug_Name"].nunique()
            st.metric(
                "STADA продукти",
                f"{total_products}",
                help="Брой STADA продукти в данните"
            )
        
        with col3:
            total_regions = df_stada["Region"].nunique()
            st.metric(
                "Региони",
                f"{total_regions}",
                help="Брой региони с STADA продажби"
            )
        
        st.divider()
        
        # Top performers (по Units) - без GRAND TOTAL
        st.subheader("🏆 Топ 5 STADA продукта (по продажби)")
        df_stada_clean = df_stada[df_stada["Drug_Name"] != "GRAND TOTAL"].copy()
        top_products = df_stada_clean.groupby("Drug_Name")["Units"].sum().sort_values(ascending=False).head(5)
        
        if not top_products.empty:
            top_df = pd.DataFrame({
                "Продукт": top_products.index,
                "Опаковки": top_products.values
            })
            top_df["Опаковки"] = top_df["Опаковки"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(top_df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Growth analysis - показваме top 3 с най-висок ръст
        st.subheader("📈 Най-бърз растеж (последни 2 периода)")
        
        if len(periods) >= 2:
            last_period = periods[-1]
            prev_period = periods[-2]
            
            # Units по продукт за последните 2 периода (само STADA, без GRAND TOTAL)
            df_growth = df_stada_clean[df_stada_clean["Quarter"].isin([last_period, prev_period])]
            growth_pivot = df_growth.groupby(["Drug_Name", "Quarter"])["Units"].sum().reset_index()
            growth_pivot = growth_pivot.pivot(index="Drug_Name", columns="Quarter", values="Units")
            
            if prev_period in growth_pivot.columns and last_period in growth_pivot.columns:
                growth_pivot["Ръст %"] = (
                    (growth_pivot[last_period] / growth_pivot[prev_period].replace(0, float("nan")) - 1) * 100
                )
                growth_pivot = growth_pivot.dropna(subset=["Ръст %"])
                growth_pivot = growth_pivot.sort_values("Ръст %", ascending=False).head(3)
                
                if not growth_pivot.empty:
                    growth_display = pd.DataFrame({
                        "Продукт": growth_pivot.index,
                        "Ръст": growth_pivot["Ръст %"].apply(lambda x: f"{x:+.1f}%")
                    })
                    st.dataframe(growth_display, use_container_width=True, hide_index=True)
                else:
                    st.info("Няма достатъчно данни за изчисляване на ръст.")
        else:
            st.info("Нужни са поне 2 периода за изчисляване на ръст.")
        
        st.divider()
        
        # Проблемни продукти (negative growth)
        st.subheader("⚠️ STADA продукти с отрицателен ръст")
        
        if len(periods) >= 2:
            df_decline = df_stada_clean[df_stada_clean["Quarter"].isin([last_period, prev_period])]
            decline_pivot = df_decline.groupby(["Drug_Name", "Quarter"])["Units"].sum().reset_index()
            decline_pivot = decline_pivot.pivot(index="Drug_Name", columns="Quarter", values="Units")
            
            if prev_period in decline_pivot.columns and last_period in decline_pivot.columns:
                decline_pivot["Ръст %"] = (
                    (decline_pivot[last_period] / decline_pivot[prev_period].replace(0, float("nan")) - 1) * 100
                )
                decline_pivot = decline_pivot[decline_pivot["Ръст %"] < 0]
                decline_pivot = decline_pivot.sort_values("Ръст %").head(5)
                
                if not decline_pivot.empty:
                    decline_display = pd.DataFrame({
                        "Продукт": decline_pivot.index,
                        "Спад": decline_pivot["Ръст %"].apply(lambda x: f"{x:.1f}%")
                    })
                    st.dataframe(decline_display, use_container_width=True, hide_index=True)
                else:
                    st.success("Няма STADA продукти с отрицателен ръст!")
        else:
            st.info("Нужни са поне 2 периода за изчисляване на ръст.")
    
    st.divider()
    
    # Бързи линкове и съвети
    st.subheader("💡 Следващи стъпки")
    st.markdown("""
    - **📈 По тримесечие:** Виж тренда на твоя продукт спрямо конкуренти
    - **🗺️ По Brick:** Анализирай кои региони/райони са най-силни
    - **⚖️ Сравнение:** Сравни 2 периода или региони
    - **🤖 AI Анализ:** Задай въпрос и получи insights от данните
    """)

# --- ТАБ 1: ПО ТРИМЕСЕЧИЕ ---
with tab_timeline:
    # Изчисляване на метриката
    df_agg, y_col, y_label = calculate_metric_data(
        df=df_filtered,
        products_list=products_on_chart,
        periods=periods,
        metric=metric,
        share_in_molecule=share_in_molecule,
        molecule=filters["product_molecule"],
    )
    
    # Създаване на линейна графика
    create_timeline_chart(
        df_agg=df_agg,
        y_col=y_col,
        y_label=y_label,
        periods=periods,
        sel_product=filters["product"],
        competitors=filters["competitors"],
    )
    
    # Дял на продукта (ако има конкуренти)
    if filters["competitors"] and filters["product"] in df_filtered["Drug_Name"].values:
        total_by_q = df_filtered.groupby("Quarter")["Units"].sum()
        me_by_q = df_filtered[
            df_filtered["Drug_Name"] == filters["product"]
        ].groupby("Quarter")["Units"].sum()
        
        share = (me_by_q / total_by_q.replace(0, float("nan")) * 100).round(1)
        last_share = share.iloc[-1] if len(share) and not pd.isna(share.iloc[-1]) else 0
        
        st.metric(
            f"Дял {filters['product']} (%) – последен период",
            f"{last_share:.1f}%"
        )


# --- ТАБ 2: ПО BRICK (РАЙОНИ) ---
with tab_brick:
    create_brick_charts(
        df=df_raw,  # Използваме пълните данни, не филтрираните
        products_list=products_on_chart,
        sel_product=filters["product"],
        competitors=filters["competitors"],
        periods=periods,
    )


# --- ТАБ 3: СРАВНЕНИЕ НА ПЕРИОДИ ---
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


# --- ТАБ 4: AI АНАЛИЗ ---
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
