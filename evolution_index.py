"""
Еволюционен Индекс (EI) – анализ на растеж на продукт vs терапевтичен клас.

EI = ((100 + Product_Growth) / (100 + Class_Growth)) * 100
EI > 100 означава, че продуктът расте по-бързо от пазарния сегмент.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, Tuple, List, Dict, Any


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


def _calc_evolution_index(
    df: pd.DataFrame,
    drug: str,
    ref_period: str,
    base_period: str,
    period_col: str = "Quarter",
) -> Optional[Dict[str, Any]]:
    """
    Изчислява EI за даден медикамент между два периода.
    
    Връща dict: sales_ref, sales_base, growth_pct, class_growth_pct, ei, class_name
    или None ако няма данни.
    """
    if "Source" not in df.columns:
        return None
    
    sales_ref = df[(df["Drug_Name"] == drug) & (df[period_col] == ref_period)]["Units"].sum()
    sales_base = df[(df["Drug_Name"] == drug) & (df[period_col] == base_period)]["Units"].sum()
    
    if sales_base == 0:
        growth_pct = 0.0 if sales_ref == 0 else 100.0
    else:
        growth_pct = ((sales_ref - sales_base) / sales_base) * 100
    
    product_source = df[df["Drug_Name"] == drug]["Source"].iloc[0] if len(df[df["Drug_Name"] == drug]) > 0 else None
    if not product_source:
        return {"sales_ref": sales_ref, "sales_base": sales_base, "growth_pct": growth_pct, "class_growth_pct": None, "ei": None, "class_name": None}
    
    df_classes = df[df["Drug_Name"].apply(_is_atc_class)].copy()
    matching_classes = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
    
    if len(matching_classes) == 0:
        return {"sales_ref": sales_ref, "sales_base": sales_base, "growth_pct": growth_pct, "class_growth_pct": None, "ei": None, "class_name": None}
    
    class_name = matching_classes[0]
    class_ref = df[(df["Drug_Name"] == class_name) & (df[period_col] == ref_period)]["Units"].sum()
    class_base = df[(df["Drug_Name"] == class_name) & (df[period_col] == base_period)]["Units"].sum()
    
    if class_base == 0:
        class_growth_pct = 0.0 if class_ref == 0 else 100.0
    else:
        class_growth_pct = ((class_ref - class_base) / class_base) * 100
    
    ei = ((100 + growth_pct) / (100 + class_growth_pct)) * 100
    
    return {
        "sales_ref": sales_ref,
        "sales_base": sales_base,
        "growth_pct": growth_pct,
        "class_growth_pct": class_growth_pct,
        "ei": ei,
        "class_name": class_name,
    }


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
    
    # Multi-select за портфолио
    sel_drugs = st.multiselect(
        "Избери медикаменти (портфолио)",
        drugs_for_select,
        default=[drugs_for_select[0]] if drugs_for_select else [],
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
    
    # Изчисляване за всеки лекарствен продукт
    rows: List[Dict[str, Any]] = []
    total_sales_ref = 0.0
    weighted_ei_sum = 0.0
    
    for drug in sel_drugs:
        result = _calc_evolution_index(df, drug, ref_period, base_period, period_col)
        if result and result["ei"] is not None:
            rows.append({
                "drug": drug,
                "sales_ref": result["sales_ref"],
                "sales_base": result["sales_base"],
                "growth_pct": result["growth_pct"],
                "class_growth_pct": result["class_growth_pct"],
                "ei": result["ei"],
            })
            total_sales_ref += result["sales_ref"]
            weighted_ei_sum += result["ei"] * result["sales_ref"]
        else:
            rows.append({
                "drug": drug,
                "sales_ref": result["sales_ref"] if result else 0,
                "sales_base": result["sales_base"] if result else 0,
                "growth_pct": result["growth_pct"] if result else None,
                "class_growth_pct": result["class_growth_pct"] if result else None,
                "ei": None,
            })
    
    # Общ EI – претеглена средна по продажби (референтен период)
    overall_ei = (weighted_ei_sum / total_sales_ref) if total_sales_ref > 0 else None
    
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
    
    # Regional Benchmark Chart – EI по регион/брик за избраното портфолио
    if "District" in df_national.columns:
        locs = df_national.groupby(["Region", "District"]).size().reset_index()[["Region", "District"]]
        locs = locs.sort_values(["Region", "District"])
        loc_labels = [f"{r} | {d}" for r, d in zip(locs["Region"], locs["District"])]
        loc_filters = [(locs["Region"].iloc[i], locs["District"].iloc[i]) for i in range(len(locs))]
    else:
        loc_labels = sorted(df_national["Region"].unique())
        loc_filters = [(r, None) for r in loc_labels]
    
    region_ei_data: List[Tuple[str, float]] = []
    for i, (region, district) in enumerate(loc_filters):
        df_loc = df_national[df_national["Region"] == region]
        if district is not None:
            df_loc = df_loc[df_loc["District"] == district]
        w_sum = 0.0
        ei_weighted = 0.0
        for drug in sel_drugs:
            res = _calc_evolution_index(df_loc, drug, ref_period, base_period, period_col)
            if res and res["ei"] is not None and res["sales_ref"] > 0:
                ei_weighted += res["ei"] * res["sales_ref"]
                w_sum += res["sales_ref"]
        if w_sum > 0:
            region_ei_data.append((loc_labels[i], ei_weighted / w_sum))
    
    if region_ei_data:
        st.markdown("---")
        st.markdown("### 📊 EI по регион/брик (бенчмарк)")
        st.caption("Изпълнение на избраното портфолио във всеки регион. Вертикалната червена линия е EI = 100.")
        
        labels = [r[0] for r in region_ei_data]
        values = [r[1] for r in region_ei_data]
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
            yaxis_title="Регион / Брик",
            height=800,
            margin=dict(l=10, r=60, t=20, b=40),
            showlegend=False,
            xaxis=dict(zeroline=True, zerolinewidth=1),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
    
    # Таблица: Drug Name | Sales (Ref) | Sales (Base) | Growth % | Class Growth % | EI
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
    
    # TOTAL ред
    total_sales_base = sum(r["sales_base"] for r in rows)
    total_growth = ((total_sales_ref - total_sales_base) / total_sales_base * 100) if total_sales_base > 0 else 0
    # За класа – използваме среднопретегления class growth или просто overall EI
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
