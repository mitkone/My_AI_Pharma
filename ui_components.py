"""
Преизползваеми UI компоненти за Streamlit приложението.
Съдържа функции за:
- Филтри (регион, медикамент, молекула, brick)
- Графики (линейни, bar charts)
- Метрики и статистики
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Optional, Tuple
import config
from logic import is_atc_class
from dashboard_config import get_chart_sort_order, get_chart_height, get_chart_margins, get_chart_text_color


def create_filters(df: pd.DataFrame, default_product: str = None, use_sidebar: bool = True) -> dict:
    """
    Създава sidebar филтри за избор на регион, медикамент, молекула, brick.
    
    Параметри
    ---------
    df : pd.DataFrame
        Данни за филтриране
    default_product : str, optional
        Продукт за автоматично избиране (от Quick Search)
    
    Връща
    ------
    dict
        Речник с избраните стойности от потребителя
    """
    ui = st.sidebar if use_sidebar else st
    ui.header("Филтри")
    
    # Списъци САМО от реално присъстващи стойности
    region_values = df["Region"].dropna().astype(str).str.strip()
    region_values = sorted(region_values[region_values != ""].unique().tolist())
    regions = ["Всички"] + region_values
    allowed_region_names = region_values
    drugs_raw = sorted(df["Drug_Name"].dropna().unique().tolist())
    drugs = ["— Избери медикамент —"] + drugs_raw
    molecules = sorted(df["Molecule"].dropna().unique().tolist())
    has_district = "District" in df.columns
    districts = ["Всички"] + sorted(df["District"].dropna().unique().tolist()) if has_district else []
    
    # Валидация
    if st.session_state.get("sb_region") not in regions:
        if "sb_region" in st.session_state:
            del st.session_state["sb_region"]
    if st.session_state.get("sb_district") not in districts:
        if "sb_district" in st.session_state:
            del st.session_state["sb_district"]
    if st.session_state.get("sb_product") not in drugs:
        if "sb_product" in st.session_state:
            del st.session_state["sb_product"]
    
    # Медикамент първо, след това Регион (mobile: по-важно е изборът на медикамент)
    c1, c2 = ui.columns(2)
    with c1:
        idx = 0  # по подразбиране: "— Избери медикамент —"
        if default_product and default_product in drugs_raw:
            idx = drugs.index(default_product)
        elif st.session_state.get("sb_product") in drugs:
            idx = drugs.index(st.session_state["sb_product"])
        sel_product = ui.selectbox(
            "Медикамент (основен)",
            drugs,
            index=idx,
            help="Избери медикамент от списъка",
            key="sb_product",
        )
    with c2:
        sel_region = ui.selectbox(
            "Регион",
            regions,
            index=0,
            help="Пловдив, Варна, Бургас... или Всички",
            key="sb_region",
        )
    
    # Brick (район) – под регион и медикамент
    sel_district = ui.selectbox(
        "Brick (район)",
        districts,
        index=0,
        help="Опционално – налично при Total Bricks данни",
        key="sb_district",
    ) if has_district else "Всички"
    
    # Конкуренти – само ако е избран реален медикамент
    PLACEHOLDER = "— Избери медикамент —"
    sel_product_effective = sel_product if sel_product != PLACEHOLDER and sel_product in drugs_raw else (drugs_raw[0] if drugs_raw else None)
    prod_sources = df[df["Drug_Name"] == sel_product_effective]["Source"].unique() if sel_product_effective else []
    
    # Вземаме ВСИЧКИ Drug_Name от същата Source (категория)
    same_source_drugs = df[df["Source"].isin(prod_sources)]["Drug_Name"].unique()
    
    # Разделяме ATC класове от медикаменти
    # ATC класовете имат формат: Буква+цифри (напр. R06A0, B01C2, C09D3)
    categories = []
    competitor_drugs = []
    
    for item in same_source_drugs:
        if item == sel_product_effective:
            continue
        
        # Проверка дали е ATC клас:
        # 1. Първите 3-6 символа: започва с буква, има цифри
        # 2. След кода има поне 2 думи описание
        # 3. Цялото име е с главни букви
        # 4. Не е "GRAND TOTAL" или "Region"
        
        if item in ["GRAND TOTAL", "Grand Total"] or item.startswith("Region"):
            continue
            
        # ATC код формат: 1-3 букви + 2-4 цифри + опционално буква
        # Примери: R06A0, B01C2, C09D3, C10A1, N06D0
        first_word = item.split()[0] if item.split() else ""
        
        # Проверка за ATC код като първа дума
        is_atc = (
            len(first_word) >= 4 and  # Минимум 4 символа (напр. R06A)
            len(first_word) <= 7 and  # Максимум 7 (напр. C09CA01)
            first_word[0].isalpha() and  # Започва с буква
            any(c.isdigit() for c in first_word) and  # Има цифра
            first_word.isupper() and  # С главни букви
            len(item.split()) >= 2  # Има описание след кода
        )
        
        if is_atc:
            categories.append(item)
        else:
            competitor_drugs.append(item)
    
    # Подреждаме опциите: ПЪРВО класовете, ПОСЛЕ медикаментите
    competitor_options = []
    
    # ВАЖНО: Добавяме класовете с иконка ПЪРВИ
    if categories:
        for cat in sorted(categories):
            competitor_options.append(f"📊 КЛАС: {cat}")
    
    # След това добавяме медикаментите
    # Изчисляване на продажби за всеки медикамент (за сортиране)
    sales_by_drug = df.groupby("Drug_Name")["Units"].sum().to_dict()
    
    # Сортиране на медикаментите по продажби (descending)
    competitor_drugs_sorted = sorted(
        competitor_drugs, 
        key=lambda x: sales_by_drug.get(x, 0), 
        reverse=True
    )
    
    # Добавяне на продажби до името (форматирано)
    competitor_drugs_with_sales = []
    for drug in competitor_drugs_sorted:
        sales = sales_by_drug.get(drug, 0)
        competitor_drugs_with_sales.append(f"{drug} ({int(sales):,} опак.)")
    
    competitor_options.extend(competitor_drugs_with_sales)
    
    # Ако няма нищо, показваме всички медикаменти (без placeholder)
    if not competitor_options:
        competitor_options = [d for d in drugs_raw if d != sel_product_effective]
    
    # Top 3: изчисли по избрания Region/Brick, запис в session_state, rerun
    col1, col2 = ui.columns([3, 1])
    with col1:
            ui.markdown("**Добави конкуренти**")
    with col2:
        add_top3 = ui.button("Top 3", help="Наш продукт + Top 3 по продажби за избрания регион", key="top3_btn")
    
    # Филами данните по избран Region и Brick за Top 3
    df_filtered_for_top3 = df.copy()
    if sel_region != "Всички":
        df_filtered_for_top3 = df_filtered_for_top3[df_filtered_for_top3["Region"] == sel_region]
    if has_district and sel_district != "Всички":
        df_filtered_for_top3 = df_filtered_for_top3[df_filtered_for_top3["District"] == sel_district]
    
    if add_top3:
        from logic import compute_top3_drugs
        top3_drugs = compute_top3_drugs(
            df_filtered_for_top3,
            sel_region,
            sel_district,
            has_district,
            tuple(competitor_drugs),
        )
        if top3_drugs:
            opt_to_drug = {}
            for opt in competitor_options:
                if not opt.startswith("📊 КЛАС:"):
                    drug_key = opt.split(" (")[0] if " (" in opt else opt
                    opt_to_drug[drug_key.strip()] = opt
            top3_options = [opt_to_drug[d] for d in top3_drugs if d in opt_to_drug]
            st.session_state["sb_competitors"] = top3_options
            st.session_state["selected_drugs"] = [sel_product_effective] + top3_drugs if sel_product_effective else top3_drugs
            st.rerun()
    
    help_text = "📊 Класове (общи продажби) | Медикаменти сортирани по продажби (най-много → най-малко)"
    # Не подаваме default, за да избегнем конфликт с директно задаване на st.session_state[\"sb_competitors\"]
    competitor_products = ui.multiselect(
        "Избери конкуренти",
        competitor_options,
        help=help_text,
        key="sb_competitors",
    )
    
    # Обработваме избраните конкуренти - махаме префикса и продажбите от имената
    processed_competitors = []
    
    for item in competitor_products:
        if item.startswith("📊 КЛАС: "):
            # Извличаме името на класа (след префикса)
            class_name = item.replace("📊 КЛАС: ", "")
            processed_competitors.append(class_name)
        else:
            # Премахваме продажбите от името (ако има)
            # Пример: "CRESTOR (120,345 опак.)" → "CRESTOR"
            clean_name = item.split(" (")[0] if " (" in item else item
            processed_competitors.append(clean_name)
    
    return {
        "region": sel_region,
        "product": sel_product_effective if sel_product != PLACEHOLDER else None,
        "district": sel_district,
        "competitors": processed_competitors,  # Вече включва и класовете
        "product_source": prod_sources[0] if len(prod_sources) > 0 else None,
        "has_district": has_district,
        "allowed_region_names": allowed_region_names,  # само региони от списъка – за графики и AI
    }


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Прилага избраните филтри върху данните.
    
    Параметри
    ---------
    df : pd.DataFrame
        Пълен набор от данни
    filters : dict
        Филтри от create_filters()
    
    Връща
    ------
    pd.DataFrame
        Филтрирани данни
    """
    df_filtered = df.copy()
    
    # Филтър по регион
    if filters["region"] != "Всички":
        df_filtered = df_filtered[df_filtered["Region"] == filters["region"]]
    
    # Филтър по brick (район)
    if filters["has_district"] and filters["district"] != "Всички":
        df_filtered = df_filtered[df_filtered["District"] == filters["district"]]
    
    return df_filtered


def create_metric_selector() -> Tuple[str, bool]:
    """
    Връща метриката (винаги Units, другите данни се показват в hover).
    
    Връща
    ------
    Tuple[str, bool]
        (избрана_метрика, share_in_molecule) - винаги ("Units (опак.)", False)
    """
    # Метриката е винаги Units, Market Share и % Ръст се показват в hover
    return "Units (опак.)", False


@st.cache_data(show_spinner=False)
def calculate_metric_data(
    df: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    metric: str,
    period_col: str = "Quarter",
    df_full: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Изчислява метриката и допълнителни данни за hover.
    Метриката е винаги Units (опаковки).
    Допълнително изчислява: промяна, % ръст, market share, промяна в дял.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни (по регион/brick) - за показване на графиката
    products_list : List[str]
        Списък от продукти за показване (основен + конкуренти)
    periods : List[str]
        Сортирани периоди
    metric : str
        Метрика за изчисляване (винаги "Units (опак.)")
    period_col : str
        Име на колоната с периоди
    df_full : Optional[pd.DataFrame]
        Пълен dataset (национален) - за изчисляване на Market Share спрямо целия market
    
    Връща
    ------
    Tuple[pd.DataFrame, str, str]
        (DataFrame с всички метрики, име на Y колоната, етикет за Y оста)
    """
    # Ако няма пълен dataset, използваме филтрирания
    if df_full is None:
        df_full = df
    # Филтриране само на избраните продукти
    df_chart = df[df["Drug_Name"].isin(products_list)].copy()
    
    # Агрегиране по период и продукт
    df_agg_base = df_chart.groupby([period_col, "Drug_Name"], as_index=False)["Units"].sum()
    
    # Метриката е винаги Units, но изчисляваме и допълнителни данни за hover
    df_agg = df_agg_base.copy()
    y_col = "Units"
    y_label = "Опаковки"
    
    # 1. Промяна в опаковки (абсолютна)
    pivot_units = df_agg_base.pivot(index="Drug_Name", columns=period_col, values="Units")
    pivot_units = pivot_units.reindex(columns=periods)
    
    # Абсолютна промяна
    abs_change = pivot_units.diff(axis=1)
    df_abs = abs_change.reset_index().melt(
        id_vars="Drug_Name",
        var_name=period_col,
        value_name="Change_Units"
    )
    df_agg = df_agg.merge(df_abs, on=["Drug_Name", period_col], how="left")
    
    # 2. % Промяна (ръст спрямо предходен период)
    pct_change = pivot_units.pct_change(axis=1, fill_method=None) * 100
    df_pct = pct_change.reset_index().melt(
        id_vars="Drug_Name",
        var_name=period_col,
        value_name="Growth_%"
    )
    df_agg = df_agg.merge(df_pct, on=["Drug_Name", period_col], how="left")
    
    # 3. Market Share % (спрямо целия клас/категория)
    # ВАЖНО: Изключваме ATC класовете от изчислението на total, за да избегнем дублиране
    # Класовете са сума на медикаментите, не трябва да се броят отделно
    # Market Share изчисление:
    # За медикамент: % спрямо КЛАСА (напр. C10A1 STATINS) за съответния период
    # За клас: винаги 100%
    
    # Намираме класовете в df_full
    df_classes = df_full[df_full["Drug_Name"].apply(is_atc_class)].copy()
    
    # Създаваме маппинг: period → ATC клас опаковки
    # ВАЖНО: Трябва да намерим ПРАВИЛНИЯ клас - този който е от същия файл (Source) като избрания продукт!
    class_name = None
    if len(df_classes) > 0:
        # Намираме уникалните класове
        unique_classes = df_classes["Drug_Name"].unique()
        
        # Ако има Source колона, използваме я за намиране на правилния клас
        if "Source" in df_full.columns and len(products_list) > 0:
            # Вземаме първия избран продукт (основния)
            main_product = products_list[0]
            product_data = df_full[df_full["Drug_Name"] == main_product]
            
            if len(product_data) > 0:
                # Намираме Source на избрания продукт
                product_source = product_data["Source"].iloc[0] if "Source" in product_data.columns else None
                
                if product_source:
                    # Намираме класа със същия Source
                    matching_classes = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
                    if len(matching_classes) > 0:
                        class_name = matching_classes[0]
        
        # Ако нямаме Source или не намерихме клас, използваме първия (старата логика)
        if class_name is None and len(unique_classes) > 0:
            class_name = unique_classes[0]
        
        if class_name:
            # Total = Units на класа за всеки период
            class_by_period = df_classes[df_classes["Drug_Name"] == class_name].groupby(period_col)["Units"].sum()
        else:
            # Fallback ако няма класове
            df_for_total = df_full[~df_full["Drug_Name"].apply(is_atc_class)].copy()
            class_by_period = df_for_total.groupby(period_col)["Units"].sum()
    else:
        # Fallback ако няма класове
        df_for_total = df_full[~df_full["Drug_Name"].apply(is_atc_class)].copy()
        class_by_period = df_for_total.groupby(period_col)["Units"].sum()
    
    # За Market Share използваме НАЦИОНАЛНИ Units от df_full, не филтрирани!
    # Създаваме маппинг: (Drug_Name, Period) → Национални Units
    national_units = df_full.groupby([period_col, "Drug_Name"], as_index=False)["Units"].sum()
    national_units_dict = {}
    for _, row_nat in national_units.iterrows():
        key = (row_nat["Drug_Name"], row_nat[period_col])
        national_units_dict[key] = row_nat["Units"]
    
    def calc_share(row):
        # Ако е ATC клас → Market Share = 100% (класът Е пазара)
        if is_atc_class(row["Drug_Name"]):
            return 100.0
        
        # Медикамент: % спрямо класа за СЪЩИЯ период
        # ВАЖНО: Използваме НАЦИОНАЛНИ Units, не филтрирани по регион!
        drug_name = row["Drug_Name"]
        period = row[period_col]
        national_drug_units = national_units_dict.get((drug_name, period), 0)
        
        total = class_by_period.get(period, 0)
        return 100 * national_drug_units / total if total > 0 else 0
    
    df_agg["Market_Share_%"] = df_agg.apply(calc_share, axis=1)
    
    # 4. Промяна в Market Share (процентни пунктове)
    pivot_share = df_agg.pivot(index="Drug_Name", columns=period_col, values="Market_Share_%")
    pivot_share = pivot_share.reindex(columns=periods)
    change_share = pivot_share.diff(axis=1)
    
    df_share_change = change_share.reset_index().melt(
        id_vars="Drug_Name",
        var_name=period_col,
        value_name="Change_Share_pp"
    )
    df_agg = df_agg.merge(df_share_change, on=["Drug_Name", period_col], how="left")
    
    # За ATC класове промяната в дял е винаги 0 (класът е винаги 100%)
    df_agg.loc[df_agg["Drug_Name"].apply(is_atc_class), "Change_Share_pp"] = 0.0
    
    # Закръгляване на всички изчислени метрики до 2 знака
    df_agg["Change_Units"] = df_agg["Change_Units"].round(0)  # Цели числа
    df_agg["Growth_%"] = df_agg["Growth_%"].round(2)  # 2 знака
    df_agg["Market_Share_%"] = df_agg["Market_Share_%"].round(2)  # 2 знака
    df_agg["Change_Share_pp"] = df_agg["Change_Share_pp"].round(2)  # 2 знака
    
    # Сортиране по период за правилно свързване на линиите в графиката
    period_order = {p: i for i, p in enumerate(periods)}
    df_agg["_sort"] = df_agg[period_col].map(period_order)
    df_agg = df_agg.sort_values(["Drug_Name", "_sort"]).drop(columns=["_sort"])
    
    # Само избраните продукти (без допълнителни от данните)
    df_agg = df_agg[df_agg["Drug_Name"].isin(products_list)].copy()
    return df_agg, y_col, y_label


def create_timeline_chart(
    df_agg: pd.DataFrame,
    y_col: str,
    y_label: str,
    periods: List[str],
    sel_product: str,
    competitors: List[str],
    period_col: str = "Quarter"
) -> pd.DataFrame:
    """
    Създава линейна графика по тримесечия/месеци.
    
    Параметри
    ---------
    df_agg : pd.DataFrame
        Агрегирани данни с метриката
    y_col : str
        Име на колоната за Y-ос
    y_label : str
        Етикет за Y-ос
    periods : List[str]
        Сортирани периоди за X-ос
    sel_product : str
        Основен продукт
    competitors : List[str]
        Конкуренти
    period_col : str
        Име на колоната с периоди
    
    Връща
    ------
    pd.DataFrame
        df_agg за показване на Market Share таблица
    """
    if df_agg.empty:
        st.info("Няма данни за избраните филтри.")
        return
    
    # Заглавие на графиката
    comp_text = ""
    if competitors:
        if len(competitors) > 2:
            comp_text = f" vs {', '.join(competitors[:2])}…"
        else:
            comp_text = f" vs {', '.join(competitors)}"
    
    title = f"{y_label} – {sel_product}{comp_text}"
    
    # Подготовка на customdata с всички метрики
    # Форматиране на текстовите индикатори за растеж/спад
    def format_growth(value):
        """Форматира % ръст с оцветен индикатор"""
        if pd.isna(value):
            return "—"
        elif value > 0:
            return f"🟢 +{value:.2f}%"
        elif value < 0:
            return f"🔴 {value:.2f}%"
        else:
            return f"{value:.2f}%"
    
    def format_share_change(value):
        """Форматира промяна в дял с оцветен индикатор"""
        if pd.isna(value):
            return "—"
        elif value > 0:
            return f"🟢 +{value:.2f} pp"
        elif value < 0:
            return f"🔴 {value:.2f} pp"
        else:
            return f"{value:.2f} pp"
    
    # Добавяне на форматирани колони
    df_agg["Growth_Text"] = df_agg["Growth_%"].apply(format_growth)
    df_agg["Share_Change_Text"] = df_agg["Change_Share_pp"].apply(format_share_change)
    
    # customdata колони - САМО промяна и ръст (без Market Share)
    custom_cols = ["Change_Units", "Growth_Text"]
    for col in custom_cols:
        if col not in df_agg.columns:
            df_agg[col] = None
    
    # Създаване на линейна графика с хронологичен ред на периодите
    fig = px.line(
        df_agg,
        x=period_col,
        y=y_col,
        color="Drug_Name",
        markers=True,
        title=title,
        custom_data=custom_cols,
        category_orders={period_col: periods}  # Изрично задаваме хронологичния ред
    )
    
    # Hover template - опростен (без Market Share)
    fig.update_traces(
        mode="lines+markers",
        line=dict(width=3),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "%{x}<br>"
            "━━━━━━━━━━━━━━━━━━━━<br>"
            "💊 Опаковки: <b>%{y:,.0f}</b><br>"
            "📊 Промяна: <b>%{customdata[0]:+,.0f} опак.</b><br>"
            "% Ръст: <b>%{customdata[1]}</b>"
            "<extra></extra>"
        ),
    )
    
    fig.update_layout(
        height=get_chart_height(),
        legend_title="",
        showlegend=True,
        hovermode="closest",
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
        xaxis_tickangle=-45,
        xaxis=dict(
            categoryorder="array",
            categoryarray=periods,
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
            fixedrange=True,
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
            fixedrange=True,
        ),
        # Легенда ДОЛУ (Mobile-first: още по-долу за да не смачква графиката)
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.5,  # Още по-долу за mobile
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=30, b=0),  # Минимални margins за mobile
        font=dict(size=12),
    )
    
    st.plotly_chart(fig, width="stretch", config=config.PLOTLY_CONFIG)
    
    # Връщаме и df_agg за да можем да покажем Market Share данни извън функцията
    return df_agg


@st.cache_data(show_spinner=False)
def calculate_regional_market_share(
    df: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    period_col: str = "Quarter"
) -> pd.DataFrame:
    """
    Изчислява регионален market share спрямо филтрираните данни (регион/brick).
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни (по регион/brick)
    products_list : List[str]
        Списък от продукти
    periods : List[str]
        Сортирани периоди
    period_col : str
        Име на колоната с периоди
    
    Връща
    ------
    pd.DataFrame
        DataFrame с Regional Market Share
    """
    # Филтриране само на избраните продукти
    df_chart = df[df["Drug_Name"].isin(products_list)].copy()
    
    # Агрегиране по период и продукт
    df_agg = df_chart.groupby([period_col, "Drug_Name"], as_index=False)["Units"].sum()
    # Намираме класа в ФИЛТРИРАНИТЕ данни (регионален)
    df_classes = df[df["Drug_Name"].apply(is_atc_class)].copy()
    
    if len(df_classes) > 0:
        # Ако има Source колона, намираме правилния клас
        if "Source" in df.columns and len(products_list) > 0:
            main_product = products_list[0]
            product_data = df[df["Drug_Name"] == main_product]
            
            if len(product_data) > 0:
                product_source = product_data["Source"].iloc[0] if "Source" in product_data.columns else None
                
                if product_source:
                    matching_classes = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
                    if len(matching_classes) > 0:
                        class_name = matching_classes[0]
                        # Регионален total за класа
                        regional_class_by_period = df_classes[df_classes["Drug_Name"] == class_name].groupby(period_col)["Units"].sum()
                        
                        # Изчисляваме регионален market share
                        def calc_regional_share(row):
                            if is_atc_class(row["Drug_Name"]):
                                return 100.0
                            total = regional_class_by_period.get(row[period_col], 0)
                            return 100 * row["Units"] / total if total > 0 else 0
                        
                        df_agg["Market_Share_%"] = df_agg.apply(calc_regional_share, axis=1)
                        df_agg["Market_Share_%"] = df_agg["Market_Share_%"].round(2)
    
    return df_agg


def show_market_share_table(
    df_agg: pd.DataFrame,
    period_col: str = "Quarter",
    is_national: bool = True,
    key_suffix: str = "national",
    products_list: List[str] = None,
) -> None:
    """
    Показва stacked bar chart с Market Share – само избрания продукт + конкуренти.
    
    Параметри
    ---------
    df_agg : pd.DataFrame
        Агрегирани данни с изчислен Market Share
    period_col : str
        Име на колоната с периоди
    is_national : bool
        Дали е национален (True) или регионален (False) market share
    key_suffix : str
        Суфикс за уникален key (за national/regional при едновременно показване)
    products_list : list, optional
        Само тези продукти да се показват (основен + конкуренти); ако е None, показва всички от df_agg
    """
    import plotly.graph_objects as go
    
    if "Market_Share_%" not in df_agg.columns:
        return
    
    if products_list:
        df_agg = df_agg[df_agg["Drug_Name"].isin(products_list)].copy()
    
    # Различни заглавия в зависимост от типа
    if is_national:
        st.subheader("📊 Национален Market Share")
    else:
        st.subheader("📍 Регионален Market Share")
    
    # Филтрираме само медикаменти (без класове 100%, без Grand Total)
    df_drugs = df_agg[df_agg["Market_Share_%"] < 100].copy()
    if "Drug_Name" in df_drugs.columns:
        df_drugs = df_drugs[~df_drugs["Drug_Name"].isin(["GRAND TOTAL", "Grand Total"])]
    
    if len(df_drugs) == 0:
        st.info("Няма медикаменти за показване")
        return
    
    # Pivot таблица: периоди x продукти
    pivot = df_drugs.pivot(index=period_col, columns="Drug_Name", values="Market_Share_%")
    
    # Хронологично сортиране на периодите
    from data_processing import get_period_sort_key
    sorted_periods = sorted(pivot.index.tolist(), key=get_period_sort_key)
    pivot = pivot.reindex(sorted_periods)
    
    # Сортиране на продукти по пазарен дял (лидерът отгоре в стека)
    drug_order = pivot.sum().sort_values(ascending=True).index.tolist()
    pivot = pivot[drug_order]
    
    # Цветова палитра
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    # Horizontal stacked bar chart – винаги разгърнат, всички % видими (outside = винаги четливи)
    fig = go.Figure()
    for i, drug in enumerate(pivot.columns):
        fig.add_trace(go.Bar(
            x=pivot[drug],
            y=pivot.index,
            name=drug,
            orientation='h',
            marker_color=colors[i % len(colors)],
            text=pivot[drug].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x >= 0.5 else ""),
            textposition='inside',
            textfont=dict(color='white', size=11, family='Arial'),
        ))
    
    # Layout – auto-scale on load, дебели барове
    fig.update_layout(
        barmode='stack',
        bargap=0.1,
        xaxis_title='Market Share (%)',
        xaxis=dict(autorange=True, title_font=dict(size=14), tickfont=dict(size=12), fixedrange=True),
        yaxis_title=period_col,
        yaxis=dict(
            categoryorder='array',
            categoryarray=sorted_periods,
            autorange=True,
            title_font=dict(size=14),
            tickfont=dict(size=12),
            fixedrange=True,
        ),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5,
            font=dict(size=11),
        ),
        dragmode=False,
        uirevision='constant',
        height=800,
        margin=dict(l=10, r=10, t=20, b=20),
    )
    fig.update_traces(
        marker_line_width=1.5,
        opacity=0.9,
        width=0.8,
        hoverinfo='none',
        hovertemplate=None,
        selectedpoints=None,
        unselected=dict(marker=dict(opacity=1)),
    )
    
    st.plotly_chart(
        fig,
        width="stretch",
        config={'doubleClick': 'reset', 'displayModeBar': False},
    )
    
    # Различни обяснения
    if is_national:
        st.caption(
            "**Забележка:** Показва пазарен дял спрямо **националния market** (всички региони) "
            "за съответния период. Този % НЕ се променя при филтриране по регион."
        )
    else:
        st.caption(
            "**Забележка:** Показва пазарен дял спрямо **избрания регион/brick** "
            "за съответния период. Този % показва локалната позиция."
        )


def create_brick_charts(
    df: pd.DataFrame,
    products_list: List[str],
    sel_product: str,
    competitors: List[str],
    periods: List[str],
    period_col: str = "Quarter",
    selected_region: str = None,
    allowed_region_names: Optional[List[str]] = None,
) -> None:
    """
    Създава графики по региони и brick-ове.
    
    Параметри
    ---------
    df : pd.DataFrame
        Пълен набор от данни
    products_list : List[str]
        Продукти за показване
    sel_product : str
        Основен продукт
    competitors : List[str]
        Конкуренти
    periods : List[str]
        Сортирани периоди
    period_col : str
        Име на колоната с периоди
    """
    has_district = "District" in df.columns
    sel_region_brick = ""

    if not has_district:
        st.info('Избери лист "Total Bricks" за разбивка по региони и Brick-ове.')
        return
    
    st.subheader("Продажби по региони и Brick-ове")
    
    # Селектор за период – по подразбиране последно тримесечие (Q4 или последното)
    geo_period = st.selectbox(
        "Период (за опаковките)",
        ["Всички периоди (сума)", "Последно тримесечие"] + periods,
        index=1,
        key="geo_period",
    )
    
    # Филтриране по период
    if geo_period == "Всички периоди (сума)":
        df_geo_base = df.copy()
    elif geo_period == "Последно тримесечие":
        df_geo_base = df[df[period_col] == periods[-1]].copy()
    else:
        df_geo_base = df[df[period_col] == geo_period].copy()
    
    # Нормализиране за сравнение (category/whitespace)
    def _region_match(ser, val):
        if val is None or str(val).strip() == "" or str(val).strip().lower() == "всички":
            return pd.Series(False, index=ser.index)
        v = str(val).strip()
        return ser.astype(str).str.strip() == v

    # Ако е избран регион от филтрите – показваме САМО брикове в този регион
    if selected_region and selected_region != "Всички":
        by_region = False
        df_geo = df_geo_base[_region_match(df_geo_base["Region"], selected_region)].copy()
        group_col = "District"
        st.caption(f"📍 Брикове в регион **{selected_region}** (избран от филтрите)")
    else:
        level = st.radio(
            "Покажи по",
            ["Региони (Пловдив, Варна, Бургас...)", "Brick-ове в регион (избери регион по-долу)"],
            key="brick_level",
        )
        by_region = "Региони" in level
        if by_region:
            df_geo = df_geo_base.copy()
            group_col = "Region"
        else:
            sel_region_brick = st.selectbox(
                "Избери регион",
                sorted(df["Region"].dropna().astype(str).str.strip().unique().tolist()),
                key="sel_region_brick",
            )
            df_geo = df_geo_base[_region_match(df_geo_base["Region"], sel_region_brick)].copy()
            group_col = "District"
    
    # Филтриране САМО на избрания продукт + конкуренти; макс. 20 серии за четлива графика
    MAX_SERIES_BRICK = 20
    raw_allowed = list(products_list) if products_list else []
    if not raw_allowed:
        st.info("Избери поне един продукт от филтрите.")
        return
    # Подредба: първо основният продукт, после конкурентите (ограничени)
    allowed = [raw_allowed[0]] + [p for p in raw_allowed[1:] if p != raw_allowed[0]][: MAX_SERIES_BRICK - 1]
    allowed_set = set(allowed)
    if len(raw_allowed) > MAX_SERIES_BRICK:
        st.caption(f"Показани са само първите {MAX_SERIES_BRICK} продукта/конкуренти.")
    df_geo_chart = df_geo[df_geo["Drug_Name"].isin(allowed_set)].copy()
    df_geo_agg = df_geo_chart.groupby([group_col, "Drug_Name"], as_index=False)["Units"].sum()
    df_geo_agg = df_geo_agg[df_geo_agg["Drug_Name"].isin(allowed_set)]
    # Само стойности от филтрираните данни (региони ИЛИ брикове в избрания регион)
    if group_col == "Region" and allowed_region_names is not None:
        allowed_set_grp = set(str(r).strip() for r in allowed_region_names)
        df_geo_agg = df_geo_agg[df_geo_agg[group_col].astype(str).str.strip().isin(allowed_set_grp)]
    elif group_col == "District":
        # САМО брикове от df_geo (вече филтрирани по Region) – да не излизат брикове от други региони
        allowed_districts = set(df_geo[group_col].dropna().astype(str).str.strip().unique())
        df_geo_agg = df_geo_agg[df_geo_agg[group_col].astype(str).str.strip().isin(allowed_districts)]
    df_geo_agg = df_geo_agg.sort_values("Units", ascending=False)
    
    if df_geo_agg.empty:
        st.info("Няма данни за избраните продукти.")
        return
    
    # Bar chart за опаковки
    x_label = "Регион" if by_region else "Brick"
    comp_text = f" vs {', '.join(competitors[:2])}" + ("…" if len(competitors) > 2 else "") if competitors else ""
    
    df_geo_agg = df_geo_agg.copy()
    df_geo_agg["_lbl"] = df_geo_agg["Units"].apply(lambda u: f"{int(u):,}" if u > 0 else "")
    fig_geo = px.bar(
        df_geo_agg,
        y=group_col,
        x="Units",
        color="Drug_Name",
        barmode="group",
        orientation="h",
        text="_lbl",
        title=f"Опаковки по {x_label} – {sel_product}{comp_text}",
    )
    fig_geo.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{y}<br>%{x:,.0f} опак.<extra></extra>",
        textposition="inside",
        textfont=dict(size=10, color=get_chart_text_color()),
    )
    
    fig_geo.update_layout(
        height=max(get_chart_height(), len(df_geo_agg[group_col].unique()) * 28),
        legend_title="",
        xaxis=dict(title="", tickfont=dict(size=11), fixedrange=True),
        yaxis=dict(
            title="", tickfont=dict(size=11),
            categoryorder="total ascending" if get_chart_sort_order() == "desc" else "total descending",
            fixedrange=True,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        hovermode='closest',
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
        margin={**get_chart_margins(), "t": 30, "b": 20},
        font=dict(size=12),
    )
    st.plotly_chart(fig_geo, width="stretch", config=config.PLOTLY_CONFIG)

    # Графика за ръст % – брикове (при регион/избран регион) или региони (при Всички + Региони)
    st.markdown("#### 📈 Ръст % спрямо последно тримесечие")
    if "_growth_display" not in st.session_state:
        st.session_state["_growth_display"] = "pct"

    def _set_growth_mode_brick():
        st.session_state["_growth_display"] = st.session_state["growth_radio_brick"]

    st.radio(
        "Покажи по",
        options=["pct", "units"],
        format_func=lambda x: "Проценти" if x == "pct" else "Опаковки",
        index=0 if st.session_state.get("_growth_display", "pct") == "pct" else 1,
        key="growth_radio_brick",
        horizontal=True,
        on_change=_set_growth_mode_brick,
    )
    try:
        from logic import compute_last_vs_previous_rankings
        from data_processing import get_sorted_periods
        periods_sorted = get_sorted_periods(df, period_col)
        if len(periods_sorted) >= 2:
            grp_col = group_col
            eff_region = selected_region if (selected_region and selected_region != "Всички") else sel_region_brick
            if grp_col == "District" and eff_region:
                df_grp = df[_region_match(df["Region"], eff_region)].copy()
            else:
                df_grp = df
            res = compute_last_vs_previous_rankings(
                df_grp, sel_product, period_col, tuple(periods_sorted), group_col=grp_col
            )
            if res and not res["merged"].empty:
                m = res["merged"].sort_values("Growth_%", ascending=True)
                if grp_col == "Region" and allowed_region_names is not None:
                    allowed_r_set = set(str(r).strip() for r in allowed_region_names)
                    m = m[m["Region"].astype(str).str.strip().isin(allowed_r_set)]
                elif grp_col == "District":
                    # Само брикове от избрания регион (df_geo вече е филтриран)
                    allowed_d = set(df_geo["District"].dropna().astype(str).str.strip().unique())
                    m = m[m["Region"].astype(str).str.strip().isin(allowed_d)]  # "Region" колоната съдържа District при grp_col=District
                if m.empty:
                    st.caption("Няма данни за ръст за избраните региони.")
                else:
                    m = m.copy()
                    m["Units_Delta"] = m["Last_Units"] - m["Previous_Units"]
                    lbl = "Брик" if grp_col == "District" else "Регион"
                    disp = st.session_state.get("_growth_display", "pct")
                    if disp == "units":
                        m = m.sort_values("Units_Delta", ascending=False)
                        x_vals = m["Units_Delta"]
                        txts = [f"{u:+,.0f} оп." for u in m["Units_Delta"]]
                        colors_g = ["#2ecc71" if v >= 0 else "#e74c3c" for v in m["Units_Delta"]]
                    else:
                        m = m.sort_values("Growth_%", ascending=False)
                        x_vals = m["Growth_%"]
                        txts = [f"{g:+.1f}%" for g in m["Growth_%"]]
                        colors_g = ["#2ecc71" if v >= 0 else "#e74c3c" for v in m["Growth_%"]]
                    import plotly.graph_objects as go
                    fig_g = go.Figure()
                    hover_tmpl = "<b>%{y}</b><br>Ръст: %{x:+.1f}%<br>Промяна: %{customdata:+,.0f} оп.<extra></extra>" if disp == "pct" else "<b>%{y}</b><br>Промяна: %{x:+,.0f} оп.<extra></extra>"
                    fig_g.add_trace(go.Bar(
                        x=x_vals.tolist(),
                        y=m["Region"].tolist(),
                        orientation="h",
                        marker_color=colors_g,
                        text=txts,
                        textposition="inside",
                        textfont=dict(size=9, color=get_chart_text_color()),
                        customdata=m["Units_Delta"].tolist() if disp == "pct" else [0] * len(m),
                        hovertemplate=hover_tmpl,
                    ))
                    fig_g.add_vline(x=0, line_dash="dash", line_color="gray")
                    cat_arr = m["Region"].tolist()
                    fig_g.update_layout(
                        title=f"Ръст % по {lbl} – {sel_product}" if disp == "pct" else f"Промяна (опак.) по {lbl} – {sel_product}",
                        height=max(get_chart_height(), len(m) * 32), showlegend=False,
                        xaxis=dict(title="", tickfont=dict(size=11), fixedrange=True),
                        yaxis_title="", coloraxis_showscale=False,
                        margin={**get_chart_margins(), "t": 25, "b": 20}, dragmode=False,
                        yaxis=dict(
                            categoryorder="array",
                            categoryarray=cat_arr,
                            tickfont=dict(size=11),
                            fixedrange=True,
                        ),
                    )
                    st.plotly_chart(fig_g, width="stretch", config=config.PLOTLY_CONFIG)
            else:
                st.caption("Няма данни за ръст.")
        else:
            st.caption("Нужни са поне 2 периода за ръст.")
    except Exception:
        st.caption("Няма данни за ръст.")


def render_last_vs_previous_quarter(
    df: pd.DataFrame,
    selected_product: str,
    period_col: str = "Quarter",
    allowed_region_names: Optional[List[str]] = None,
) -> None:
    """Рендира таб Последно vs Предишно: използва logic слой за изчисления, само UI тук."""
    from data_processing import get_sorted_periods
    from logic import compute_last_vs_previous_rankings
    import plotly.graph_objects as go

    if df.empty or not selected_product:
        st.warning("Избери медикамент от филтрите (основен продукт).")
        return
    periods = get_sorted_periods(df, period_col=period_col)
    if len(periods) < 2:
        st.warning("Нужни са поне два периода за сравнение.")
        return

    result = compute_last_vs_previous_rankings(df, selected_product, period_col, tuple(periods))
    if result is None:
        st.warning(f"Няма данни за продукт **{selected_product}**.")
        return

    merged = result["merged"]
    if allowed_region_names and not merged.empty and "Region" in merged.columns:
        allowed_r_set = set(str(r).strip() for r in allowed_region_names)
        merged = merged[merged["Region"].astype(str).str.strip().isin(allowed_r_set)]
    if merged.empty:
        st.warning("Няма данни за избраните региони.")
        return
    last_period = result["last_period"]
    prev_period = result["prev_period"]
    top_region = result["top_region"]
    top_growth = result["top_growth"]

    st.subheader("📊 Последно vs Предишно тримесечие")
    st.caption(f"**Продукт:** {selected_product} | **Периоди:** {last_period} (текущ) vs {prev_period} (предишен)")

    st.markdown("#### 📈 Ръст % по регион")
    if "_growth_display" not in st.session_state:
        st.session_state["_growth_display"] = "pct"

    def _set_growth_mode_lastvp():
        st.session_state["_growth_display"] = st.session_state["growth_radio_lastvp"]

    st.radio(
        "Покажи по",
        options=["pct", "units"],
        format_func=lambda x: "Проценти" if x == "pct" else "Опаковки",
        index=0 if st.session_state.get("_growth_display", "pct") == "pct" else 1,
        key="growth_radio_lastvp",
        horizontal=True,
        on_change=_set_growth_mode_lastvp,
    )
    merged_chart = merged.copy()
    merged_chart["Units_Delta"] = merged_chart["Last_Units"] - merged_chart["Previous_Units"]
    disp = st.session_state.get("_growth_display", "pct")
    if disp == "units":
        merged_chart = merged_chart.sort_values("Units_Delta", ascending=False)
        x_vals = merged_chart["Units_Delta"]
        txts = [f"{u:+,.0f} оп." for u in merged_chart["Units_Delta"]]
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in merged_chart["Units_Delta"]]
    else:
        merged_chart = merged_chart.sort_values("Growth_%", ascending=False)
        x_vals = merged_chart["Growth_%"]
        txts = [f"{g:+.1f}%" for g in merged_chart["Growth_%"]]
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in merged_chart["Growth_%"]]
    hover_tmpl = "<b>%{y}</b><br>Ръст: %{x:+.1f}%<br>Промяна: %{customdata:+,.0f} оп.<extra></extra>" if disp == "pct" else "<b>%{y}</b><br>Промяна: %{x:+,.0f} оп.<extra></extra>"
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_vals,
        y=merged_chart["Region"],
        orientation="h",
        marker_color=colors,
        text=txts,
        textposition="inside",
        textfont=dict(size=9, color=get_chart_text_color()),
        customdata=merged_chart["Units_Delta"] if disp == "pct" else [0] * len(merged_chart),
        hovertemplate=hover_tmpl,
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    fig.update_layout(
        xaxis=dict(title="", tickfont=dict(size=11), fixedrange=True),
        yaxis_title="",
        height=max(get_chart_height(), len(merged_chart) * 32),
        margin={**get_chart_margins(), "t": 20, "b": 30},
        showlegend=False,
        dragmode=False,
        yaxis=dict(
            categoryorder="array",
            categoryarray=merged_chart["Region"].tolist(),
            tickfont=dict(size=11),
            fixedrange=True,
        ),
    )
    st.plotly_chart(fig, width="stretch", config=config.PLOTLY_CONFIG)
