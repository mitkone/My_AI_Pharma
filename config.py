"""
Конфигурационни константи за Pharma Data Viz приложението.
Тук съхраняваме всички настройки на едно място за лесна поддръжка.
"""

from pathlib import Path

# === ДИРЕКТОРИИ ===
# Главна папка на проекта
PROJECT_DIR = Path(__file__).parent

# Папка с Excel файлове (същата, където е app.py)
DATA_DIR = PROJECT_DIR

# Папки по екипи – данните за всеки екип се пазят в отделна папка
TEAM_FOLDERS = ["Team 1", "Team 2", "Team 3"]

# === STREAMLIT НАСТРОЙКИ ===
PAGE_TITLE = "STADA Rx Data"
PAGE_ICON = "📊"
LAYOUT = "centered"  # Mobile-first: centered layout

# Време за кеширане на данните (секунди)
CACHE_TTL = 300  # 5 минути

# Мобилна оптимизация
MOBILE_OPTIMIZED = True
MOBILE_CHART_HEIGHT = 500  # Фиксирана височина за мобилни

# === КОЛОНИ В ДАННИТЕ ===
# Задължителни колони след обработка на Excel
REQUIRED_COLUMNS = ["Region", "Drug_Name", "Quarter", "Units"]

# Опционални колони
OPTIONAL_COLUMNS = ["District", "Source", "Molecule"]

# === ПЕРИОДИ ===
# Тримесечия
QUARTERS = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

# Месеци
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

# Години за разпознаване на периоди
VALID_YEARS = ["2023", "2024", "2025", "2026"]

# === ВИЗУАЛИЗАЦИИ ===
# Метрики за показване (само Units, останалото се показва в hover)
METRICS = ["Units (опак.)"]

# Височина на графики - Mobile-first: фиксирана на 500px
CHART_HEIGHT = 500
BRICK_CHART_HEIGHT = 500
MARKET_SHARE_CHART_HEIGHT = 650  # По-голяма за по-четливи tooltips и autoscale
MARKET_SHARE_CHART_HEIGHT_MOBILE = 500  # Фиксирана височина – не се смачква при много конкуренти
TIMELINE_CHART_HEIGHT = 500
COMPARISON_CHART_HEIGHT = 500

# Plotly mobile config - scroll zoom off, no toolbar, sticky tooltips
PLOTLY_CONFIG = {
    "scrollZoom": False,
    "displayModeBar": False,   # Hide floating menu bar; tooltip stays until click elsewhere
    "staticPlot": False,
    "responsive": True,
}

# === AI НАСТРОЙКИ ===
# OpenAI модел
AI_MODEL = "gpt-4o-mini"
AI_MAX_TOKENS = 1500

# === ФАЙЛОВЕ ===
# Разширения на Excel файлове
EXCEL_EXTENSIONS = [".xlsx", ".xls"]

# Префикс за временни файлове (игнорираме)
TEMP_FILE_PREFIX = ".~"
