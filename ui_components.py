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


def create_filters(df: pd.DataFrame) -> dict:
    """
    Създава sidebar филтри за избор на регион, медикамент, молекула, brick.
    
    Параметри
    ---------
    df : pd.DataFrame
        Данни за филтриране
    
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
        help="Географска област (София, Пловдив, Варна...) - избери \"Всички\" за национален преглед"
    )
    
    # 2. Медикамент (основен продукт)
    sel_product = st.sidebar.selectbox(
        "2. Медикамент (основен)",
        drugs,
        index=0,
        help="Твоят продукт за анализ – напр. Lipocante, Valsavil, Aerius"
    )
    
    # 3. Молекула - по подразбиране само молекулата на избрания продукт
    prod_df = df[df["Drug_Name"] == sel_product]
    prod_mol = prod_df["Molecule"].iloc[0] if len(prod_df) > 0 else None
    default_mol = [prod_mol] if prod_mol and prod_mol in molecules else molecules
    
    sel_molecules = st.sidebar.multiselect(
        "3. Молекула",
        molecules,
        default=default_mol,
        help="Активното вещество (напр. Pitavastatin, Valsartan) - по подразбиране само молекулата на избрания продукт"
    )
    
    # 4. Brick (район)
    sel_district = st.sidebar.selectbox(
        "4. Brick (район)",
        districts,
        index=0,
        help="Малък географски район в града (Лозенец, Дружба, Самоков...) - налично само ако имаш \"Total Bricks\" данни"
    ) if has_district else "Всички"
    
    # 5. Конкуренти - само от същата категория (Source)
    prod_sources = df[df["Drug_Name"] == sel_product]["Source"].unique()
    same_source_drugs = df[df["Source"].isin(prod_sources)]["Drug_Name"].unique()
    competitor_options = sorted([d for d in same_source_drugs if d != sel_product])
    
    competitor_products = st.sidebar.multiselect(
        "Добави конкурент на графиката",
        competitor_options if competitor_options else [d for d in drugs if d != sel_product],
        default=[],
        help="Конкуренти от същата категория (напр. статини, антихистамини)"
    )
    
    return {
        "region": sel_region,
        "product": sel_product,
        "molecules": sel_molecules,
        "district": sel_district,
        "competitors": competitor_products,
        "product_molecule": prod_mol,
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
    Създава селектор за метрика (Units, Market Share, Growth).
    
    Връща
    ------
    Tuple[str, bool]
        (избрана_метрика, share_in_molecule)
    """
    st.sidebar.header("Метрика")
    metric = st.sidebar.radio(
        "Покажи",
        config.METRICS,
        index=0,
        help="Избери каква метрика да виждаш в графиките"
    )
    
    share_in_molecule = False
    if metric == "Market Share (%)":
        scope_choice = st.sidebar.radio(
            "Дял спрямо",
            ["Цял клас (всички в категорията)", "Само молекулата (напр. само Pitavastatin)"],
            index=1,  # По подразбиране в молекулата
            help="Изчислявай дял спрямо целия пазар или само спрямо избраната молекула"
        )
        share_in_molecule = "Само молекулата" in scope_choice
    
    # Глосар на термините
    with st.sidebar.expander("ℹ️ Какво означава..."):
        st.markdown("""
        **Region** - Голяма географска област (София, Пловдив, Варна...)
        
        **Brick** - Малък район в града (Лозенец, Дружба, Самоков...)
        
        **Molecule** - Активното вещество в медикамента (напр. Pitavastatin, Valsartan)
        
        **Market Share** - Твоят дял от пазара в процент (%)
        
        **Units** - Брой продадени опаковки
        
        **% Ръст** - Промяна спрямо предишен период (позитивно = ръст, негативно = спад)
        """)
    
    return metric, share_in_molecule


def calculate_metric_data(
    df: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    metric: str,
    period_col: str = "Quarter",
    share_in_molecule: bool = False,
    molecule: Optional[str] = None,
) -> pd.DataFrame:
    """
    Изчислява избраната метрика за продуктите.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни
    products_list : List[str]
        Списък от продукти за показване (основен + конкуренти)
    periods : List[str]
        Сортирани периоди
    metric : str
        Метрика за изчисляване
    period_col : str
        Име на колоната с периоди
    share_in_molecule : bool
        Дали дял да се изчислява само спрямо молекулата
    molecule : str
        Молекула за share calculation
    
    Връща
    ------
    pd.DataFrame
        DataFrame с изчислената метрика
    """
    # Филтриране само на избраните продукти
    df_chart = df[df["Drug_Name"].isin(products_list)].copy()
    
    # Агрегиране по период и продукт
    df_agg_base = df_chart.groupby([period_col, "Drug_Name"], as_index=False)["Units"].sum()
    
    if metric == "Units (опак.)":
        df_agg = df_agg_base
        y_col = "Units"
        y_label = "Опаковки"
        
    elif metric == "Market Share (%)":
        # Market Share = (Units_продукт / Units_всички) * 100
        if share_in_molecule and molecule:
            # Дял само спрямо молекулата
            df_denom = df[df["Molecule"] == molecule]
        else:
            # Дял спрямо целия пазар
            df_denom = df
        
        total_by_period = df_denom.groupby(period_col)["Units"].sum()
        df_agg = df_agg_base.copy()
        
        def calc_share(row):
            total = total_by_period.get(row[period_col], 0)
            return 100 * row["Units"] / total if total > 0 else 0
        
        df_agg["Share"] = df_agg.apply(calc_share, axis=1)
        y_col = "Share"
        y_label = f"Дял (%) – {'само ' + molecule if share_in_molecule and molecule else 'цял пазар'}"
        
    else:  # % Ръст
        # Growth = (Units_период / Units_предишен_период - 1) * 100
        pivot = df_agg_base.pivot(index="Drug_Name", columns=period_col, values="Units")
        pivot = pivot.reindex(columns=periods)
        growth = pivot.pct_change(axis=1) * 100
        df_agg = growth.reset_index().melt(id_vars="Drug_Name", var_name=period_col, value_name="Growth_%")
        df_agg = df_agg.dropna(subset=["Growth_%"])
        y_col = "Growth_%"
        y_label = "% Ръст"
    
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
) -> None:
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
    
    # Създаване на линейна графика
    fig = px.line(
        df_agg,
        x=period_col,
        y=y_col,
        color="Drug_Name",
        markers=True,
        title=title,
    )
    
    # Настройка на графиката
    fig.update_traces(
        mode="lines+markers",
        line=dict(width=3),
        hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>%{y:,.1f}<extra></extra>",
    )
    
    fig.update_layout(
        height=config.CHART_HEIGHT,
        legend_title="Продукт",
        hovermode="x unified",
        xaxis_tickangle=-45,
        xaxis={"categoryorder": "array", "categoryarray": periods},
        # Мобилна оптимизация
        legend=dict(
            orientation="h",  # Хоризонтална легенда за мобилни
            yanchor="bottom",
            y=-0.3,  # Под графиката
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=120, t=80, l=50, r=50),  # Повече място за легендата
        font=dict(size=12),  # По-големи шрифтове за мобилни
    )
    
    st.plotly_chart(fig, use_container_width=True)


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
        ["Региони (Sofia East, Varna, Burgas...)", "Brick-ове в регион (Samokov, Druzhba, Lozenets...)"],
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
        height=config.CHART_HEIGHT,
        xaxis_tickangle=-45,
        xaxis_title="",  # Премахва етикета на оста
        yaxis_title="Опаковки",
        # Мобилна оптимизация
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=100, t=80, l=50, r=50),
        font=dict(size=12),
    )
    st.plotly_chart(fig_geo, use_container_width=True)
    
    # Stacked bar chart за дял
    total_by_x = df_geo.groupby(group_col)["Units"].sum()
    
    def calc_geo_share(row):
        total = total_by_x.get(row[group_col], 0)
        return 100 * row["Units"] / total if total > 0 else 0
    
    df_geo_agg["Share"] = df_geo_agg.apply(calc_geo_share, axis=1)
    
    fig_share = px.bar(
        df_geo_agg,
        x=group_col,
        y="Share",
        color="Drug_Name",
        barmode="stack",
        title=f"Дял (%) по {x_label}",
    )
    
    # Почистен hover template
    fig_share.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}<br>%{y:.1f}%<extra></extra>"
    )
    
    fig_share.update_layout(
        height=config.BRICK_CHART_HEIGHT,
        xaxis_tickangle=-45,
        xaxis_title="",
        yaxis_title="Дял (%)",
        # Мобилна оптимизация
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=100, t=80, l=50, r=50),
        font=dict(size=12),
    )
    st.plotly_chart(fig_share, use_container_width=True)
