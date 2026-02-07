"""
Инструменти за сравнение на периоди, продукти и региони.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Tuple
import config


def create_period_comparison(
    df: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    period_col: str = "Quarter"
) -> None:
    """
    Създава сравнение между два периода.
    
    Параметри
    ---------
    df : pd.DataFrame
        Данни за сравнение
    products_list : List[str]
        Продукти за показване
    periods : List[str]
        Налични периоди
    period_col : str
        Колона с периоди
    """
    st.subheader("📊 Сравнение на периоди")
    
    if len(periods) < 2:
        st.warning("Нужни са поне 2 периода за сравнение.")
        return
    
    # Избор на периоди за сравнение
    col1, col2 = st.columns(2)
    
    with col1:
        period1 = st.selectbox(
            "Период 1 (базов)",
            periods,
            index=max(0, len(periods) - 5),  # Преди 4 тримесечия
            key="period1_comp"
        )
    
    with col2:
        period2 = st.selectbox(
            "Период 2 (сравнителен)",
            periods,
            index=len(periods) - 1,  # Последен период
            key="period2_comp"
        )
    
    if period1 == period2:
        st.info("Избери различни периоди за сравнение.")
        return
    
    # Филтриране на данни
    df1 = df[df[period_col] == period1]
    df2 = df[df[period_col] == period2]
    
    # Филтриране на продукти
    df1_prod = df1[df1["Drug_Name"].isin(products_list)]
    df2_prod = df2[df2["Drug_Name"].isin(products_list)]
    
    # Агрегиране по продукт
    agg1 = df1_prod.groupby("Drug_Name")["Units"].sum().reset_index()
    agg2 = df2_prod.groupby("Drug_Name")["Units"].sum().reset_index()
    
    # Merge за сравнение
    comparison = agg1.merge(
        agg2,
        on="Drug_Name",
        how="outer",
        suffixes=("_1", "_2")
    ).fillna(0)
    
    # Изчисляване на промяна
    comparison["Change"] = comparison["Units_2"] - comparison["Units_1"]
    comparison["Change_%"] = (
        (comparison["Change"] / comparison["Units_1"].replace(0, 1)) * 100
    )
    
    # Сортиране по Units_2
    comparison = comparison.sort_values("Units_2", ascending=False)
    
    # Графика - grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name=period1,
        x=comparison["Drug_Name"],
        y=comparison["Units_1"],
        marker_color='lightblue',
        text=comparison["Units_1"].apply(lambda x: f"{int(x):,}"),
        textposition='outside',
    ))
    
    fig.add_trace(go.Bar(
        name=period2,
        x=comparison["Drug_Name"],
        y=comparison["Units_2"],
        marker_color='darkblue',
        text=comparison["Units_2"].apply(lambda x: f"{int(x):,}"),
        textposition='outside',
    ))
    
    fig.update_layout(
        title=f"Сравнение: {period1} vs {period2}",
        xaxis_title="Продукт",
        yaxis_title="Опаковки",
        barmode='group',
        height=config.CHART_HEIGHT,
        xaxis_tickangle=-45,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=120, t=80, l=50, r=50),
        font=dict(size=12),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Таблица с промени
    st.subheader("Промени (%)")
    
    # Форматиране на таблицата
    display_df = comparison[["Drug_Name", "Units_1", "Units_2", "Change", "Change_%"]].copy()
    display_df.columns = ["Продукт", period1, period2, "Промяна (опак.)", "Промяна (%)"]
    
    # Форматиране на числата
    display_df[period1] = display_df[period1].apply(lambda x: f"{int(x):,}")
    display_df[period2] = display_df[period2].apply(lambda x: f"{int(x):,}")
    display_df["Промяна (опак.)"] = display_df["Промяна (опак.)"].apply(
        lambda x: f"+{int(x):,}" if x > 0 else f"{int(x):,}"
    )
    display_df["Промяна (%)"] = display_df["Промяна (%)"].apply(
        lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%"
    )
    
    # Стилизиране на таблицата
    st.dataframe(
        display_df,
        use_container_width=True,
        height=min(400, len(display_df) * 35 + 50)
    )


def create_regional_comparison(
    df: pd.DataFrame,
    products_list: List[str],
    period: str,
    period_col: str = "Quarter"
) -> None:
    """
    Създава сравнение между региони за избран период.
    
    Параметри
    ---------
    df : pd.DataFrame
        Данни за сравнение
    products_list : List[str]
        Продукти за показване
    period : str
        Период за сравнение
    period_col : str
        Колона с периоди
    """
    st.subheader(f"🗺️ Сравнение на региони - {period}")
    
    # Филтриране по период
    df_period = df[df[period_col] == period]
    
    # Филтриране на продукти
    df_prod = df_period[df_period["Drug_Name"].isin(products_list)]
    
    # Агрегиране по регион и продукт
    agg = df_prod.groupby(["Region", "Drug_Name"])["Units"].sum().reset_index()
    
    if agg.empty:
        st.info("Няма данни за сравнение.")
        return
    
    # Pivot за по-лесно сравнение
    pivot = agg.pivot(index="Region", columns="Drug_Name", values="Units").fillna(0)
    
    # Сортиране по общ обем
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False).drop(columns=["Total"])
    
    # Stacked bar chart
    fig = go.Figure()
    
    for product in products_list:
        if product in pivot.columns:
            fig.add_trace(go.Bar(
                name=product,
                x=pivot.index,
                y=pivot[product],
                text=pivot[product].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                textposition='inside',
            ))
    
    fig.update_layout(
        title=f"Регионално разпределение - {period}",
        xaxis_title="Регион",
        yaxis_title="Опаковки",
        barmode='stack',
        height=config.CHART_HEIGHT,
        xaxis_tickangle=-45,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        margin=dict(b=120, t=80, l=50, r=50),
        font=dict(size=12),
    )
    
    st.plotly_chart(fig, use_container_width=True)
