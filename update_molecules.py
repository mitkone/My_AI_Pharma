"""
Скрипт за сканиране на всички Excel файлове в папката,
събиране на уникални препарати и определяне на молекулите.
Пускай: python update_molecules.py
"""
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from process_excel_hierarchy import process_pharma_excel
from drug_molecules import get_molecule, add_drug_to_cache, _norm

EXCEL_DIR = Path(__file__).parent


def scan_all_excels():
    """Сканира всички .xlsx файлове и връща { filename: [drug_names] }."""
    results = {}
    for fpath in sorted(EXCEL_DIR.glob("*.xlsx")):
        if fpath.name.startswith(".~"):
            continue
        try:
            df = process_pharma_excel(str(fpath), save=False, sheet_name=None)
            drugs = [d for d in df["Drug_Name"].unique() if d and str(d).strip() and str(d) != "Grand Total"]
            results[fpath.name] = sorted(set(drugs))
        except Exception as e:
            results[fpath.name] = []
            print(f"  WARN {fpath.name}: {e}")
    return results


def main():
    print("Scanning Excel files in", EXCEL_DIR)
    print("-" * 50)
    all_drugs = set()
    file_to_drugs = scan_all_excels()

    for fname, drugs in file_to_drugs.items():
        print(f"\n{fname}: {len(drugs)} products")
        all_drugs.update(drugs)

    unknown = []
    known = []
    for d in sorted(all_drugs):
        mol = get_molecule(d)
        if mol == "Other":
            unknown.append(d)
        else:
            known.append((d, mol))

    print("\n" + "=" * 50)
    print(f"Known molecules: {len(known)}")
    for d, mol in known[:20]:
        print(f"   {d} -> {mol}")
    if len(known) > 20:
        print(f"   ... and {len(known) - 20} more")

    print(f"\nUnknown (Other): {len(unknown)}")
    for d in unknown[:30]:
        print(f"   {d}")
    if len(unknown) > 30:
        print(f"   ... and {len(unknown) - 30} more")

    print("\nTo add molecule: use app sidebar 'Dobavi molekula' or add_drug_to_cache()")
    print("   or: python -c \"from drug_molecules import add_drug_to_cache; add_drug_to_cache('DRUG_NAME', 'MOLECULE')\"")
    return file_to_drugs, known, unknown


if __name__ == "__main__":
    main()
