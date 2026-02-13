"""
Инструменти за сравнение на периоди, продукти и региони.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from typing import List, Tuple, Optional
import config


def create_period_comparison(
    df: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    period_col: str = "Quarter",
    level_label: str = None,
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
    level_label : str, optional
        "Национално ниво" или "Регионално: [Име на регион]"
    """
    st.subheader("📊 Сравнение на периоди")
    if level_label:
        st.caption(f"📍 **Ниво:** {level_label}")
    
    if len(periods) < 2:
        st.warning("Нужни са поне 2 периода за сравнение.")
        return
    
    # Избор на периоди за сравнение (Mobile-first: вертикално)
    period1 = st.selectbox(
        "Период 1 (базов)",
        periods,
        index=max(0, len(periods) - 5),  # Преди 4 тримесечия
        key="period1_comp",
        help="Избери стар период като база за сравнение"
    )
    
    period2 = st.selectbox(
        "Период 2 (сравнителен)",
        periods,
        index=len(periods) - 1,  # Последен период
        key="period2_comp",
        help="Избери нов период за да видиш промяната"
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
    
    # Графика - grouped bar chart с % промяна
    fig = go.Figure()
    
    # Период 1
    fig.add_trace(go.Bar(
        name=period1,
        x=comparison["Drug_Name"],
        y=comparison["Units_1"],
        marker_color='lightblue',
        text=comparison["Units_1"].apply(lambda x: f"{int(x):,}"),
        textposition='outside',
        hovertemplate="<b>%{x}</b><br>" + period1 + ": %{y:,.0f} опак.<extra></extra>",
    ))
    
    # Период 2 с % промяна (закръглена до 2 знака с индикатори)
    def format_bar_text(row):
        change = row['Change_%']
        if change > 0:
            return f"{int(row['Units_2']):,}<br>(🟢 +{change:.2f}%)"
        elif change < 0:
            return f"{int(row['Units_2']):,}<br>(🔴 {change:.2f}%)"
        else:
            return f"{int(row['Units_2']):,}<br>({change:.2f}%)"
    
    comparison["text_with_change"] = comparison.apply(format_bar_text, axis=1)
    
    fig.add_trace(go.Bar(
        name=period2,
        x=comparison["Drug_Name"],
        y=comparison["Units_2"],
        marker_color='darkblue',
        text=comparison["text_with_change"],
        textposition='outside',
        hovertemplate=(
            "<b>%{x}</b><br>" + 
            period2 + ": %{y:,.0f} опак.<br>" +
            "Промяна: %{customdata:+.1f}%<extra></extra>"
        ),
        customdata=comparison["Change_%"],
    ))
    
    fig.update_layout(
        title=f"Сравнение: {period1} vs {period2}",
        legend_title="",
        xaxis=dict(
            title="Продукт",
            tickangle=-45,
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
        barmode='group',
        height=config.MOBILE_CHART_HEIGHT,  # Mobile-first: 500px
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.5,  # Още по-долу за mobile
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(size=12),
        hovermode="closest",
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
    )
    
    st.plotly_chart(fig, width="stretch", config=config.PLOTLY_CONFIG)
    
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
    # Промяна (%) с индикатори
    def format_percent_with_icon(x):
        if x > 0:
            return f"🟢 +{x:.2f}%"
        elif x < 0:
            return f"🔴 {x:.2f}%"
        else:
            return f"{x:.2f}%"
    
    display_df["Промяна (%)"] = display_df["Промяна (%)"].apply(format_percent_with_icon)
    
    # Стилизиране на таблицата с оцветени проценти
    def color_change(val):
        """Оцвети процентите - зелено за +, червено за -"""
        if isinstance(val, str) and "%" in val:
            if "🟢" in val or val.startswith("+"):
                return 'color: green; font-weight: bold'
            elif "🔴" in val or val.startswith("-"):
                return 'color: red; font-weight: bold'
        return ''
    
    styled_df = display_df.style.applymap(color_change, subset=["Промяна (%)"])
    
    st.dataframe(
        styled_df,
        width="stretch",
        height=min(400, len(display_df) * 35 + 50)
    )


def create_regional_comparison(
    df: pd.DataFrame,
    products_list: List[str],
    period: str,
    period_col: str = "Quarter",
    level_label: str = None,
    periods_fallback: List[str] = None,
    allowed_region_names: Optional[List[str]] = None,
) -> None:
    """
    Създава сравнение между региони – по опаковки или по ръст % (лесно превключване).
    """
    st.subheader(f"🗺️ Сравнение на региони - {period}")
    if level_label:
        st.caption(f"📍 **Ниво:** {level_label}")

    # Филтриране по период – fallback
    df_period = df[df[period_col] == period]
    df_prod = df_period[df_period["Drug_Name"].isin(products_list)] if not df_period.empty else pd.DataFrame()
    if (df_period.empty or df_prod.empty) and periods_fallback:
        for p in reversed(periods_fallback[:-1]):
            if p == period:
                continue
            df_period = df[df[period_col] == p]
            df_prod = df_period[df_period["Drug_Name"].isin(products_list)] if not df_period.empty else pd.DataFrame()
            if not df_prod.empty:
                period = p
                st.caption(f"*(Данни за {period})*")
                break

    agg = df_prod.groupby(["Region", "Drug_Name"])["Units"].sum().reset_index() if not df_prod.empty else pd.DataFrame()

    if agg.empty:
        st.info("Няма данни за сравнение.")
        return

    pivot = agg.pivot(index="Region", columns="Drug_Name", values="Units").fillna(0)
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("Total", ascending=False).drop(columns=["Total"])
    if allowed_region_names:
        allowed_r = set(str(r).strip() for r in allowed_region_names)
        pivot = pivot[pivot.index.astype(str).str.strip().isin(allowed_r)]
    if pivot.empty:
        st.info("Няма данни за избраните региони.")
        return

    # 1. Графика за опаковки
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
        legend_title="",
        xaxis=dict(title="Регион", tickangle=-45, title_font=dict(size=14), tickfont=dict(size=14), autorange=True),
        yaxis=dict(title="Опаковки", title_font=dict(size=14), tickfont=dict(size=14), autorange=True),
        barmode='stack',
        height=config.MOBILE_CHART_HEIGHT,
        legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
        hovermode='closest', dragmode=False, margin=dict(l=0, r=0, t=30, b=0), font=dict(size=12),
    )
    st.plotly_chart(fig, width="stretch", config=config.PLOTLY_CONFIG)

    # 2. Графика за ръст % под опаковките (като в секция Опаковки по Brick)
    st.markdown("#### 📈 Ръст % спрямо предишно тримесечие")
    prev_period = None
    if periods_fallback and period in periods_fallback:
        idx = periods_fallback.index(period)
        if idx > 0:
            prev_period = periods_fallback[idx - 1]
    if prev_period and not df[df[period_col] == prev_period].empty:
        agg_prev = df[df[period_col] == prev_period]
        agg_prev = agg_prev[agg_prev["Drug_Name"].isin(products_list)].groupby(["Region", "Drug_Name"])["Units"].sum().reset_index()
        pivot_prev = agg_prev.pivot(index="Region", columns="Drug_Name", values="Units").fillna(0)
        pivot_growth = pivot.copy()
        for col in pivot_growth.columns:
            if col in pivot_prev.columns:
                prev_vals = pivot_prev[col].reindex(pivot.index).fillna(0)
                curr_vals = pivot[col]
                pivot_growth[col] = np.where(prev_vals > 0, ((curr_vals - prev_vals) / prev_vals * 100), np.where(curr_vals > 0, 100.0, 0.0))
            else:
                pivot_growth[col] = 0
        pivot_growth["_tot"] = pivot_growth[[c for c in pivot_growth.columns if c in products_list]].sum(axis=1)
        pivot_growth = pivot_growth.sort_values("_tot", ascending=False).drop(columns=["_tot"])
        pivot_prev_reidx = pivot_prev.reindex(pivot.index).fillna(0)
        fig2 = go.Figure()
        for product in products_list:
            if product in pivot_growth.columns:
                pct = pivot_growth[product]
                delta_vals = (pivot[product] - pivot_prev_reidx[product]).reindex(pivot_growth.index).fillna(0) if product in pivot.columns else pd.Series(0.0, index=pivot_growth.index)
                txt = [f"{p:+.1f}% ({d:+,.0f} оп.)" for p, d in zip(pct, delta_vals)]
                fig2.add_trace(go.Bar(
                    name=product,
                    x=pivot_growth.index,
                    y=pivot_growth[product],
                    text=txt,
                    textposition='outside',
                ))
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        n_reg = len(pivot_growth)
        fig2.update_layout(
            title=f"Ръст % по регион – {period} vs {prev_period}",
            yaxis_title="Ръст (%)",
            barmode='group',
            height=max(500, n_reg * 38),
            legend_title="",
            xaxis=dict(title="Регион", tickangle=-45, tickfont=dict(size=14)),
            yaxis=dict(tickfont=dict(size=13)),
            legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
            margin=dict(l=80, r=80, t=40, b=80),
            font=dict(size=12),
        )
        st.plotly_chart(fig2, width="stretch", config=config.PLOTLY_CONFIG)
    else:
        st.caption("Няма данни за предишния период за ръст.")
