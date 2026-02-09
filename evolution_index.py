"""
Еволюционен Индекс (EI) – анализ на растеж на продукт vs терапевтичен клас.

EI = ((100 + Product_Growth) / (100 + Class_Growth)) * 100
EI > 100 означава, че продуктът расте по-бързо от пазарния сегмент.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Tuple, List, Dict, Any
import config


def _is_atc_class(drug_name) -> bool:
    """Проверява дали е ATC клас (напр. C10A1 STATINS)."""
    if pd.isna(drug_name):
        return False
    parts = str(drug_name).split()
    if not parts:
        return False
    first_word = parts[0]
    return (
        len(first_word) >= 4 and len(first_word) <= 7
        and first_word[0].isalpha()
        and any(c.isdigit() for c in first_word)
        and first_word.isupper()
        and len(parts) >= 2
        and drug_name not in ["GRAND TOTAL", "Grand Total"]
        and not str(drug_name).startswith("Region")
    )


def _get_location_label(filters: dict) -> str:
    """Формира етикет за локация от филтрите."""
    if not filters:
        return "Всички региони"
    region = filters.get("region", "Всички")
    district = filters.get("district", "Всички")
    has_district = filters.get("has_district", False)
    if region == "Всички" and (not has_district or district == "Всички"):
        return "Всички региони"
    parts = []
    if region != "Всички":
        parts.append(f"Регион: {region}")
    if has_district and district != "Всички":
        parts.append(f"Брик: {district}")
    return " | ".join(parts) if parts else "Всички региони"


def render_evolution_index_tab(
    df_filtered: pd.DataFrame,
    df_national: pd.DataFrame,
    periods: list,
    filters: dict,
    period_col: str = "Quarter",
) -> None:
    """
    Рендерира таба 'Еволюционен Индекс'.
    
    Параметри
    ---------
    df_filtered : pd.DataFrame
        Данни филтрирани по Region/Brick от sidebar
    df_national : pd.DataFrame
        Пълни национални данни (всички региони)
    periods : list
        Сортирани периоди
    filters : dict
        Текущи филтри от sidebar (region, district, has_district)
    period_col : str
        Име на колоната с периоди
    """
    st.subheader("📊 Еволюционен Индекс")
    
    # Location selector: National или Region/Brick от sidebar
    location_mode = st.radio(
        "Регион/Брик",
        options=["national", "sidebar"],
        format_func=lambda x: "Всички региони (национално)" if x == "national" else "Регион/Брик от sidebar",
        horizontal=True,
        key="ei_location",
    )
    
    df = df_national if location_mode == "national" else df_filtered
    location_label = "Всички региони" if location_mode == "national" else _get_location_label(filters)
    
    drugs_for_select = sorted(
        df[~df["Drug_Name"].apply(_is_atc_class)]["Drug_Name"].unique()
    )
    
    if not drugs_for_select:
        st.warning("Няма налични медикаменти за анализ.")
        return
    
    if not periods:
        st.warning("Няма налични периоди за анализ.")
        return
    
    # По подразбиране: медикаментът от търсачката (филтрите), ако е в списъка
    selected_product = filters.get("product") or ""
    default_drugs = [selected_product] if selected_product in drugs_for_select else ([drugs_for_select[0]] if drugs_for_select else [])
    
    # Multi-select за портфолио
    sel_drugs = st.multiselect(
        "Избери медикаменти (портфолио)",
        drugs_for_select,
        default=default_drugs,
        key="ei_drugs",
    )
    
    col1, col2 = st.columns(2)
    with col1:
        ref_idx = len(periods) - 1
        ref_period = st.selectbox("Референтен период", periods, index=ref_idx, key="ei_ref")
    with col2:
        base_idx = len(periods) - 2 if len(periods) >= 2 else 0
        base_period = st.selectbox("Базов период", periods, index=base_idx, key="ei_base")
    
    if ref_period == base_period:
        st.warning("Референтният и базовият период трябва да са различни.")
        return
    
    if not sel_drugs:
        st.info("Избери поне един медикамент.")
        return

    from logic import compute_ei_rows_and_overall, compute_region_ei_benchmark

    rows, overall_ei = compute_ei_rows_and_overall(
        df, tuple(sel_drugs), ref_period, base_period, period_col
    )
    total_sales_ref = sum(r["sales_ref"] for r in rows)

    # Голяма метрика – Общ Еволюционен Индекс, контекстуален за локация
    drugs_display = ", ".join(sel_drugs) if len(sel_drugs) <= 3 else f"{len(sel_drugs)} медикамента"
    st.markdown("---")
    st.markdown(f"### Еволюционен Индекс за **{drugs_display}** в **{location_label}**")
    if overall_ei is not None:
        st.metric(label=f"{ref_period} vs {base_period}", value=f"{overall_ei:.1f}", delta=None)
    else:
        st.metric(label=f"{ref_period} vs {base_period}", value="—", delta=None)
    st.caption(
        "EI > 100 означава, че продуктът расте по-бързо от пазарния сегмент. "
        f"Претеглено по продажби в {location_label} (референтен период)."
    )
    
    # Regional Benchmark Chart – EI по регион
    region_ei_data = compute_region_ei_benchmark(
        df_national, tuple(sel_drugs), ref_period, base_period, period_col
    )
    labels = [r[0] for r in region_ei_data]
    values = [r[1] for r in region_ei_data]

    if region_ei_data:
        st.markdown("---")
        st.markdown("### 📊 EI по регион (бенчмарк)")
        
        fig = _build_ei_region_figure(tuple(labels), tuple(values))
        st.plotly_chart(fig, use_container_width=True, config=config.PLOTLY_CONFIG)
        st.caption("Графиката показва сравнително представяне на избраното портфолио по региони за избраните периоди.")

    # Таблица: Резултати по медикамент
    st.markdown("---")
    st.markdown("**Резултати по медикамент**")
    table_data = []
    for r in rows:
        table_data.append({
            "Медикамент": r["drug"],
            "Продажби (Ref)": f"{int(r['sales_ref']):,}",
            "Продажби (Base)": f"{int(r['sales_base']):,}",
            "Ръст %": f"{r['growth_pct']:+.1f}%" if r["growth_pct"] is not None else "—",
            "Ръст клас %": f"{r['class_growth_pct']:+.1f}%" if r["class_growth_pct"] is not None else "—",
            "EI": f"{r['ei']:.1f}" if r["ei"] is not None else "—",
        })
    df_table = pd.DataFrame(table_data)
    total_sales_base = sum(r["sales_base"] for r in rows)
    total_growth = ((total_sales_ref - total_sales_base) / total_sales_base * 100) if total_sales_base > 0 else 0
    total_row = {
        "Медикамент": "**TOTAL**",
        "Продажби (Ref)": f"{int(total_sales_ref):,}",
        "Продажби (Base)": f"{int(total_sales_base):,}",
        "Ръст %": f"{total_growth:+.1f}%",
        "Ръст клас %": "—",
        "EI": f"{overall_ei:.1f}" if overall_ei is not None else "—",
    }
    df_table = pd.concat([df_table, pd.DataFrame([total_row])], ignore_index=True)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


@st.cache_resource(show_spinner=False)
def _build_ei_region_figure(labels: Tuple[str, ...], values: Tuple[float, ...]) -> go.Figure:
    """Създава Plotly фигура за EI по регион (скъпа за рендер)."""
    colors = ["#2ecc71" if v >= 100 else "#e74c3c" for v in values]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition='outside',
        textfont=dict(size=11),
    ))
    fig.add_vline(x=100, line_dash="dash", line_color="red", line_width=2)
    fig.update_layout(
        xaxis_title="Еволюционен Индекс (EI)",
        yaxis_title="Регион",
        height=800,
        margin=dict(l=80, r=60, t=20, b=40),
        showlegend=False,
        dragmode=False,
        xaxis=dict(zeroline=True, zerolinewidth=1),
        yaxis=dict(tickfont=dict(size=12), categoryorder='total ascending'),
    )
    return fig
