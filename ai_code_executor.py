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

logger = logging.getLogger(__name__)


class CodeExecutionError(Exception):
    """Грешка при изпълнение на код."""
    pass


def safe_exec(
    code: str,
    master_data_path: Path,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Безопасно изпълнява Python код с достъп до master_data.csv.
    
    Параметри
    ---------
    code : str
        Python код за изпълнение
    master_data_path : Path
        Път до master_data.csv
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
    
    safe_locals = {
        'master_data_path': str(master_data_path),
        'result': None,
        'fig': None,
    }
    
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

**Available data:**
- master_data.csv with columns: Region, Drug_Name, District, Quarter, Units, Source
- You can use: pandas (pd), plotly.express (px), plotly.graph_objects (go)

**Requirements:**
1. Load data: `df = pd.read_csv(master_data_path)`
2. Perform the analysis
3. Store the answer in variable `result` (string or number)
4. Create a Plotly chart in variable `fig` (if visualization makes sense)
5. Use print() for intermediate info (optional)

**Example:**
```python
# Load data
df = pd.read_csv(master_data_path)

# Analysis
product_data = df[df['Drug_Name'] == '{product_name}']
last_quarter = product_data[product_data['Quarter'] == 'Q4 2025']['Units'].sum()
prev_quarter = product_data[product_data['Quarter'] == 'Q3 2025']['Units'].sum()
growth = ((last_quarter - prev_quarter) / prev_quarter * 100) if prev_quarter > 0 else 0

result = f"Growth in Q4 2025: {{growth:.1f}}%"

# Visualization
quarterly_data = product_data.groupby('Quarter')['Units'].sum().reset_index()
fig = px.line(quarterly_data, x='Quarter', y='Units', title='{product_name} Sales Trend')
```

**Important:**
- ALWAYS assign result to `result` variable
- ALWAYS assign figure to `fig` variable (or set `fig = None` if no chart)
- Keep code simple and efficient
- Handle edge cases (empty data, division by zero, etc.)
- Use Bulgarian for `result` text

Now write ONLY the Python code (no markdown, no explanation):"""
    
    return prompt


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
