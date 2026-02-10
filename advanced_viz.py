"""
Advanced visualization modules that are robust and lightweight.
Currently includes:
- Churn Alert Table (biggest drops)
- Growth Leaders Table (biggest gains)
- Regional Growth Table (per-region growth for selected product)
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List

import config
from logic import compute_ei_rows_and_overall, compute_last_vs_previous_rankings


def _is_atc_class(drug_name) -> bool:
    if pd.isna(drug_name):
        return False
    s = str(drug_name)
    parts = s.split()
    if not parts:
        return False
    first = parts[0]
    return (
        len(first) >= 4
        and len(first) <= 7
        and first[0].isalpha()
        and any(c.isdigit() for c in first)
        and first.isupper()
        and len(parts) >= 2
        and drug_name not in ["GRAND TOTAL", "Grand Total"]
        and not s.startswith("Region")
    )


def render_churn_alert_table(
    df_raw: pd.DataFrame,
    periods: List[str],
    period_col: str = "Quarter",
    top_n: int = 10,
) -> None:
    """Churn Alert Table: top N products with biggest drop in sales this period."""
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


def render_growth_leaders_table(
    df_raw: pd.DataFrame,
    periods: List[str],
    period_col: str = "Quarter",
    top_n: int = 10,
) -> None:
    """Top Growth Table: products with biggest increase in sales this period."""
    st.markdown("### 🚀 Top Growth Table")
    if not periods or len(periods) < 2:
        st.caption("Need at least 2 periods.")
        return
    last_period = periods[-1]
    prev_period = periods[-2]
    df = df_raw[~df_raw["Drug_Name"].apply(_is_atc_class)]
    prev = df[df[period_col] == prev_period].groupby("Drug_Name")["Units"].sum().reset_index()
    prev.columns = ["Drug_Name", "Previous"]
    curr = df[df[period_col] == last_period].groupby("Drug_Name")["Units"].sum().reset_index()
    curr.columns = ["Drug_Name", "Current"]
    merged = prev.merge(curr, on="Drug_Name", how="outer").fillna(0)
    merged["Change"] = merged["Current"] - merged["Previous"]
    merged["Change_%"] = np.where(merged["Previous"] == 0, 0, (merged["Change"] / merged["Previous"]) * 100)
    merged = merged.sort_values("Change", ascending=False).head(top_n)
    merged["Previous"] = merged["Previous"].astype(int)
    merged["Current"] = merged["Current"].astype(int)
    merged["Change"] = merged["Change"].astype(int)
    merged["Change_%"] = merged["Change_%"].round(1)
    merged.columns = ["Entity", "Previous", "Current", "Change", "Change %"]
    st.caption(f"Top {top_n} products with biggest growth ({prev_period} → {last_period}).")
    st.dataframe(merged, use_container_width=True, height=320)


def render_regional_growth_table(
    df_raw: pd.DataFrame,
    sel_product: str,
    periods: List[str],
    period_col: str = "Quarter",
) -> None:
    """Regional Growth Table: growth by region for the selected product."""
    st.markdown("### 🗺️ Regional Growth Table")
    if not periods or len(periods) < 2 or not sel_product:
        st.caption("Need at least 2 periods and a selected product.")
        return
    res = compute_last_vs_previous_rankings(df_raw, sel_product, period_col, tuple(periods))
    if not res or "merged" not in res:
        st.caption("No regional data available for this product.")
        return
    merged = res["merged"].copy()
    merged = merged[["Region", "Previous_Units", "Last_Units", "Growth_%"]].rename(
        columns={
            "Previous_Units": "Previous",
            "Last_Units": "Current",
            "Growth_%": "Growth %",
        }
    )
    merged["Previous"] = merged["Previous"].astype(int)
    merged["Current"] = merged["Current"].astype(int)
    merged["Growth %"] = merged["Growth %"].round(1)
    merged = merged.sort_values("Growth %", ascending=False)
    st.caption(f"Regional growth for {sel_product} ({periods[-2]} → {periods[-1]}).")
    st.dataframe(merged, use_container_width=True, height=320)
