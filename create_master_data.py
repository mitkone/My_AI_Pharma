"""
Създава master_data.csv - централна база данни от всички Excel файлове.

Този скрипт:
1. Чете всички Excel файлове от папката
2. Обработва йерархията (Region → Drug → District)
3. Използва ffill() за mapping
4. Конвертира в Long Format
5. Запазва в master_data.csv като "база данни"
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
import logging
from process_excel_hierarchy import process_pharma_excel, ExcelProcessingError
from data_processing import extract_source_name

# Настройка на логване
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def identify_row_types(df: pd.DataFrame, col_a: pd.Series) -> Dict[str, pd.Series]:
    """
    Robust идентифициране на типове редове в йерархията.
    
    Йерархия:
    - Region: започва с "Region" или е главни букви без цифри
    - Category: ATC код формат (напр. "C10A1 STATINS")
    - Drug: име на медикамент (главни букви, може да има цифри в края)
    - District: име на район/град (смесени/главни букви)
    
    Параметри
    ---------
    df : pd.DataFrame
        Пълен DataFrame
    col_a : pd.Series
        Колона A с йерархичните данни
    
    Връща
    ------
    Dict[str, pd.Series]
        Речник с boolean серии за всеки тип ред
    """
    # 1. REGION: Започва с "Region" или е в списък от познати региони
    is_region = col_a.str.startswith("Region", na=False)
    
    # 2. CATEGORY: ATC код формат (буква + цифри + букви + описание)
    # Примери: "C10A1 STATINS", "R06A0 ANTIHISTAMINES"
    is_category = col_a.apply(lambda x: (
        isinstance(x, str) and
        len(x.split()) >= 2 and
        len(x.split()[0]) >= 4 and
        len(x.split()[0]) <= 7 and
        x.split()[0][0].isalpha() and
        any(c.isdigit() for c in x.split()[0]) and
        x.split()[0].isupper() and
        x not in ["GRAND TOTAL", "Grand Total"]
    ))
    
    # 3. DRUG: Име на медикамент
    # - Главни букви
    # - Може да има цифри в края (напр. AERIUS 5MG)
    # - НЕ е Region, Category или известни header думи
    header_keywords = ["GRAND TOTAL", "Grand Total", "TOTAL", "Total"]
    is_drug = col_a.apply(lambda x: (
        isinstance(x, str) and
        x not in header_keywords and
        not x.startswith("Region") and
        x.isupper() and
        not is_category.loc[col_a == x].any() if x in col_a.values else False
    ))
    
    # 4. DISTRICT: Останалите валидни стрингове (може да са смесени букви)
    is_district = (
        col_a.notna() &
        ~is_region &
        ~is_category &
        ~is_drug &
        ~col_a.isin(header_keywords)
    )
    
    return {
        "is_region": is_region,
        "is_category": is_category,
        "is_drug": is_drug,
        "is_district": is_district
    }


def robust_clean_excel(
    filepath: Path,
    source_name: str
) -> pd.DataFrame:
    """
    Robust почистване и трансформация на Excel файл.
    
    Стъпки:
    1. Идентифициране на йерархията в Column A
    2. ffill() за mapping на District → Drug → Region
    3. Wide to Long format conversion
    4. Валидация и почистване
    
    Параметри
    ---------
    filepath : Path
        Път до Excel файла
    source_name : str
        Име на източника (категория)
    
    Връща
    ------
    pd.DataFrame
        Почистен DataFrame в Long Format с колони:
        Region, Drug_Name, District, Period, Units, Source
    """
    try:
        logger.info(f"Обработка: {filepath.name}")
        
        # Използваме съществуващата функция за първоначална обработка
        df_melted = process_pharma_excel(str(filepath), save=False, sheet_name=None)
        
        if df_melted.empty:
            logger.warning(f"Празен резултат за {filepath.name}")
            return pd.DataFrame()
        
        # Добавяме Source колона
        df_melted["Source"] = source_name
        
        # Валидация и почистване
        # 1. Премахваме редове без Units
        initial_len = len(df_melted)
        df_melted = df_melted[df_melted["Units"].notna()].copy()
        removed = initial_len - len(df_melted)
        if removed > 0:
            logger.info(f"  Премахнати {removed} реда без продажби")
        
        # 2. Конвертираме Units в числа
        df_melted["Units"] = pd.to_numeric(df_melted["Units"], errors="coerce")
        df_melted = df_melted[df_melted["Units"] > 0].copy()
        
        # 3. Почистваме празни стойности в ключови колони
        required_cols = ["Region", "Drug_Name"]
        for col in required_cols:
            if col in df_melted.columns:
                df_melted = df_melted[df_melted[col].notna()].copy()
        
        # 4. Стандартизиране на имена
        for col in ["Region", "Drug_Name", "District"]:
            if col in df_melted.columns:
                df_melted[col] = df_melted[col].astype(str).str.strip()
        
        # 5. Премахваме дупликати
        # Определяме колоната с периодите (Quarter или Month)
        period_col = "Quarter" if "Quarter" in df_melted.columns else "Month"
        
        if period_col in df_melted.columns:
            before_dedup = len(df_melted)
            subset_cols = ["Region", "Drug_Name", "Source", period_col]
            if "District" in df_melted.columns:
                subset_cols.append("District")
            
            df_melted = df_melted.drop_duplicates(
                subset=subset_cols,
                keep="first"
            )
            dedup_removed = before_dedup - len(df_melted)
            if dedup_removed > 0:
                logger.warning(f"  Премахнати {dedup_removed} дупликата")
        
        logger.info(f"  Успешно: {len(df_melted)} реда")
        return df_melted
    
    except Exception as e:
        logger.error(f"Грешка при обработка на {filepath.name}: {e}")
        return pd.DataFrame()


def create_master_data(
    data_dir: Path = None,
    output_file: str = "master_data.csv"
) -> pd.DataFrame:
    """
    Създава master_data.csv от всички Excel файлове.
    
    Параметри
    ---------
    data_dir : Path, optional
        Директория с Excel файлове (по подразбиране текущата)
    output_file : str
        Име на изходния файл
    
    Връща
    ------
    pd.DataFrame
        Обединен DataFrame от всички файлове
    """
    if data_dir is None:
        data_dir = Path(__file__).parent
    
    logger.info("="*70)
    logger.info("СЪЗДАВАНЕ НА MASTER DATA")
    logger.info("="*70)
    
    # Намираме всички Excel файлове
    excel_files = []
    for ext in [".xlsx", ".xls"]:
        excel_files.extend(data_dir.glob(f"*{ext}"))
    
    # Филтрираме временни файлове
    excel_files = [f for f in excel_files if not f.name.startswith(".~") and not f.name.startswith("~$")]
    
    if not excel_files:
        logger.error("Няма намерени Excel файлове!")
        return pd.DataFrame()
    
    logger.info(f"Намерени {len(excel_files)} файла")
    
    # Обработваме всеки файл
    all_data = []
    successful = 0
    failed = 0
    
    for filepath in excel_files:
        source_name = extract_source_name(filepath.name)
        
        try:
            df_clean = robust_clean_excel(filepath, source_name)
            
            if not df_clean.empty:
                all_data.append(df_clean)
                successful += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"FAILED: {filepath.name} - {e}")
            failed += 1
    
    # Обединяваме всички данни
    if not all_data:
        logger.error("Няма успешно обработени файлове!")
        return pd.DataFrame()
    
    logger.info(f"\n{'='*70}")
    logger.info(f"РЕЗУЛТАТ: {successful} успешни, {failed} неуспешни")
    logger.info(f"{'='*70}")
    
    df_master = pd.concat(all_data, ignore_index=True)
    
    # Финални проверки
    logger.info(f"\nОБЩО РЕДОВЕ: {len(df_master):,}")
    logger.info(f"ИЗТОЧНИЦИ: {df_master['Source'].nunique()}")
    logger.info(f"РЕГИОНИ: {df_master['Region'].nunique()}")
    logger.info(f"МЕДИКАМЕНТИ: {df_master['Drug_Name'].nunique()}")
    
    # Периоди (Quarter или Month)
    if "Quarter" in df_master.columns:
        logger.info(f"ТРИМЕСЕЧИЯ: {df_master['Quarter'].nunique()}")
    if "Month" in df_master.columns:
        logger.info(f"МЕСЕЦИ: {df_master['Month'].nunique()}")
    
    # Запазваме в CSV
    output_path = data_dir / output_file
    df_master.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"\n✓ Запазено в: {output_path}")
    logger.info(f"  Размер: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return df_master


def is_master_data_fresh(
    data_dir: Path = None,
    master_file: str = "master_data.csv"
) -> bool:
    """
    Проверява дали master_data.csv съществува и е актуален.
    
    Актуален = по-нов от всички Excel файлове
    
    Параметри
    ---------
    data_dir : Path, optional
        Директория с файлове
    master_file : str
        Име на master файла
    
    Връща
    ------
    bool
        True ако master_data.csv е актуален
    """
    if data_dir is None:
        data_dir = Path(__file__).parent
    
    master_path = data_dir / master_file
    
    # Проверка дали съществува
    if not master_path.exists():
        return False
    
    master_mtime = master_path.stat().st_mtime
    
    # Проверка дали е по-нов от всички Excel файлове
    excel_files = []
    for ext in [".xlsx", ".xls"]:
        excel_files.extend(data_dir.glob(f"*{ext}"))
    
    excel_files = [f for f in excel_files if not f.name.startswith(".~") and not f.name.startswith("~$")]
    
    for excel_file in excel_files:
        if excel_file.stat().st_mtime > master_mtime:
            return False  # Excel файлът е по-нов
    
    return True


if __name__ == "__main__":
    # Създаване на master_data.csv
    df = create_master_data()
    
    if not df.empty:
        print("\n" + "="*70)
        print("УСПЕШНО! master_data.csv е готов за използване")
        print("="*70)
