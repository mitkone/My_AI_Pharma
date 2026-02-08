"""
AI Code Executor - Безопасно изпълнение на Python код генериран от AI.

Този модул позволява на AI да:
1. Чете master_data.csv
2. Генерира Python код за анализ
3. Изпълнява кода безопасно
4. Връща резултати и Plotly графики
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
import traceback
import logging
import re

logger = logging.getLogger(__name__)


def _strip_redundant_imports(code: str) -> str:
    """
    Премахва import редове за pandas и plotly - pd, px, go са вече в safe_globals.
    Това предотвратява ImportError: import not found в sandbox environment.
    """
    lines = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith('import pandas') or stripped.startswith('import plotly'):
            continue
        # import ... as pd / as px / as go
        if re.match(r'^from\s+(pandas|plotly)\s+import', stripped):
            continue
        lines.append(line)
    return '\n'.join(lines)


class CodeExecutionError(Exception):
    """Грешка при изпълнение на код."""
    pass


def safe_exec(
    code: str,
    master_data_path: Optional[Path] = None,
    df: Optional[pd.DataFrame] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Безопасно изпълнява Python код с достъп до данните.
    
    Параметри
    ---------
    code : str
        Python код за изпълнение
    master_data_path : Path, optional
        Път до CSV (не се използва ако df е подаден)
    df : pd.DataFrame, optional
        DataFrame с данните – приоритет над master_data_path
    timeout : int
        Timeout в секунди (currently not implemented)
    
    Връща
    ------
    Dict[str, Any]
        Резултати от изпълнението:
        - 'success': bool
        - 'result': Any (result от кода)
        - 'figure': plotly.graph_objects.Figure или None
        - 'output': str (print output)
        - 'error': str или None
    """
    # Подготовка на sandboxed environment
    safe_globals = {
        'pd': pd,
        'px': px,
        'go': go,
        'Path': Path,
        '__builtins__': {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'sum': sum,
            'min': min,
            'max': max,
            'round': round,
            'abs': abs,
            'sorted': sorted,
            'True': True,
            'False': False,
            'None': None,
        }
    }
    
    if df is not None and not df.empty:
        exec_df = df.copy()
    elif master_data_path and Path(master_data_path).exists():
        exec_df = pd.read_csv(master_data_path)
    else:
        exec_df = pd.DataFrame()
    safe_locals = {
        'master_data_path': str(master_data_path) if master_data_path else '',
        'df': exec_df,
        'result': None,
        'fig': None,
    }
    
    # Премахваме import редове – pd, px, go са вече в safe_globals
    code = _strip_redundant_imports(code)
    
    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, safe_globals, safe_locals)
        
        return {
            'success': True,
            'result': safe_locals.get('result'),
            'figure': safe_locals.get('fig'),
            'output': stdout_capture.getvalue(),
            'error': None
        }
    
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Code execution error: {error_trace}")
        
        return {
            'success': False,
            'result': None,
            'figure': None,
            'output': stdout_capture.getvalue(),
            'error': f"{type(e).__name__}: {str(e)}\n\n{error_trace}"
        }


def generate_analysis_code(
    question: str,
    product_name: str,
    data_summary: Dict[str, Any]
) -> str:
    """
    Генерира prompt за AI да създаде анализен код.
    
    Параметри
    ---------
    question : str
        Въпрос от потребителя
    product_name : str
        Име на избрания продукт
    data_summary : Dict[str, Any]
        Резюме на наличните данни
    
    Връща
    ------
    str
        Prompt за AI
    """
    prompt = f"""You are a pharmaceutical data analyst. The user asked:

"{question}"

**Context:**
- Selected product: {product_name}
- Data summary: {data_summary}

**Your task:**
Write Python code to analyze the data and answer the question.

**Data Access:**
- Use the dataframe `df` already loaded in memory – DO NOT use pd.read_csv or master_data_path
- Column names: Drug_Name (Drug), Region, District (Brick), Quarter (Period), Units (Sales), Source
- DO NOT use import statements - pd, px, go are ALREADY available

**Calculation Method – STRICT (NEVER estimate):**
- To find 'most sales' or 'top region': 1) Filter by Period (Quarter == 'Q4 2025'); 2) Group by Region or Drug_Name; 3) Sum Units; 4) Sort by Units descending: .sort_values('Units', ascending=False)
- ALWAYS sort by Units descending when looking for 'top' anything
- Always use .sum() for totals – never use a single row value when you need aggregate
- Growth_Pct: calculate as ((current - previous) / previous * 100) when previous > 0

**Specific Definitions:**
- Evolution Index (EI): ((100 + Product_Growth) / (100 + Class_Growth)) * 100
- Market Share: Sales of a specific drug / total sales of all drugs in that period/region * 100

**Handling Errors:**
- If the requested period or drug does not exist in the data: set result = 'Липсват данни за този период/продукт. Моля, проверете наличните във филтрите.'

**Language:**
- Always answer in Bulgarian, professional and concise

**Verification:**
- Before giving a number, double-check: is it the sum of sales (groupby + sum) or a single row value?

**Output Requirements:**
- ALWAYS assign result to `result` variable (string)
- ALWAYS assign figure to `fig` variable (Plotly figure or fig = None)
- Handle empty data, division by zero

Now write ONLY the Python code (no markdown, no explanation):"""
    
    return prompt


def get_data_summary_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Резюме на данните от DataFrame (за AI context)."""
    try:
        from data_processing import get_period_sort_key
        periods = []
        if 'Quarter' in df.columns:
            periods = sorted(df['Quarter'].unique().tolist(), key=get_period_sort_key)
        return {
            'total_rows': len(df),
            'regions': df['Region'].nunique() if 'Region' in df.columns else 0,
            'drugs': df['Drug_Name'].nunique() if 'Drug_Name' in df.columns else 0,
            'periods': periods,
            'sources': df['Source'].unique().tolist() if 'Source' in df.columns else [],
        }
    except Exception as e:
        logger.error(f"Error getting data summary from df: {e}")
        return {'error': str(e)}


def get_data_summary(master_data_path: Path) -> Dict[str, Any]:
    """
    Извлича резюме на данните за context на AI.
    
    Параметри
    ---------
    master_data_path : Path
        Път до master_data.csv
    
    Връща
    ------
    Dict[str, Any]
        Резюме с: regions, drugs, periods, total_rows
    """
    try:
        # Четем само header + първите 1000 реда за бързина
        df_sample = pd.read_csv(master_data_path, nrows=1000)
        
        # Ако е малък файл, четем всичко
        total_rows = sum(1 for _ in open(master_data_path)) - 1  # -1 за header
        
        if total_rows <= 10000:
            df = pd.read_csv(master_data_path)
        else:
            df = df_sample
        
        # Хронологично сортиране на периоди
        from data_processing import get_period_sort_key
        periods = []
        if 'Quarter' in df.columns:
            periods = sorted(df['Quarter'].unique().tolist(), key=get_period_sort_key)
        
        return {
            'total_rows': total_rows,
            'regions': df['Region'].nunique() if 'Region' in df.columns else 0,
            'drugs': df['Drug_Name'].nunique() if 'Drug_Name' in df.columns else 0,
            'periods': periods,
            'sources': df['Source'].unique().tolist() if 'Source' in df.columns else [],
        }
    
    except Exception as e:
        logger.error(f"Error getting data summary: {e}")
        return {'error': str(e)}


def create_mobile_friendly_figure(fig: go.Figure) -> go.Figure:
    """
    Оптимизира Plotly фигура за мобилни устройства.
    
    Параметри
    ---------
    fig : go.Figure
        Plotly фигура
    
    Връща
    ------
    go.Figure
        Оптимизирана фигура
    """
    if fig is None:
        return None
    
    # Mobile-first настройки
    fig.update_layout(
        height=500,  # Оптимална височина за mobile (matching config.MOBILE_CHART_HEIGHT)
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(size=12),
        hovermode='closest',
        dragmode=False,
        clickmode="event+select",
        uirevision="constant",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.5,  # Още по-долу за да не смачква графиката
            xanchor="center",
            x=0.5
        ),
        xaxis=dict(
            tickangle=-45,
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
        ),
        yaxis=dict(
            title_font=dict(size=14),
            tickfont=dict(size=14),
            autorange=True,
        ),
    )
    
    return fig


def validate_code_safety(code: str) -> Tuple[bool, Optional[str]]:
    """
    Проверява дали кодът е безопасен за изпълнение.
    
    Блокира:
    - import statements (освен разрешените)
    - file operations (освен read_csv)
    - os/subprocess commands
    - eval/exec
    
    Параметри
    ---------
    code : str
        Код за проверка
    
    Връща
    ------
    Tuple[bool, Optional[str]]
        (is_safe, error_message)
    """
    dangerous_patterns = [
        'import os',
        'import sys',
        'import subprocess',
        'import shutil',
        '__import__',
        'eval(',
        'compile(',
        'open(',  # Разрешаваме само read_csv
        'write',
        'delete',
        'remove',
        'rmdir',
        'system(',
    ]
    
    code_lower = code.lower()
    
    for pattern in dangerous_patterns:
        if pattern in code_lower:
            # Exception за pd.read_csv
            if pattern == 'open(' and 'pd.read_csv' in code:
                continue
            
            return False, f"Опасна операция: {pattern}"
    
    return True, None
