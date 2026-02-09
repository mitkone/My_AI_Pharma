"""
Слой с бизнес изчисления – само векторни Pandas операции, без UI.
Всички тежки функции са с @st.cache_data и се преизчисляват само при промяна на входните параметри.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional

# --- Helpers (no Streamlit in logic, but cache is in this module) ---

def _is_atc_class(drug_name) -> bool:
    """Проверява дали е ATC клас (напр. C10A1 STATINS)."""
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


@st.cache_data(show_spinner=False)
def compute_last_vs_previous_rankings(
    df: pd.DataFrame,
    product: str,
    period_col: str,
    periods: Tuple[str, ...],
) -> Optional[Dict[str, Any]]:
    """
    Изчислява лидерборд за % ръст по регион за един продукт: последен vs предпоследен период.
    Връща merged DataFrame (Rank, Region, Last_Units, Previous_Units, Growth_%), last_period, prev_period, top_region, top_growth.
    """
    if df.empty or "Region" not in df.columns or "Units" not in df.columns or period_col not in df.columns:
        return None
    if "Drug_Name" not in df.columns or not product:
        return None
    if len(periods) < 2:
        return None

    sub = df.loc[df["Drug_Name"] == product, [period_col, "Region", "Units"]]
    if sub.empty:
        return None

    last_period, prev_period = periods[-1], periods[-2]
    last_df = sub.loc[sub[period_col] == last_period].groupby("Region", as_index=False)["Units"].sum()
    last_df = last_df.rename(columns={"Units": "Last_Units"})
    prev_df = sub.loc[sub[period_col] == prev_period].groupby("Region", as_index=False)["Units"].sum()
    prev_df = prev_df.rename(columns={"Units": "Previous_Units"})

    merged = last_df.merge(prev_df, on="Region", how="outer").fillna(0)
    prev_u = merged["Previous_Units"].values
    curr_u = merged["Last_Units"].values
    merged["Growth_%"] = np.where(prev_u == 0, np.where(curr_u > 0, 100.0, 0.0), ((curr_u - prev_u) / prev_u) * 100)
    merged = merged.sort_values("Growth_%", ascending=False).reset_index(drop=True)
    merged["Rank"] = range(1, len(merged) + 1)

    top_region = merged.iloc[0]["Region"] if len(merged) > 0 else None
    top_growth = float(merged.iloc[0]["Growth_%"]) if len(merged) > 0 else None
    return {
        "merged": merged,
        "last_period": last_period,
        "prev_period": prev_period,
        "top_region": top_region,
        "top_growth": top_growth,
    }


@st.cache_data(show_spinner=False)
def compute_top3_drugs(
    df: pd.DataFrame,
    region: str,
    district: str,
    has_district: bool,
    competitor_drugs: Tuple[str, ...],
) -> List[str]:
    """
    Връща списък от до 3 медикамента (от competitor_drugs) с най-много Units за дадения регион/брик.
    """
    if not competitor_drugs:
        return []
    f = df.copy()
    if region != "Всички":
        f = f[f["Region"] == region]
    if has_district and district != "Всички":
        f = f[f["District"] == district]
    f = f[f["Drug_Name"].isin(competitor_drugs)]
    s = f.groupby("Drug_Name")["Units"].sum()
    return s.sort_values(ascending=False).head(3).index.tolist()


@st.cache_data(show_spinner=False)
def compute_ei_rows_and_overall(
    df: pd.DataFrame,
    drugs: Tuple[str, ...],
    ref_period: str,
    base_period: str,
    period_col: str,
) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """
    Изчислява EI редове и общ претеглен EI за списък медикаменти.
    Формула: EI = ((100 + Product_Growth) / (100 + Class_Growth)) * 100.
    Връща (rows, overall_ei).
    """
    if "Source" not in df.columns or not drugs:
        return [], None

    rows: List[Dict[str, Any]] = []
    total_sales_ref = 0.0
    weighted_ei_sum = 0.0

    for drug in drugs:
        product_df = df[df["Drug_Name"] == drug]
        sales_ref = product_df[product_df[period_col] == ref_period]["Units"].sum()
        sales_base = product_df[product_df[period_col] == base_period]["Units"].sum()
        growth_pct = ((sales_ref - sales_base) / sales_base * 100) if sales_base else (100.0 if sales_ref else 0.0)
        product_source = product_df["Source"].iloc[0] if len(product_df) > 0 else None
        class_growth_pct = None
        ei = None
        if product_source:
            df_classes = df[df["Drug_Name"].apply(_is_atc_class)]
            matching = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
            if len(matching) > 0:
                class_name = matching[0]
                class_ref = df[(df["Drug_Name"] == class_name) & (df[period_col] == ref_period)]["Units"].sum()
                class_base = df[(df["Drug_Name"] == class_name) & (df[period_col] == base_period)]["Units"].sum()
                class_growth_pct = ((class_ref - class_base) / class_base * 100) if class_base else (100.0 if class_ref else 0.0)
                ei = ((100 + growth_pct) / (100 + class_growth_pct)) * 100
        rows.append({
            "drug": drug,
            "sales_ref": sales_ref,
            "sales_base": sales_base,
            "growth_pct": growth_pct,
            "class_growth_pct": class_growth_pct,
            "ei": ei,
        })
        if ei is not None:
            total_sales_ref += sales_ref
            weighted_ei_sum += ei * sales_ref

    overall_ei = (weighted_ei_sum / total_sales_ref) if total_sales_ref > 0 else None
    return rows, overall_ei


@st.cache_data(show_spinner=False)
def compute_region_ei_benchmark(
    df_national: pd.DataFrame,
    drugs: Tuple[str, ...],
    ref_period: str,
    base_period: str,
    period_col: str,
) -> List[Tuple[str, float]]:
    """Връща списък (region, weighted_avg_ei) за всеки регион, сортиран по EI descending."""
    if df_national.empty or "Region" not in df_national.columns or not drugs:
        return []
    regions = sorted(df_national["Region"].unique())
    out: List[Tuple[str, float]] = []
    for region in regions:
        df_r = df_national[df_national["Region"] == region]
        rows, _ = compute_ei_rows_and_overall(df_r, drugs, ref_period, base_period, period_col)
        w_sum = 0.0
        ei_w = 0.0
        for r in rows:
            if r["ei"] is not None and r["sales_ref"] and r["sales_ref"] > 0:
                ei_w += r["ei"] * r["sales_ref"]
                w_sum += r["sales_ref"]
        if w_sum > 0:
            out.append((region, ei_w / w_sum))
    out.sort(key=lambda x: x[1], reverse=True)
    return out
