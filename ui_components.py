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


def create_filters(df: pd.DataFrame, default_product: str = None) -> dict:
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
    st.sidebar.header("Филтри")
    
    # Списъци от уникални стойности
    regions = ["Всички"] + sorted(df["Region"].unique())
    drugs = sorted(df["Drug_Name"].unique())
    molecules = sorted(df["Molecule"].unique())
    has_district = "District" in df.columns
    districts = ["Всички"] + sorted(df["District"].unique()) if has_district else []
    
    # 1. Регион
    sel_region = st.sidebar.selectbox(
        "1. Регион",
        regions,
        index=0,
        help="Географска област (Пловдив, Варна, Бургас...) - избери \"Всички\" за национален преглед"
    )
    
    # 2. Медикамент (основен продукт) - с поддръжка за Quick Search default
    product_index = 0
    if default_product and default_product in drugs:
        try:
            product_index = drugs.index(default_product)
        except ValueError:
            product_index = 0
    
    sel_product = st.sidebar.selectbox(
        "2. Медикамент (основен)",
        drugs,
        index=product_index,
        help="Твоят продукт за анализ (автоматично избран от Quick Search)"
    )
    
    # 3. Brick (район)
    sel_district = st.sidebar.selectbox(
        "3. Brick (район)",
        districts,
        index=0,
        help="Малък географски район - налично само ако имаш \"Total Bricks\" данни"
    ) if has_district else "Всички"
    
    # 4. Конкуренти - включваме и категориите (класовете)
    prod_sources = df[df["Drug_Name"] == sel_product]["Source"].unique()
    
    # Вземаме ВСИЧКИ Drug_Name от същата Source (категория)
    same_source_drugs = df[df["Source"].isin(prod_sources)]["Drug_Name"].unique()
    
    # Разделяме ATC класове от медикаменти
    # ATC класовете имат формат: Буква+цифри (напр. R06A0, B01C2, C09D3)
    categories = []
    competitor_drugs = []
    
    for item in same_source_drugs:
        if item == sel_product:
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
    
    # Ако няма нищо, показваме всички медикаменти
    if not competitor_options:
        competitor_options = [d for d in drugs if d != sel_product]
    
    # Бутон за автоматично добавяне на Top 3
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.markdown("**Добави конкуренти**")
    with col2:
        add_top3 = st.button("Top 3", help="Добави 3-те най-продавани", key="top3_btn")
    
    # Ако е натиснат бутона Top 3, избираме автоматично
    default_competitors = []
    if add_top3:
        # Вземаме Top 3 (без класове)
        top3_options = [opt for opt in competitor_options if not opt.startswith("📊 КЛАС:")][:3]
        default_competitors = top3_options
    
    # Multiselect за конкуренти
    help_text = "📊 Класове (общи продажби) | Медикаменти сортирани по продажби (най-много → най-малко)"
    
    competitor_products = st.sidebar.multiselect(
        "Избери конкуренти",
        competitor_options,
        default=default_competitors,
        help=help_text,
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
        "product": sel_product,
        "district": sel_district,
        "competitors": processed_competitors,  # Вече включва и класовете
        "product_source": prod_sources[0] if prod_sources.size > 0 else None,
        "has_district": has_district,
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
    pct_change = pivot_units.pct_change(axis=1) * 100
    df_pct = pct_change.reset_index().melt(
        id_vars="Drug_Name",
        var_name=period_col,
        value_name="Growth_%"
    )
    df_agg = df_agg.merge(df_pct, on=["Drug_Name", period_col], how="left")
    
    # 3. Market Share % (спрямо целия клас/категория)
    # ВАЖНО: Изключваме ATC класовете от изчислението на total, за да избегнем дублиране
    # Класовете са сума на медикаментите, не трябва да се броят отделно
    
    def is_atc_class(drug_name):
        """Проверява дали е ATC клас (напр. C10A1 STATINS)"""
        if pd.isna(drug_name):
            return False
        parts = str(drug_name).split()
        if not parts:
            return False
        first_word = parts[0]
        # ATC код формат: 4-7 символа, започва с буква, има цифра, главни букви, има описание
        return (
            len(first_word) >= 4 and
            len(first_word) <= 7 and
            first_word[0].isalpha() and
            any(c.isdigit() for c in first_word) and
            first_word.isupper() and
            len(parts) >= 2 and
            drug_name not in ["GRAND TOTAL", "Grand Total"] and
            not drug_name.startswith("Region")
        )
    
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
        height=config.MOBILE_CHART_HEIGHT,
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
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
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
    
    st.plotly_chart(fig, use_container_width=True, config=config.PLOTLY_CONFIG)
    
    # Връщаме и df_agg за да можем да покажем Market Share данни извън функцията
    return df_agg


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
    
    # Функция за проверка на ATC класове
    def is_atc_class(drug_name):
        if pd.isna(drug_name):
            return False
        parts = str(drug_name).split()
        if not parts:
            return False
        first_word = parts[0]
        return (
            len(first_word) >= 4 and
            len(first_word) <= 7 and
            first_word[0].isalpha() and
            any(c.isdigit() for c in first_word) and
            first_word.isupper() and
            len(parts) >= 2 and
            drug_name not in ["GRAND TOTAL", "Grand Total"] and
            not drug_name.startswith("Region")
        )
    
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
) -> None:
    """
    Показва stacked bar chart с Market Share по всички тримесечия.
    
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
    """
    import plotly.graph_objects as go
    
    if "Market_Share_%" not in df_agg.columns:
        return
    
    # Различни заглавия в зависимост от типа
    if is_national:
        st.subheader("📊 Национален Market Share")
    else:
        st.subheader("📍 Регионален Market Share")
    
    # Филтрираме само медикаменти (без класове които са 100%)
    df_drugs = df_agg[df_agg["Market_Share_%"] < 100].copy()
    
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
    
    # Horizontal stacked bar chart – по-четливо на мобилни
    fig = go.Figure()
    for i, drug in enumerate(pivot.columns):
        fig.add_trace(go.Bar(
            x=pivot[drug],
            y=pivot.index,
            name=drug,
            orientation='h',
            marker_color=colors[i % len(colors)],
            text=pivot[drug].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x >= 2 else ""),
            textposition='inside',
            textfont=dict(color='white', size=11, family='Arial Black'),
            insidetextanchor='middle',
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '<b>%{y}</b><br>' +
                         'Market Share: <b>%{x:.2f}%</b><extra></extra>'
        ))
    
    # Layout – mobile-optimized: horizontal bars, фиксирана височина, минимални margins
    fig.update_layout(
        barmode='stack',
        xaxis_title='Market Share (%)',
        xaxis=dict(
            range=[0, 100],
            title_font=dict(size=14),
            tickfont=dict(size=12),
            autorange=False,
        ),
        yaxis_title=period_col,
        yaxis=dict(
            categoryorder='array',
            categoryarray=sorted_periods,
            title_font=dict(size=14),
            tickfont=dict(size=12),
            autorange='reversed',  # Q1 най-горе
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.35,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        hovermode='y unified',
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#333",
            font=dict(size=14, family="Arial", color="#1a1a1a"),
        ),
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
        height=config.MARKET_SHARE_CHART_HEIGHT_MOBILE,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    
    chart_key = f"market_share_{key_suffix}"
    dismiss_key = f"ms_dismissed_{key_suffix}"
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        config=config.PLOTLY_CONFIG,
        key=chart_key,
        on_select="rerun",
        selection_mode="points",
    )
    
    # Панел с информация при натискане на стълб – скрива се при натискане на бутона
    if event and event.selection and event.selection.points:
        pts = event.selection.points
        sel_key = str([(p.get("curve_number", 0), p.get("point_index", 0)) for p in pts])
        if st.session_state.get(dismiss_key) != sel_key:
            items = []
            for p in pts:
                cnum = p.get("curve_number", 0)
                share = p.get("x", 0)  # при orientation='h': x=value
                period = p.get("y", "—")  # при orientation='h': y=category
                drug = pivot.columns[cnum] if cnum < len(pivot.columns) else "—"
                items.append(f"**{drug}** – {period}: **{share:.1f}%**")
            with st.container():
                st.markdown("---")
                st.markdown("### 📋 Избрана информация")
                for it in items:
                    st.markdown(f"- {it}")
                if st.button("✕ Затвори", key=f"ms_close_{key_suffix}"):
                    st.session_state[dismiss_key] = sel_key
                    st.rerun()
    
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
    period_col: str = "Quarter"
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
    
    if not has_district:
        st.info('Избери лист "Total Bricks" за разбивка по региони и Brick-ове.')
        return
    
    st.subheader("Продажби по региони и Brick-ове")
    
    # Селектор за период
    geo_period = st.selectbox(
        "Период (за опаковките)",
        ["Всички периоди (сума)", "Последно тримесечие"] + periods,
        key="geo_period",
    )
    
    # Филтриране по период
    if geo_period == "Всички периоди (сума)":
        df_geo_base = df.copy()
    elif geo_period == "Последно тримесечие":
        df_geo_base = df[df[period_col] == periods[-1]].copy()
    else:
        df_geo_base = df[df[period_col] == geo_period].copy()
    
    # Ниво на агрегация: Региони vs Brick-ове
    # Вертикално за мобилна четливост
    level = st.radio(
        "Покажи по",
        ["Региони (Пловдив, Варна, Бургас...)", "Brick-ове в регион (Самоков, Банско, Пазарджик...)"],
        key="brick_level",
    )
    by_region = "Региони" in level
    
    # Подготовка на данни
    if by_region:
        df_geo = df_geo_base.copy()
        group_col = "Region"
    else:
        sel_region_brick = st.selectbox(
            "Избери регион",
            sorted(df["Region"].unique()),
            key="sel_region_brick",
        )
        df_geo = df_geo_base[df_geo_base["Region"] == sel_region_brick].copy()
        group_col = "District"
    
    # Филтриране на продукти и агрегация
    df_geo_chart = df_geo[df_geo["Drug_Name"].isin(products_list)]
    df_geo_agg = df_geo_chart.groupby([group_col, "Drug_Name"], as_index=False)["Units"].sum()
    df_geo_agg = df_geo_agg.sort_values("Units", ascending=False)
    
    if df_geo_agg.empty:
        st.info("Няма данни.")
        return
    
    # Bar chart за опаковки
    x_label = "Регион" if by_region else "Brick"
    comp_text = f" vs {', '.join(competitors[:2])}" + ("…" if len(competitors) > 2 else "") if competitors else ""
    
    fig_geo = px.bar(
        df_geo_agg,
        x=group_col,
        y="Units",
        color="Drug_Name",
        barmode="group",
        title=f"Опаковки по {x_label} – {sel_product}{comp_text}",
    )
    
    # Почистен hover template - само име и стойност
    fig_geo.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>%{y:,.0f} опак.<extra></extra>"
    )
    
    fig_geo.update_layout(
        height=config.MOBILE_CHART_HEIGHT,  # Mobile-first: 500px
        legend_title="",
        xaxis_tickangle=-45,
        xaxis=dict(
            title="",
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
        ),
        yaxis=dict(
            title="Опаковки",
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.5,
            xanchor="center",
            x=0.5
        ),
        hovermode='closest',
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(size=12),
    )
    st.plotly_chart(fig_geo, use_container_width=True, config=config.PLOTLY_CONFIG)
