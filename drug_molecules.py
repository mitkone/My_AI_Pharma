"""
Drug name → molecule (active ingredient) mapping.
Used for filtering by molecule in the Pharma Data Viz app.
Sources: EMA, FDA, pharmaceutical databases.
Loads drug_molecules_cache.json for user-added / auto-discovered mappings.
"""

import json
import os
from pathlib import Path

_CACHE_PATH = Path(__file__).parent / "drug_molecules_cache.json"

# Antihistamines (R06A)
ANTIHISTAMINES = {
    "Desloratadine": ["AERIUS", "DESLARIS", "DESLORATADINE SOPH", "DESYBEL", "ALLERGOSAN"],
    "Bilastine": ["BILERGIA", "BILASTINE TEVA"],
    "Levocetirizine": ["XYZAL", "XYZAL BTE>>", "XYZAL IVP>>", "ZENARO", "ZENARO BTE >>", "KSIVOZAN", "ROLETRA", "XALLERGAN"],
    "Cetirizine": ["ZYRTEC", "ZYRTEC BTE>>", "CETIRISTAD"],
    "Fexofenadine": ["ALLEGRA", "ALLEGRA BTE>>", "ALLEZODAC", "ALLEZODAC BTE>>", "EFESTAD", "EWOFEX"],
    "Loratadine": ["LORANO ACUT", "LORATADIN SOPHARMA", "LORATADIN UHA", "CLARITINE", "TALERT", "ALLERTESIN"],
    "Rupatadine": ["RUPAFIN"],
    "Ebastine": ["FORTECAL", "FORTECAL BTE>>"],
}

# Valsartan / ARB products (C09C)
VALSARTAN = {
    "Valsartan": ["VALSAVIL", "VALSARTAN", "DIOVAN", "DIOVAN BTE>>"],
    "Valsartan/HCT": ["VALSAVIL COMP", "CO-DIOVAN", "CO-DIOVAN BTE>>", "CO-HYPERTONIC"],
    "Valsartan/Amlodipine": ["VALSAVIL AM", "EXFORGE", "AMLODIPINE/VALSART", "AMLODIPINE/VALSARTAN"],
    "Valsartan/Amlodipine/HCT": ["VALSAVIL AM TRIO", "EXFORGE HCT"],
    "Candesartan": ["ACTELSAR", "ATACAND", "ATACAND BTE>>", "CANDECARD", "CANDESARTAN ACTAV", "CANDESARTAN ECOPHA", "CANDESTAR", "CANTAB"],
    "Candesartan/HCT": ["ACTELSAR HCT", "CANDESARTAN HCT", "CANDESTAR H", "CANTAB PLUS", "COCANDESARGEN"],
    "Irbesartan": ["IRBEC", "IRBESAN", "IRBESARTAN ACCORD", "IRBESSO", "IRPRESTAN"],
    "Irbesartan/HCT": ["CO-IRBEC", "CO-IRBESAN", "CO-IRBESSO"],
    "Losartan": ["LORISTA", "COOLSART"],
    "Losartan/HCT": ["LORISTA H", "LORISTA HD", "LORISTA HL", "LOSARCON-CO"],
    "Olmesartan/Amlodipine": ["OLMEDIPIN", "OLMESARTAN MED/AML", "OLMESTA A", "OLMEZIDE AM"],
    "Olmesartan/Amlodipine/HCT": ["OLMESTA A PLUS", "OLMEZIDE TRIO"],
    "Telmisartan/HCT": ["CO-TELSART"],
    "Perindopril/Amlodipine": ["DIPPERAM", "REPIDO AM", "BILAMCAR"],
    "Perindopril/Amlodipine/HCT": ["DIPPERAM HCT"],
    "Amlodipine": ["AMOLCON"],  # Чист Amlodipine (не ARB, но в Valsavil AM файла)
}

# Cilostazol (B01AC) - antiplatelet, PDE3 inhibitor
CILOSTAZOL = {
    "Cilostazol": ["CILOSTAZOL", "CILOSTAZOL SANDOZ", "CILOSTAZOL STADA", "PLETAL", "LOSTRAZIN", "TROMBYE", "ILOMEDIN", "THROMBOREDUCTIN"],
}

# Nasal corticosteroids (R01AD)
NASAL_CORT = {
    "Fluticasone": ["FLONASE", "AVAMYS", "FLUTICASONE", "FLIXONASE", "FLIXONASE BTE>>", "BLOCTIMO", "DYMISTA", "RHINOSTAD"],
    "Mometasone": ["NASONEX", "NASONEX BTE>>", "MOMETASONE", "MOMANOSE", "NASOSTAD"],
    "Budesonide": ["RHINOCORT", "BUDESONIDE", "ETACID", "KALMENTE"],
}

# Nootropics (N06BX)
NOOTROPICS = {
    "Piracetam": ["NOOTROPIL", "NOOTROPIL BTE>>", "PIRACETAM", "PIRACETAM ABR", "PIRACETAM AL", "PIRACETAM C+X", "PIRACETAM DS", "LUCETAM", "DINAGEN", "PHEZAM", "PYRAMEM B&R", "PYRAMEM B/D", "PYRAMINOL"],
    "Vinpocetine": ["CAVINTON", "CAVINTON FORTE", "VINPOCETINE", "VINPEX", "VICETIN"],
    "Cinnarizine": ["CINNARIZINE", "STUGERON"],
    "Ginkgo biloba": ["TANAKAN", "GINKGO"],
}

# Antiplatelets P2Y12 (B01AC) - Kaldera SPM
ANTIPLATELETS = {
    "Ticagrelor": ["BRILIQUE", "KALDERA SPM", "TICAGRELOR TEVA", "QYDAXER", "BEWIM"],
    "Clopidogrel": ["CLOPIDOGREL ACCORD", "CLOPIDOGREL ATV", "CLOPIDOGREL ECOPH", "EGITROMB", "FLUIDORO", "GLOPENEL", "PLAQUEX", "PLATEL", "PLAVIX"],
    "Prasugrel": ["EFIENT", "PRASUGREL TEVA"],
}

# Statins (C10AA) - Lipocante, Crestor, etc.
STATINS = {
    "Pitavastatin": ["LIPOCANTE", "LIVALO", "LIVALO BTE>>", "PITAVASTATIN", "PITAVAST", "PITAVIA"],
    "Atorvastatin": [
        "LIPITOR", "ATORVASTATIN", "ATORVA", "TORVAST", "TULIP", "ATEROSTAD", "ATORGEN",
        "ATORIS", "ATORIS BTE>>", "ATORVASTATIN ECOPH", "ATORVIN", "ATORVISTAT K", "AVANOR", "CALIPRA", "ACTALIPID",
    ],
    "Rosuvastatin": ["CRESTOR", "CRESTOR BTE>>", "CRESTOR IVP>>", "ROSUVASTATIN", "ROSUVA", "ROZAVEL", "HOLETAR", "HOLLESTA", "ROSISTAT", "ROSTTA", "ROSUCARD", "ROSUCARD BTE>>", "ROSUVASTATIN MYLAN", "ROMAZIC", "ROPUIDO"],
    "Simvastatin": ["ZOCOR", "SIMVASTATIN", "SIMVA", "SIMVACOR", "NEOROSO", "NEOSIMVA"],
    "Pravastatin": ["PRAVACHOL", "PRAVASTATIN", "PRATIN"],
    "Fluvastatin": ["LESCOL", "LESCOL XL", "FLUVASTATIN"],
    "Lovastatin": ["MEVACOR", "LOVASTATIN"],
}


def _load_cache():
    """Load user cache of drug→molecule mappings."""
    if _CACHE_PATH.exists():
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    """Save cache to JSON."""
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _norm(s: str) -> str:
    return " ".join(s.strip().upper().split())


# Merge built-in mappings
DRUG_TO_MOLECULE = {}
for molecule, drugs in ANTIHISTAMINES.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in VALSARTAN.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in STATINS.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in CILOSTAZOL.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in NASAL_CORT.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in NOOTROPICS.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule
for molecule, drugs in ANTIPLATELETS.items():
    for d in drugs:
        DRUG_TO_MOLECULE[_norm(d)] = molecule

# Load user cache
DRUG_TO_MOLECULE.update(_load_cache())


def get_molecule(drug_name: str, use_cache: bool = True) -> str:
    """Return molecule for drug, or 'Other' if unknown."""
    import math

    if drug_name is None or (isinstance(drug_name, float) and math.isnan(drug_name)):
        return "Other"
    key = _norm(str(drug_name))
    mol = DRUG_TO_MOLECULE.get(key)
    if mol:
        return mol
    if use_cache:
        cache = _load_cache()
        return cache.get(key, "Other")
    return "Other"


def add_drug_to_cache(drug_name: str, molecule: str):
    """Add drug→molecule to cache (for new drugs)."""
    key = _norm(str(drug_name))
    if not key:
        return
    cache = _load_cache()
    cache[key] = molecule
    _save_cache(cache)
    DRUG_TO_MOLECULE[key] = molecule


def add_molecule_column(df, drug_col: str = "Drug_Name"):
    """Add Molecule column to dataframe."""
    df = df.copy()
    df["Molecule"] = df[drug_col].apply(get_molecule)
    return df
