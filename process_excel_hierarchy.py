"""
Обработка на йерархични Excel файлове с фармацевтични данни.

Структура на Excel файловете:
- Колона A: Йерархия (Region → District/Brick → Category → Drug)
- Колони B-M+: Периоди (Q1 2023, Q2 2023... или Jan 2023, Feb 2023...)

Функцията разпознава различните типове редове, попълва регионите и районите
надолу с ffill(), премахва header/category редове и преобразува данните
в long format (дълъг формат) за анализ.
"""

import io
import pandas as pd
from pathlib import Path
from typing import Union, Optional
import logging

# Настройка на логване
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelProcessingError(Exception):
    """Грешка при обработка на Excel файл."""
    pass


def _detect_sheet_name(filepath: Union[str, bytes, io.BytesIO]) -> str:
    """
    Определя кой лист да се чете от Excel файла.
    Предпочита "Total Bricks" (пълни данни с райони) пред "Total Regiones".
    
    Параметри
    ---------
    filepath : str, bytes или BytesIO
        Път до Excel файла или BytesIO обект
    
    Връща
    ------
    str
        Име на листа за четене
    """
    try:
        xl = pd.ExcelFile(filepath)
        
        # Търсене на лист с "Bricks" в името (пълни данни)
        bricks_sheets = [s for s in xl.sheet_names if "Bricks" in s]
        if bricks_sheets:
            logger.info(f"Използван лист: {bricks_sheets[0]}")
            return bricks_sheets[0]
        
        # Fallback към първия лист
        logger.info(f"Използван лист: {xl.sheet_names[0]}")
        return xl.sheet_names[0]
    
    except Exception as e:
        raise ExcelProcessingError(f"Грешка при четене на Excel листове: {e}")


def _detect_period_columns(df: pd.DataFrame) -> list:
    """
    Разпознава колони с периоди (тримесечия или месеци).
    
    Параметри
    ---------
    df : pd.DataFrame
        DataFrame с данни
    
    Връща
    ------
    list
        Списък от колони с периоди
    """
    # Търсене на тримесечия (Q1 2023, Q2 2024 и т.н.)
    quarter_cols = [
        c for c in df.columns[1:]
        if "Q" in str(c) and any(year in str(c) for year in ["2023", "2024", "2025", "2026"])
    ]
    
    if quarter_cols:
        logger.info(f"Открити {len(quarter_cols)} тримесечия")
        return quarter_cols
    
    # Търсене на месеци (Jan 2023, Feb 2023 и т.н.)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_cols = [
        c for c in df.columns[1:]
        if any(month in str(c) for month in months)
    ]
    
    if month_cols:
        logger.info(f"Открити {len(month_cols)} месеца")
        return month_cols
    
    # Fallback: първите 12 колони след колона A
    logger.warning("Периодни колони не са разпознати автоматично, използвам първите 12 колони")
    return list(df.columns[1:13])


def _identify_row_types(col_a: pd.Series) -> dict:
    """
    Разпознава типовете редове в Excel файла.
    
    Типове редове:
    - Region: започва с "Region " (напр. "Region SOFIA")
    - District: формат (XX) NAME (напр. "(PH) BANSKO", "(PS) DRUZHBA")
    - Category: ATC код (напр. "R06A0 Antihistamines")
    - Drug: всичко останало (напр. "AERIUS", "ALLEGRA")
    
    Параметри
    ---------
    col_a : pd.Series
        Колона A от Excel (йерархията)
    
    Връща
    ------
    dict
        Речник с boolean маски за всеки тип ред
    """
    # Region редове: започват с "Region "
    is_region = col_a.str.startswith("Region ", na=False)
    
    # District/Brick редове: формат (XX) NAME
    is_district = col_a.str.match(r"^\([A-Z]{2}\)\s+", na=False)
    
    # Category редове: ATC код (напр. R06A0, B01C4)
    is_category = col_a.str.match(r"^[A-Z]\d{2}[A-Z]\d\s+", na=False)
    
    # Drug редове: всичко, което НЕ е Region, District или Category
    is_drug = ~is_region & ~is_district & ~is_category
    
    logger.info(
        f"Разпознати: {is_region.sum()} региона, "
        f"{is_district.sum()} района, "
        f"{is_category.sum()} категории, "
        f"{is_drug.sum()} медикамента"
    )
    
    return {
        "is_region": is_region,
        "is_district": is_district,
        "is_category": is_category,
        "is_drug": is_drug,
    }


def _fill_hierarchy(df: pd.DataFrame, row_types: dict) -> pd.DataFrame:
    """
    Попълва йерархията (Region, District, Drug_Name) надолу с ffill().
    
    Обяснение на ffill():
    - Всеки ред с Region задава нов регион
    - Всички следващи редове получават този регион, докато не се появи нов Region
    - Същото за District и Drug_Name
    
    Параметри
    ---------
    df : pd.DataFrame
        DataFrame с данни
    row_types : dict
        Типове редове от _identify_row_types()
    
    Връща
    ------
    pd.DataFrame
        DataFrame с попълнени колони Region, District, Drug_Name
    """
    col_a = df["col_a"].astype(str).str.strip()
    
    # Колона Region: запълни където е Region ред, после ffill()
    df["Region"] = col_a.where(row_types["is_region"])
    df["Region"] = df["Region"].ffill()  # Forward fill надолу
    
    # Колона District: запълни където е District ред, после ffill()
    df["District"] = col_a.where(row_types["is_district"])
    df["District"] = df["District"].ffill()
    
    # Колона Drug_Name: запълни където е Drug ИЛИ Category ред
    # Category редовете (ATC кодове) трябва да се запазват като Drug_Name
    df["Drug_Name"] = col_a.where(row_types["is_drug"] | row_types["is_category"])
    df["Drug_Name"] = df["Drug_Name"].ffill()
    
    return df


def process_pharma_excel(
    filepath: Union[str, bytes, io.BytesIO],
    output_path: Optional[str] = None,
    save: bool = True,
    sheet_name: Optional[str] = None,
) -> pd.DataFrame:
    """
    Обработва йерархичен фармацевтичен Excel файл.
    
    Стъпки на обработка:
    1. Чете Excel файла
    2. Разпознава колоните с периоди (Q1 2023, Jan 2024 и т.н.)
    3. Идентифицира типовете редове (Region, District, Category, Drug)
    4. Попълва йерархията надолу с ffill()
    5. Оставя само Drug редовете (data rows)
    6. Преобразува в long format с pd.melt()
    
    Параметри
    ----------
    filepath : str, bytes или BytesIO
        Път до Excel файла или BytesIO обект (от Streamlit upload)
    output_path : str, optional
        Път за запазване на CSV. Ако е None, запазва до файла с "_melted" суфикс.
    save : bool, default True
        Дали да запази резултата в CSV
    sheet_name : str, optional
        Име на листа за четене. Ако е None, избира автоматично "Total Bricks"
        или първия лист.
    
    Връща
    -------
    pd.DataFrame
        Long-format DataFrame с колони:
        - Region: Регион (напр. "Region SOFIA")
        - District: Район/Brick (напр. "(PH) BANSKO"), ако има
        - Drug_Name: Медикамент (напр. "AERIUS")
        - Quarter: Период (напр. "Q1 2023", "Jan 2024")
        - Units: Опаковки (число)
    
    Raises
    ------
    ExcelProcessingError
        При грешка в обработката на файла
    """
    try:
        # === 1. ПОДГОТОВКА НА ВХОДА ===
        # Ако е bytes, конвертираме в BytesIO
        if isinstance(filepath, bytes):
            filepath = io.BytesIO(filepath)
        
        # === 2. ОПРЕДЕЛЯНЕ НА ЛИСТА ===
        if sheet_name is None:
            sheet_name = _detect_sheet_name(filepath)
        
        # === 3. ЧЕТЕНЕ НА EXCEL ===
        logger.info(f"Четене на лист '{sheet_name}'...")
        df = pd.read_excel(filepath, header=0, sheet_name=sheet_name)
        
        if df.empty:
            raise ExcelProcessingError("Excel файлът е празен")
        
        # === 4. СТАНДАРТИЗИРАНЕ НА ПЪРВАТА КОЛОНА ===
        # Първата колона може да има различни имена/интервали
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "col_a"})
        
        # === 5. РАЗПОЗНАВАНЕ НА ПЕРИОДНИ КОЛОНИ ===
        period_cols = _detect_period_columns(df)
        
        if not period_cols:
            raise ExcelProcessingError("Не са открити колони с периоди")
        
        # === 6. ИДЕНТИФИКАЦИЯ НА ТИПОВЕ РЕДОВЕ ===
        col_a = df["col_a"].astype(str).str.strip()
        row_types = _identify_row_types(col_a)
        
        # === 7. ПОПЪЛВАНЕ НА ЙЕРАРХИЯТА ===
        df = _fill_hierarchy(df, row_types)
        
        # === 8. ФИЛТРИРАНЕ НА DRUG И CATEGORY РЕДОВЕ ===
        # Оставяме Drug редове (медикаменти) И Category редове (ATC класове с общи суми)
        df_clean = df[row_types["is_drug"] | row_types["is_category"]].copy()
        df_clean = df_clean.reset_index(drop=True)
        
        # Премахване на col_a (вече имаме Drug_Name)
        df_clean = df_clean.drop(columns=["col_a"])
        
        # === 9. ОБРАБОТКА НА DISTRICT КОЛОНАТА ===
        # Ако няма райони (Total Regiones лист), махаме District колоната
        if df_clean["District"].isna().all():
            df_clean = df_clean.drop(columns=["District"])
            id_vars = ["Region", "Drug_Name"]
            logger.info("Без райони (Total Regiones лист)")
        else:
            id_vars = ["Region", "District", "Drug_Name"]
            logger.info("С райони (Total Bricks лист)")
        
        # === 10. MELT (ПРЕОБРАЗУВАНЕ В LONG FORMAT) ===
        # От wide format (много колони с периоди) към long format (един ред на период)
        value_vars = [c for c in period_cols if c in df_clean.columns]
        
        df_melted = pd.melt(
            df_clean,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="Period",
            value_name="Units",
        )
        
        # === 11. ПОЧИСТВАНЕ НА ПЕРИОД КОЛОНАТА ===
        # Премахване на " Units" в края, ако има
        df_melted["Period"] = (
            df_melted["Period"]
            .astype(str)
            .str.replace(r"\s+Units$", "", regex=True)
            .str.strip()
        )
        
        # Преименуване на "Period" в "Quarter" (за съвместимост с app.py)
        df_melted = df_melted.rename(columns={"Period": "Quarter"})
        
        logger.info(f"✓ Обработени {len(df_melted)} реда")
        
        # === 12. ЗАПАЗВАНЕ В CSV (ОПЦИОНАЛНО) ===
        if save and isinstance(filepath, (str, Path)):
            if output_path is None:
                output_path = Path(filepath).parent / (Path(filepath).stem + "_melted.csv")
            df_melted.to_csv(output_path, index=False)
            logger.info(f"✓ Запазено в {output_path}")
        
        return df_melted
    
    except Exception as e:
        logger.error(f"Грешка при обработка: {e}")
        raise ExcelProcessingError(f"Не мога да обработя Excel файла: {e}")


# ============================================================================
# MAIN - ТЕСТВАНЕ НА СКРИПТА
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        # По подразбиране: обработва първия Excel файл в папката
        excel_files = list(Path(__file__).parent.glob("*.xlsx"))
        excel_files = [f for f in excel_files if not f.name.startswith(".~")]
        
        if excel_files:
            filepath = str(excel_files[0])
            print(f"\n{'='*60}")
            print(f"Обработка на: {filepath}")
            print(f"{'='*60}\n")
            
            result = process_pharma_excel(filepath)
            
            print("\nПърви 20 реда:")
            print(result.head(20))
            print(f"\nОбщо реда: {len(result)}")
            print(f"Колони: {list(result.columns)}")
        else:
            print("Използване: python process_excel_hierarchy.py <път_до_excel>")
            print("Или постави .xlsx файл в папката и пусни скрипта без аргументи.")
    else:
        filepath = sys.argv[1]
        print(f"\n{'='*60}")
        print(f"Обработка на: {filepath}")
        print(f"{'='*60}\n")
        
        result = process_pharma_excel(filepath)
        
        print("\nПърви 20 реда:")
        print(result.head(20))
        print(f"\nОбщо реда: {len(result)}")
