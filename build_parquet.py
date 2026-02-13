"""
Скрипт за еднократно конвертиране на Excel → Parquet.
Пусни: python build_parquet.py

След като създаде pharma_data.parquet, приложението ще зарежда от него
(2-5x по-бързо, по-малко RAM). Прегенерирай след промяна на Excel файловете.
"""
import sys
from pathlib import Path

# Добавяме project root към path
sys.path.insert(0, str(Path(__file__).parent))

import config
import pandas as pd
from process_excel_hierarchy import process_pharma_excel
from drug_molecules import add_molecule_column


def load_all_excel_raw(data_dir: Path) -> pd.DataFrame:
    """Зарежда всички Excel без Streamlit cache."""
    frames = []
    team_folders = getattr(config, "TEAM_FOLDERS", ["Team 1", "Team 2", "Team 3"])
    for team_name in team_folders:
        team_dir = data_dir / team_name
        if team_dir.is_dir():
            for ext in ["*.xlsx", "*.xls"]:
                for filepath in sorted(team_dir.glob(ext)):
                    if filepath.name.startswith(getattr(config, "TEMP_FILE_PREFIX", ".~")):
                        continue
                    try:
                        df = process_pharma_excel(str(filepath), save=False, sheet_name=None)
                        if df is not None and not df.empty:
                            source = filepath.stem.replace(" Total Q", "").replace(" Total", "").strip()
                            df["Source"] = source
                            df["Team"] = team_name
                            frames.append(df)
                            print(f"  OK {filepath.name}")
                    except Exception as e:
                        print(f"  ERR {filepath.name}: {e}")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Подготовка като в data_processing."""
    if df.empty:
        return df
    if "Region" in df.columns:
        df["Region"] = df["Region"].astype(str).str.replace(r"^Region\s+", "", regex=True).str.strip()
    try:
        if "Drug_Name" in df.columns:
            df = add_molecule_column(df)
        else:
            df["Molecule"] = "Other"
    except Exception:
        df["Molecule"] = "Other"
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce").astype("float32")
    df = df.dropna(subset=["Units"])
    for col in ["Region", "Drug_Name", "Quarter", "Source", "District", "Molecule"]:
        if col in df.columns and df[col].dtype == "object":
            df[col] = df[col].astype("category")
    return df


def main():
    data_dir = config.DATA_DIR
    out_path = data_dir / "pharma_data.parquet"
    print("Зареждане на Excel файлове...")
    df = load_all_excel_raw(data_dir)
    if df.empty:
        print("Няма данни! Провери Team 1/, Team 2/, Team 3/")
        return 1
    print(f"Обработка на {len(df):,} реда...")
    df = prepare(df)
    print(f"Запис в {out_path}...")
    df.to_parquet(out_path, index=False, compression="snappy")
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"Done! {out_path} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
