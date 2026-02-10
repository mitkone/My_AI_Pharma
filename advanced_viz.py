"""
Advanced visualization modules: Bubble Matrix, Waterfall, Radar, Churn Table.
Rendered only when the corresponding Admin Panel toggle is True.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from typing import List, Optional

import config
from logic import compute_ei_rows_and_overall


def _is_atc_class(drug_name) -> bool:
    if pd.isna(drug_name):
        return False
    s = str(drug_name)
    parts = s.split()
    if not parts:
        return False
    first = parts[0]
    return (
        len(first) >= 4 and len(first) <= 7
        and first[0].isalpha()
        and any(c.isdigit() for c in first)
        and first.isupper()
        and len(parts) >= 2
        and drug_name not in ["GRAND TOTAL", "Grand Total"]
        and not s.startswith("Region")
    )


def render_growth_share_bubble(
    df_raw: pd.DataFrame,
    products_list: List[str],
    periods: List[str],
    period_col: str = "Quarter",
) -> None:
    """Growth-Share Bubble Matrix: Market Share vs Evolution Index for all products."""
    st.markdown("### 📊 Growth-Share Bubble Matrix")
    if not periods or len(periods) < 2 or not products_list:
        st.caption("Need at least 2 periods and a product list.")
        return
    last_period = periods[-1]
    prev_period = periods[-2]
    # Filter to non-ATC products that we have in the list
    products = [p for p in products_list if not _is_atc_class(p)]
    if not products:
        st.caption("No valid products for bubble chart.")
        return

    rows_data = []
    for drug in products:
        ei_rows, overall_ei = compute_ei_rows_and_overall(
            df_raw, (drug,), last_period, prev_period, period_col
        )
        ei_val = overall_ei if overall_ei is not None else (ei_rows[0]["ei"] if ei_rows else None)
        if ei_val is None:
            continue
        product_units = df_raw[(df_raw["Drug_Name"] == drug) & (df_raw[period_col] == last_period)]["Units"].sum()
        if product_units <= 0:
            continue
        # Market share: product / class (national). Need class total for same Source.
        if "Source" not in df_raw.columns:
            ms = 0.0
        else:
            sub = df_raw[df_raw["Drug_Name"] == drug]
            if sub.empty:
                ms = 0.0
            else:
                src = sub["Source"].iloc[0]
                df_classes = df_raw[df_raw["Drug_Name"].apply(_is_atc_class)]
                matching = df_classes[df_classes["Source"] == src]["Drug_Name"].unique()
                if len(matching) == 0:
                    ms = 0.0
                else:
                    class_name = matching[0]
                    class_units = df_raw[(df_raw["Drug_Name"] == class_name) & (df_raw[period_col] == last_period)]["Units"].sum()
                    ms = (100 * product_units / class_units) if class_units > 0 else 0.0
        rows_data.append({"Drug_Name": drug, "Market_Share_%": round(ms, 2), "EI": round(ei_val, 2), "Volume": int(product_units)})

    if not rows_data:
        st.caption("No data for Growth-Share matrix.")
        return
    df_bubble = pd.DataFrame(rows_data)
    # Bubble size: scale Volume for visibility (e.g. sqrt)
    df_bubble["size"] = np.sqrt(df_bubble["Volume"].clip(lower=1))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_bubble["Market_Share_%"],
        y=df_bubble["EI"],
        text=df_bubble["Drug_Name"],
        mode="markers+text",
        marker=dict(size=df_bubble["size"], sizemode="diameter", sizeref=df_bubble["size"].max() / 40 if df_bubble["size"].max() > 0 else 1, opacity=0.7),
        textposition="top center",
    ))
    fig.update_layout(
        title="Market Share vs Evolution Index (bubble = volume)",
        xaxis_title="Market Share %",
        yaxis_title="Evolution Index",
        height=450,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=config.PLOTLY_CONFIG)


def render_regional_waterfall(
    df_raw: pd.DataFrame,
    periods: List[str],
    period_col: str = "Quarter",
) -> None:
    """Regional Waterfall: bridge between last period's and this period's sales by region."""
    st.markdown("### 📉 Regional Waterfall Chart")
    if not periods or len(periods) < 2 or "Region" not in df_raw.columns:
        st.caption("Need at least 2 periods and Region column.")
        return
    last_period = periods[-1]
    prev_period = periods[-2]

    prev_total = df_raw[df_raw[period_col] == prev_period]["Units"].sum()
    curr_total = df_raw[df_raw[period_col] == last_period]["Units"].sum()
    prev_by_r = df_raw[df_raw[period_col] == prev_period].groupby("Region")["Units"].sum()
    curr_by_r = df_raw[df_raw[period_col] == last_period].groupby("Region")["Units"].sum()
    all_regions = sorted(set(prev_by_r.index) | set(curr_by_r.index))
    deltas = []
    for r in all_regions:
        c = curr_by_r.get(r, 0)
        p = prev_by_r.get(r, 0)
        deltas.append((r, c - p))
    deltas.sort(key=lambda x: -x[1])  # biggest gain first
    names = ["Previous total"] + [f"{r} ({d:+.0f})" for r, d in deltas] + ["Current total"]
    values = [prev_total] + [d for _, d in deltas] + [curr_total]
    measure = ["absolute"] + ["relative"] * len(deltas) + ["total"]

    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=measure,
        x=names,
        y=values,
        connector={"line": {"color": "#64748b"}},
    ))
    fig.update_layout(
        title=f"Sales bridge: {prev_period} → {last_period}",
        height=420,
        margin=dict(l=10, r=10, t=50, b=120),
        xaxis_tickangle=-45,
        showlegend=False,
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=config.PLOTLY_CONFIG)


def render_radar_chart(
    df_raw: pd.DataFrame,
    sel_product: str,
    periods: List[str],
    period_col: str = "Quarter",
) -> None:
    """Radar Chart: compare two regions across MS, EI, Volume (normalized 0–100)."""
    st.markdown("### 🕸️ Radar Chart – Compare Two Regions")
    if not periods or len(periods) < 2 or "Region" not in df_raw.columns:
        st.caption("Need at least 2 periods and Region column.")
        return
    last_period = periods[-1]
    prev_period = periods[-2]
    regions = sorted(df_raw["Region"].unique())
    if len(regions) < 2:
        st.caption("Need at least 2 regions.")
        return

    r1 = st.selectbox("Region A", regions, key="radar_region_a")
    r2_options = [r for r in regions if r != r1]
    r2 = st.selectbox("Region B", r2_options, key="radar_region_b") if r2_options else None
    if r2 is None:
        st.caption("Only one region available.")
        return

    def kpis_for_region(region: str) -> tuple:
        df_r = df_raw[df_raw["Region"] == region]
        vol = df_r[(df_r["Drug_Name"] == sel_product) & (df_r[period_col] == last_period)]["Units"].sum()
        rows, overall = compute_ei_rows_and_overall(df_r, (sel_product,), last_period, prev_period, period_col)
        ei = overall if overall is not None else (rows[0]["ei"] if rows else 0) or 0
        # MS in region: product units / class units in that region
        if "Source" in df_r.columns and not df_r[df_r["Drug_Name"] == sel_product].empty:
            src = df_r[df_r["Drug_Name"] == sel_product]["Source"].iloc[0]
            df_cl = df_r[df_r["Drug_Name"].apply(_is_atc_class)]
            match = df_cl[df_cl["Source"] == src]["Drug_Name"].unique()
            if len(match) > 0:
                class_units = df_r[(df_r["Drug_Name"] == match[0]) & (df_r[period_col] == last_period)]["Units"].sum()
                ms = (100 * vol / class_units) if class_units > 0 else 0
            else:
                ms = 0
        else:
            ms = 0
        return ms, ei, vol

    ms1, ei1, vol1 = kpis_for_region(r1)
    ms2, ei2, vol2 = kpis_for_region(r2)
    vol_max = max(vol1, vol2) or 1
    # Normalize to 0–100: MS already 0–100, EI typically 50–150 -> (EI-50)/100*100 capped, Volume -> vol/vol_max*100
    def scale_ei(e):
        return max(0, min(100, (e - 50) / 1.0))  # 50->0, 100->50, 150->100
    r_a = [min(100, ms1), scale_ei(ei1), 100 * vol1 / vol_max]
    r_b = [min(100, ms2), scale_ei(ei2), 100 * vol2 / vol_max]
    theta = ["Market Share %", "EI (scaled)", "Volume %"]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=r_a + [r_a[0]], theta=theta + [theta[0]], name=r1, fill="toself"))
    fig.add_trace(go.Scatterpolar(r=r_b + [r_b[0]], theta=theta + [theta[0]], name=r2, fill="toself"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"{sel_product}: {r1} vs {r2}",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=config.PLOTLY_CONFIG)


def render_churn_alert_table(
    df_raw: pd.DataFrame,
    periods: List[str],
    period_col: str = "Quarter",
    top_n: int = 10,
) -> None:
    """Churn Alert Table: top N entities (products) with biggest drop in sales this period."""
    st.markdown("### ⚠️ Churn Alert Table")
    if not periods or len(periods) < 2:
        st.caption("Need at least 2 periods.")
        return
    last_period = periods[-1]
    prev_period = periods[-2]
    # Exclude ATC classes
    df = df_raw[~df_raw["Drug_Name"].apply(_is_atc_class)]
    prev = df[df[period_col] == prev_period].groupby("Drug_Name")["Units"].sum().reset_index()
    prev.columns = ["Drug_Name", "Previous"]
    curr = df[df[period_col] == last_period].groupby("Drug_Name")["Units"].sum().reset_index()
    curr.columns = ["Drug_Name", "Current"]
    merged = prev.merge(curr, on="Drug_Name", how="outer").fillna(0)
    merged["Change"] = merged["Current"] - merged["Previous"]
    merged["Change_%"] = np.where(merged["Previous"] == 0, 0, (merged["Change"] / merged["Previous"]) * 100)
    merged = merged.sort_values("Change", ascending=True).head(top_n)
    merged["Previous"] = merged["Previous"].astype(int)
    merged["Current"] = merged["Current"].astype(int)
    merged["Change"] = merged["Change"].astype(int)
    merged["Change_%"] = merged["Change_%"].round(1)
    merged.columns = ["Entity", "Previous", "Current", "Change", "Change %"]
    st.caption(f"Top {top_n} products with biggest drop in sales ({prev_period} → {last_period}).")
    st.dataframe(merged, use_container_width=True, height=320)
