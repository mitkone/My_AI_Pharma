"""
Модул за обработка и валидация на фармацевтични данни.
Съдържа функции за:
- Зареждане на Excel файлове
- Почистване и валидация на данни
- Обединяване на множество файлове
- Добавяне на метаданни (молекули, категории)
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple
import logging
import streamlit as st

from process_excel_hierarchy import process_pharma_excel
from drug_molecules import add_molecule_column
import config

# Настройка на логване
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_dataframe(df: pd.DataFrame, filename: str = "") -> Tuple[bool, str]:
    """
    Валидира дали DataFrame има необходимите колони.
    
    Параметри
    ---------
    df : pd.DataFrame
        DataFrame за проверка
    filename : str
        Име на файла (за по-информативни съобщения за грешка)
    
    Връща
    ------
    Tuple[bool, str]
        (is_valid, error_message) - is_valid е True ако данните са валидни
    """
    if df.empty:
        return False, f"Файлът {filename} е празен или не съдържа данни."
    
    # Проверка за задължителни колони
    missing_cols = [col for col in config.REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return False, f"Файлът {filename} липсват колони: {', '.join(missing_cols)}"
    
    # Проверка за валидни данни в Units
    if "Units" in df.columns:
        non_numeric = pd.to_numeric(df["Units"], errors="coerce").isna().sum()
        if non_numeric > 0:
            logger.warning(f"{filename}: {non_numeric} реда с невалидни Units (ще бъдат игнорирани)")
    
    return True, ""


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Почиства имената на колоните: премахва интервали, специални символи.
    
    Параметри
    ---------
    df : pd.DataFrame
        DataFrame с "мръсни" имена на колони
    
    Връща
    ------
    pd.DataFrame
        DataFrame с почистени имена на колони
    """
    # Премахване на водещи/крайни интервали
    df.columns = df.columns.str.strip()
    
    # Замяна на множество интервали с един
    df.columns = df.columns.str.replace(r'\s+', ' ', regex=True)
    
    return df


def extract_source_name(filename: str) -> str:
    """
    Извлича категория/име на продукта от името на файла.
    Пример: "Lipocante Total Q.xlsx" -> "Lipocante"
    
    Параметри
    ---------
    filename : str
        Име на Excel файла
    
    Връща
    ------
    str
        Категория на продукта
    """
    # Премахване на разширението
    name = Path(filename).stem
    
    # Премахване на общи суфикси
    for suffix in [" Total Q", " Total", " total", "_melted"]:
        name = name.replace(suffix, "")
    
    return name.strip()


def load_single_excel(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Зарежда и обработва един Excel файл.
    
    Параметри
    ---------
    filepath : Path
        Път до Excel файла
    
    Връща
    ------
    Optional[pd.DataFrame]
        DataFrame с обработени данни или None при грешка
    """
    try:
        logger.info(f"Зареждане на {filepath.name}...")
        
        # Обработка на йерархична структура
        df = process_pharma_excel(str(filepath), save=False, sheet_name=None)
        
        # Валидация
        is_valid, error_msg = validate_dataframe(df, filepath.name)
        if not is_valid:
            logger.error(f"Валидация на {filepath.name}: {error_msg}")
            return None
        
        # Почистване на колони
        df = clean_column_names(df)
        
        # Добавяне на източник (категория)
        source = extract_source_name(filepath.name)
        df["Source"] = source
        
        logger.info(f"✓ {filepath.name}: {len(df)} реда, източник '{source}'")
        return df
        
    except Exception as e:
        logger.error(f"Грешка при зареждане на {filepath.name}: {e}")
        return None


@st.cache_data(show_spinner=False)
def load_all_excel_files(data_dir: Path = config.DATA_DIR) -> pd.DataFrame:
    """
    Зарежда всички Excel файлове от директория и ги обединява.
    
    ПРИОРИТЕТ:
    1. Ако master_data.csv съществува и е актуален → използва го (БЪРЗО)
    2. Иначе → обработва Excel файловете поотделно (БАВНО)
    
    Параметри
    ---------
    data_dir : Path
        Директория с Excel файлове
    
    Връща
    ------
    pd.DataFrame
        Обединен DataFrame от всички файлове
    """
    master_file = data_dir / "master_data.csv"
    
    # Проверка за master_data.csv
    if master_file.exists():
        try:
            # Проверка дали е актуален
            master_mtime = master_file.stat().st_mtime
            
            # Намираме най-новия Excel файл
            excel_files = []
            for ext in config.EXCEL_EXTENSIONS:
                excel_files.extend(data_dir.glob(f"*{ext}"))
            
            excel_files = [f for f in excel_files if not f.name.startswith(config.TEMP_FILE_PREFIX)]
            
            is_fresh = True
            if excel_files:
                newest_excel_mtime = max(f.stat().st_mtime for f in excel_files)
                is_fresh = master_mtime > newest_excel_mtime
            
            if is_fresh:
                logger.info("✓ Зареждане от master_data.csv (БЪРЗО)")
                df = pd.read_csv(master_file)
                logger.info(f"✓ Заредени {len(df):,} реда от master_data.csv")
                return df
            else:
                logger.info("⚠ master_data.csv е остарял, обработвам Excel файлове...")
        
        except Exception as e:
            logger.warning(f"Грешка при четене на master_data.csv: {e}")
            logger.info("Обработвам Excel файлове директно...")
    logger.info(f"Сканиране за Excel файлове в {data_dir}")
    
    frames = []
    excel_files = [
        f for f in data_dir.glob("*.xlsx")
        if not f.name.startswith(config.TEMP_FILE_PREFIX)
    ]
    
    if not excel_files:
        logger.warning(f"Не са намерени Excel файлове (.xlsx) в {data_dir}")
        return pd.DataFrame()
    
    logger.info(f"Намерени {len(excel_files)} Excel файла")
    
    for filepath in sorted(excel_files):
        df = load_single_excel(filepath)
        if df is not None:
            frames.append(df)
    
    if not frames:
        logger.error("Нито един файл не е зареден успешно!")
        return pd.DataFrame()
    
    # Обединяване на всички DataFrame-и
    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"✓ Обединени {len(frames)} файла: {len(combined)} общо реда")
    
    return combined


@st.cache_data(show_spinner=False)
def prepare_data_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Подготвя данните за визуализация:
    - Добавя колона Molecule
    - Конвертира Units в числа
    - Премахва невалидни редове
    
    Параметри
    ---------
    df : pd.DataFrame
        Сурови данни
    
    Връща
    ------
    pd.DataFrame
        Обработени данни готови за визуализация
    """
    if df.empty:
        return df
    
    # Добавяне на молекули
    df = add_molecule_column(df)
    
    # Конвертиране на Units в числа
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce")
    
    # Премахване на редове без Units
    initial_len = len(df)
    df = df.dropna(subset=["Units"])
    removed = initial_len - len(df)
    if removed > 0:
        logger.info(f"Премахнати {removed} реда без валидни Units")
    
    return df


def get_period_sort_key(period: str) -> Tuple[int, int]:
    """
    Връща ключ за сортиране на периоди (Q1 2023, Jan 2024 и т.н.).
    Сортира хронологично: първо по година (числово), после по период.
    
    Параметри
    ---------
    period : str
        Период като текст (напр. "Q1 2023", "Jan 2024")
    
    Връща
    ------
    Tuple[int, int]
        (година_като_число, номер_на_период) за хронологично сортиране
    
    Примери
    -------
    >>> get_period_sort_key("Q1 2024")
    (2024, 1)
    >>> get_period_sort_key("Q4 2023")
    (2023, 4)
    >>> get_period_sort_key("Q1 2025")
    (2025, 1)
    """
    parts = str(period).split()
    
    # Извличаме годината (последната част) и конвертираме в int
    try:
        year = int(parts[-1]) if parts else 0
    except (ValueError, IndexError):
        year = 0
    
    token = parts[0] if parts else ""
    
    # Проверка за тримесечие (Q1, Q2, Q3, Q4)
    quarter_num = config.QUARTERS.get(token)
    if quarter_num:
        return (year, quarter_num)
    
    # Проверка за месец (Jan, Feb, Mar...)
    month_num = config.MONTHS.get(token)
    if month_num:
        return (year, month_num)
    
    # По подразбиране (невалидни периоди отиват в началото)
    return (year, 0)


def get_sorted_periods(df: pd.DataFrame, period_col: str = "Quarter") -> List[str]:
    """
    Връща сортиран списък от периоди.
    
    Параметри
    ---------
    df : pd.DataFrame
        DataFrame с данни
    period_col : str
        Име на колоната с периоди
    
    Връща
    ------
    List[str]
        Сортиран списък от периоди
    """
    if period_col not in df.columns:
        return []
    
    unique_periods = df[period_col].unique()
    return sorted(unique_periods, key=get_period_sort_key)


@st.cache_data(ttl=config.CACHE_TTL, show_spinner=False)
def load_data(data_dir: Path = config.DATA_DIR) -> pd.DataFrame:
    """
    Единна точка за зареждане на данни: четене на файлове + подготовка за визуализация.
    DataFrame се зарежда веднъж и се подава по референция към останалите модули.
    """
    df = load_all_excel_files(data_dir)
    return prepare_data_for_display(df)
