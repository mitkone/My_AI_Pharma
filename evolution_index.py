"""
Еволюционен Индекс (EI) – анализ на растеж на продукт vs терапевтичен клас.

EI = ((100 + Product_Growth) / (100 + Class_Growth)) * 100
EI > 100 означава, че продуктът расте по-бързо от пазарния сегмент.
"""

import streamlit as st
import pandas as pd
from typing import Optional, Tuple


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


def _get_prev_year_quarter(quarter: str) -> Optional[str]:
    """Връща същото тримесечие от предходната година. Напр. Q1 2024 -> Q1 2023."""
    parts = str(quarter).strip().split()
    if len(parts) != 2:
        return None
    q_part, year_str = parts[0], parts[1]
    try:
        year = int(year_str)
        return f"{q_part} {year - 1}"
    except ValueError:
        return None


def _calc_evolution_index(
    df: pd.DataFrame,
    drug: str,
    quarter: str,
    period_col: str = "Quarter",
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """
    Изчислява EI за даден медикамент и период.
    
    Връща: (product_growth_pct, class_growth_pct, ei_value, class_name)
    """
    if "Source" not in df.columns:
        return None, None, None, None
    
    prev_quarter = _get_prev_year_quarter(quarter)
    if not prev_quarter:
        return None, None, None, None
    
    # Product units
    product_current = df[(df["Drug_Name"] == drug) & (df[period_col] == quarter)]["Units"].sum()
    product_prev = df[(df["Drug_Name"] == drug) & (df[period_col] == prev_quarter)]["Units"].sum()
    
    if product_prev == 0:
        product_growth = 0.0 if product_current == 0 else 100.0
    else:
        product_growth = ((product_current - product_prev) / product_prev) * 100
    
    # Therapeutic class (ATC)
    product_source = df[df["Drug_Name"] == drug]["Source"].iloc[0] if len(df[df["Drug_Name"] == drug]) > 0 else None
    if not product_source:
        return product_growth, None, None, None
    
    df_classes = df[df["Drug_Name"].apply(_is_atc_class)].copy()
    matching_classes = df_classes[df_classes["Source"] == product_source]["Drug_Name"].unique()
    
    if len(matching_classes) == 0:
        return product_growth, None, None, None
    
    class_name = matching_classes[0]
    
    class_current = df[(df["Drug_Name"] == class_name) & (df[period_col] == quarter)]["Units"].sum()
    class_prev = df[(df["Drug_Name"] == class_name) & (df[period_col] == prev_quarter)]["Units"].sum()
    
    if class_prev == 0:
        class_growth = 0.0 if class_current == 0 else 100.0
    else:
        class_growth = ((class_current - class_prev) / class_prev) * 100
    
    # EI formula
    ei = ((100 + product_growth) / (100 + class_growth)) * 100
    
    return product_growth, class_growth, ei, class_name


def render_evolution_index_tab(df: pd.DataFrame, periods: list, period_col: str = "Quarter") -> None:
    """
    Рендерира таба 'Еволюционен Индекс'.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни (уважава Region/Brick от sidebar)
    periods : list
        Сортирани периоди
    period_col : str
        Име на колоната с периоди
    """
    st.subheader("📊 Еволюционен Индекс")
    
    # Само медикаменти (без ATC класове) за избор
    drugs_for_select = sorted(
        df[~df["Drug_Name"].apply(_is_atc_class)]["Drug_Name"].unique()
    )
    
    if not drugs_for_select:
        st.warning("Няма налични медикаменти за анализ.")
        return
    
    if not periods:
        st.warning("Няма налични периоди за анализ.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        sel_drug = st.selectbox("Избери медикамент", drugs_for_select, key="ei_drug")
    with col2:
        sel_period = st.selectbox("Избери тримесечие", periods, index=len(periods) - 1, key="ei_period")
    
    product_growth, class_growth, ei_value, class_name = _calc_evolution_index(df, sel_drug, sel_period, period_col)
    
    if ei_value is None:
        st.info("Не е наличен терапевтичен клас за избрания медикамент, или липсват данни за сравнението.")
        return
    
    # Голяма метрика – центрирана
    st.markdown("---")
    st.markdown(f"### Еволюционен Индекс за **{sel_drug}**")
    st.metric(
        label=sel_period,
        value=f"{ei_value:.1f}",
        delta=None,
    )
    st.caption("EI > 100 означава, че продуктът расте по-бързо от пазарния сегмент.")
    
    # Сравнителна таблица
    st.markdown("---")
    st.markdown("**Сравнение**")
    comparison_data = {
        "Показател": ["% Ръст на продукта", "% Ръст на класа (пазара)", "EI стойност"],
        "Стойност": [
            f"{product_growth:+.1f}%",
            f"{class_growth:+.1f}%",
            f"{ei_value:.1f}",
        ],
    }
    st.table(pd.DataFrame(comparison_data))
