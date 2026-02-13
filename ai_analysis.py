"""
AI анализ на фармацевтични данни с OpenAI + Code Execution.

Позволява на потребителя да задава въпроси за данните и получава:
- Автоматизиран анализ с препоръки
- Динамично генериран и изпълнен Python код
- Визуализации (Plotly charts)
"""

import os
import streamlit as st
import pandas as pd
from typing import Optional
from pathlib import Path
import config
from ai_code_executor import (
    safe_exec,
    generate_analysis_code,
    get_data_summary,
    get_data_summary_from_df,
    create_mobile_friendly_figure,
    validate_code_safety
)


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


def execute_ai_code_analysis(
    question: str,
    product_name: str,
    df: pd.DataFrame,
    master_data_path: Optional[Path] = None
) -> dict:
    """
    Изпълнява AI анализ с динамично генериран Python код.
    
    Параметри
    ---------
    question : str
        Въпрос от потребителя
    product_name : str
        Име на продукта
    df : pd.DataFrame
        DataFrame с данните (използва се директно, не се чете от CSV)
    master_data_path : Path, optional
        Път до CSV – не се използва; остава за обратна съвместимост
    
    Връща
    ------
    dict
        Резултати: 'success', 'result' (text), 'figure', 'code', 'error'
    """
    try:
        from openai import OpenAI
        
        # Извличане на data summary от DataFrame
        data_summary = get_data_summary_from_df(df) if df is not None and not df.empty else get_data_summary(master_data_path) if master_data_path else {}
        
        # Генериране на prompt за AI
        prompt = generate_analysis_code(question, product_name, data_summary)
        
        # AI генерира код
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=config.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.1,  # По-ниска температура за по-стабилен код
        )
        
        generated_code = response.choices[0].message.content.strip()
        
        # Почистване на markdown code blocks ако има
        if generated_code.startswith("```"):
            lines = generated_code.split('\n')
            generated_code = '\n'.join(lines[1:-1])  # Премахва ``` wrapper
        
        # Валидация за безопасност
        is_safe, safety_error = validate_code_safety(generated_code)
        if not is_safe:
            return {
                'success': False,
                'result': None,
                'figure': None,
                'code': generated_code,
                'error': f"Code safety check failed: {safety_error}"
            }
        
        # Изпълнение на кода – използваме df от паметта
        execution_result = safe_exec(generated_code, master_data_path=None, df=df)
        
        # Mobile-optimize фигурата ако има
        if execution_result['figure']:
            execution_result['figure'] = create_mobile_friendly_figure(execution_result['figure'])
        
        execution_result['code'] = generated_code
        return execution_result
    
    except Exception as e:
        return {
            'success': False,
            'result': None,
            'figure': None,
            'code': None,
            'error': str(e)
        }


def render_ai_analysis_tab(df: pd.DataFrame, sel_product: str, competitors: list):
    """
    Рендира таб с AI анализ + Code Execution.
    
    Параметри
    ---------
    df : pd.DataFrame
        Филтрирани данни
    sel_product : str
        Избран продукт
    competitors : list
        Конкуренти
    """
    st.subheader("🤖 AI Analyst с Code Execution")
    st.markdown(
        "**Upgraded AI:** Пиши Python код, изпълнявай го директно и визуализирай резултатите! "
        "AI използва **същите данни** като dashboard-а (текущите филтри)."
    )
    
    if df.empty:
        st.warning("Няма данни за текущите филтри. Промени филтрите в sidebar и опитай отново.")
    
    # Текстово поле за въпрос
    ai_question = st.text_area(
        "Напиши въпрос за анализ:",
        value="",
        placeholder="Напр.: Защо продажбите спадат в последните периоди?",
        height=100,
        key="ai_question",
        help="Задай конкретен въпрос за данните - колкото по-детайлен, толкова по-добър отговорът"
    )
    
    # Бутон за анализ
    if st.button("🚀 Анализирай с AI + Code", key="ai_analyze", type="primary", width="stretch"):
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
        
        # AI Code Execution Analysis – използва df директно (без CSV)
        try:
            with st.spinner("🤖 AI пише Python код..."):
                result = execute_ai_code_analysis(
                    question=ai_question,
                    product_name=sel_product,
                    df=df
                )
        except Exception as e:
            st.error("Грешка при AI анализа. Моля, опитай отново.")
            st.info(f"Детайли: {str(e)}")
            return
        
        # Показване на резултатите (Mobile-friendly)
        if result['success']:
            st.success("✅ Анализът завърши успешно!")
            
            # 1. ТЕКСТОВ РЕЗУЛТАТ (Mobile-friendly container)
            st.markdown("### 📊 Отговор:")
            with st.container():
                if result['result']:
                    st.markdown(f"**{result['result']}**")
                
                if result['output']:
                    with st.expander("📝 Детайли от анализа"):
                        st.text(result['output'])
            
            # 2. ВИЗУАЛИЗАЦИЯ (Mobile-optimized)
            if result['figure']:
                st.markdown("### 📈 Визуализация:")
                # Mobile-friendly chart display
                st.plotly_chart(
                    result['figure'],
                    width="stretch",
                    config=config.PLOTLY_CONFIG
                )
            
            # 3. ГЕНЕРИРАН КОД (Debug)
            with st.expander("🔍 Виж генерирания Python код"):
                st.code(result['code'], language='python')
        
        else:
            st.error("❌ Грешка при изпълнение на анализа")
            st.error(result['error'])
            
            if result['code']:
                with st.expander("🔍 Виж генерирания код (с грешка)"):
                    st.code(result['code'], language='python')
