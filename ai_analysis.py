"""
AI анализ на фармацевтични данни с OpenAI.
Позволява на потребителя да задава въпроси за данните и получава
автоматизиран анализ с препоръки.
"""

import os
import streamlit as st
import pandas as pd
from typing import Optional
import config


def check_api_key() -> bool:
    """
    Проверява дали OpenAI API ключът е наличен.
    
    Връща
    ------
    bool
        True ако ключът е зададен
    """
    return bool(os.environ.get("OPENAI_API_KEY"))


def build_data_context(
    df: pd.DataFrame,
    sel_product: str,
    competitors: list,
    period_col: str = "Quarter"
) -> str:
    """
    Изгражда текстов контекст от данните за AI анализа.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни
    sel_product : str
        Избран продукт
    competitors : list
        Конкуренти
    period_col : str
        Колона с периоди
    
    Връща
    ------
    str
        Текстов контекст с ключови данни
    """
    ctx_parts = []
    
    # Основна информация
    ctx_parts.append(f"Продукт: {sel_product}")
    ctx_parts.append(f"Региони: {df['Region'].nunique()}")
    
    # Продажби по региони
    if "Region" in df.columns:
        reg_units = df[df["Drug_Name"] == sel_product].groupby("Region")["Units"].sum()
        reg_sorted = reg_units.sort_values(ascending=False)
        ctx_parts.append(
            "Опаковки по регион за " + sel_product + ": " +
            ", ".join([f"{r}={int(u)}" for r, u in reg_sorted.head(10).items()])
        )
    
    # Тренд по периоди
    by_period = df[df["Drug_Name"] == sel_product].groupby(period_col)["Units"].sum()
    if len(by_period) > 1:
        ctx_parts.append(
            "Тренд по периоди: " +
            ", ".join([f"{p}={int(u)}" for p, u in by_period.items()])
        )
    
    # Конкуренти
    ctx_parts.append(f"Конкуренти на графиката: {competitors}")
    if competitors:
        for c in competitors[:5]:
            cu = df[df["Drug_Name"] == c]["Units"].sum()
            ctx_parts.append(f"  {c}: {int(cu)} опаковки")
    
    return "\n".join(ctx_parts)


def get_ai_analysis(question: str, data_context: str) -> Optional[str]:
    """
    Изпраща въпрос и контекст към OpenAI и получава анализ.
    
    Параметри
    ---------
    question : str
        Въпрос на потребителя
    data_context : str
        Контекст от данните
    
    Връща
    ------
    Optional[str]
        Отговор от AI или None при грешка
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Промпт за AI
        prompt = f"""Ти си бизнес анализатор на фармацевтични продажби. Потребителят задава въпрос за данните.

**Данни:**
{data_context}

**Въпрос на потребителя:**
{question.strip()}

Отговори на български. Анализирай наличните данни, посочи възможни причини и практични препоръки (действия). Бъди конкретен и използвай числата от данните."""
        
        # Извикване на OpenAI API
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.AI_MAX_TOKENS,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Грешка при AI заявка: {e}")
        return None


def render_ai_analysis_tab(df: pd.DataFrame, sel_product: str, competitors: list):
    """
    Рендира таб с AI анализ.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни
    sel_product : str
        Избран продукт
    competitors : list
        Конкуренти
    """
    st.subheader("🤖 AI Анализ на данните")
    st.markdown(
        "AI ще анализира наличните данни и ще предложи възможни причини и решения. "
        "Избери готов въпрос или напиши свой."
    )
    
    # ===== SUGGESTED QUESTIONS (БУТОНИ) =====
    st.markdown("### 💡 Бързи въпроси")
    st.caption("Кликни на бутон за автоматично попълване:")
    
    col1, col2 = st.columns(2)
    
    suggested_question = None  # За съхраняване на избрания въпрос
    
    with col1:
        if st.button("🔍 Защо спада ръстът?", use_container_width=True):
            suggested_question = f"Защо {sel_product} спада в последните периоди? Анализирай възможните причини и предложи решения."
        
        if st.button("📊 Кой регион е най-слаб?", use_container_width=True):
            suggested_question = f"Кой регион има най-лоши резултати за {sel_product}? Защо и какво може да се подобри?"
    
    with col2:
        if st.button("🏆 Къде растем най-много?", use_container_width=True):
            suggested_question = f"В кои региони {sel_product} расте най-бързо и какво правим правилно там?"
        
        if st.button("⚔️ Как се справям срещу конкуренти?", use_container_width=True):
            comp_text = ", ".join(competitors[:3]) if competitors else "конкуренти"
            suggested_question = f"Как {sel_product} се справя срещу {comp_text}? Какви са силните и слабите страни?"
    
    st.divider()
    
    # Текстово поле за въпрос
    ai_question = st.text_area(
        "Или напиши свой въпрос:",
        value=suggested_question if suggested_question else "",
        placeholder="Защо продажбите спадат в последните периоди?",
        height=100,
        key="ai_question",
        help="Задай конкретен въпрос за данните - колкото по-детайлен, толкова по-добър отговорът"
    )
    
    # Бутон за анализ
    if st.button("🚀 Анализирай с AI", key="ai_analyze", type="primary", use_container_width=True):
        if not ai_question or not ai_question.strip():
            st.warning("Въведи въпрос.")
            return
        
        # Проверка за API ключ
        if not check_api_key():
            st.error(
                "За AI анализ е нужен **OPENAI_API_KEY**. "
                "Добави го в `.env` файл и рестартирай приложението."
            )
            st.code(
                "# Създай файл .env в папката на проекта:\n"
                "OPENAI_API_KEY=sk-proj-твой-ключ-тук",
                language="bash"
            )
            return
        
        # Изграждане на контекст и извикване на AI
        with st.spinner("Анализираме..."):
            data_context = build_data_context(df, sel_product, competitors)
            answer = get_ai_analysis(ai_question, data_context)
            
            if answer:
                st.markdown("### Резултат")
                st.markdown(answer)
