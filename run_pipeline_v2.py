"""
run_pipeline_v2.py — Orchestrateur complet de la re-extraction du Dictionnaire Liégeois.

Usage:
    python run_pipeline_v2.py [--test]   # mode test sur 3 PDFs pilotes
    python run_pipeline_v2.py            # mode complet sur les 74 PDFs

Sortie :
    dico.json               — base de données principale
    extraction/rapport_qualite.json    — stats qualité
    extraction/rapport_qualite.html    — rapport HTML de révision
"""

import fitz, json, sys, os, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ajouter le dossier extraction au path pour les imports
sys.path.insert(0, str(Path(__file__).parent / "extraction"))

from extract_v2        import extract_columns, col_left_x
from parse_entries_v2  import parse_column_entries
from correct_diacritics_v2 import correct_entry
from validate_dico     import validate, generate_html_report

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJ    = Path(__file__).parent
PDF_DIR = PROJ / "extraction" / "pdfs"
OUT_JSON     = PROJ / "dico.json"
OUT_RAPPORT  = PROJ / "extraction" / "rapport_qualite.json"
OUT_HTML     = PROJ / "extraction" / "rapport_qualite.html"

TEST_PDFS = ["tome2-08.pdf", "tome2-15.pdf", "tome3-07.pdf"]  # PDFs pilotes


# ---------------------------------------------------------------------------
# Extraction d'un fichier PDF
# ---------------------------------------------------------------------------
def process_pdf(pdf_path: Path) -> list[dict]:
    """Extrait toutes les entrées d'un PDF, les deux tomes."""
    # Déterminer le tome depuis le nom de fichier
    name  = pdf_path.stem          # ex: "tome2-08"
    parts = name.split("-")
    if len(parts) >= 2 and parts[0].startswith("tome"):
        try:
            tome = int(parts[0].replace("tome", ""))
        except ValueError:
            tome = 0
    else:
        tome = 0

    doc     = fitz.open(str(pdf_path))
    entries = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Numéro de page "réel" (approximatif — on compte depuis le début du PDF)
        real_page = page_num + 1

        # Extraction des deux colonnes
        col_left, col_right, _ = extract_columns(page)

        col_left_margin  = col_left_x(col_left)  if col_left  else 133.0
        col_right_margin = col_left_x(col_right) if col_right else 305.0

        # Parser chaque colonne
        left_entries  = parse_column_entries(
            col_left,  col_left_margin,  tome, real_page, pdf_path.name)
        right_entries = parse_column_entries(
            col_right, col_right_margin, tome, real_page, pdf_path.name)

        entries.extend(left_entries)
        entries.extend(right_entries)

    doc.close()
    return entries


# ---------------------------------------------------------------------------
# Pipeline complet
# ---------------------------------------------------------------------------
def run(test_mode: bool = False):
    """Lance l'extraction complète ou de test."""
    t_start = time.time()

    # Sélectionner les PDFs à traiter
    if test_mode:
        pdf_files = [PDF_DIR / n for n in TEST_PDFS if (PDF_DIR / n).exists()]
        print(f"=== MODE TEST : {len(pdf_files)} PDFs ===")
    else:
        # Ne traiter que les parties du dictionnaire principal
        raw_pdf_files = sorted(PDF_DIR.glob("tome*.pdf"))
        pdf_files = []
        for pdf_path in raw_pdf_files:
            name = pdf_path.stem
            parts = name.split("-")
            if len(parts) >= 2 and parts[0].startswith("tome"):
                try:
                    tome = int(parts[0].replace("tome", ""))
                    num = int(parts[1])
                    # Tome 2 : de tome2-07 (A) à tome2-31 (Z)
                    # Tome 3 : de tome3-06 (A) à tome3-31 (Z)
                    if (tome == 2 and 7 <= num <= 31) or (tome == 3 and 6 <= num <= 31):
                        pdf_files.append(pdf_path)
                except ValueError:
                    pass
        print(f"=== MODE COMPLET : {len(pdf_files)} PDFs (sur {len(raw_pdf_files)} trouvés) ===")

    if not pdf_files:
        print("ERREUR : Aucun PDF trouvé dans", PDF_DIR)
        return

    all_entries = []
    for i, pdf_path in enumerate(pdf_files):
        print(f"[{i+1:3d}/{len(pdf_files)}] {pdf_path.name} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            entries = process_pdf(pdf_path)
            all_entries.extend(entries)
            dt = time.time() - t0
            print(f"{len(entries):4d} entrées  ({dt:.1f}s)")
        except Exception as e:
            print(f"ERREUR: {e}")

    print(f"\n--- Extraction terminée : {len(all_entries)} entrées brutes ---")

    # Correction des diacritiques å
    print("Application des corrections å ...")
    all_entries = [correct_entry(e) for e in all_entries]

    # Tri : tome → page → mot
    all_entries.sort(key=lambda e: (
        e.get("tome", 0),
        e.get("page", 0),
        e.get("word", "").lower()
    ))

    # Dédoublonnage (même mot + même tome + même page)
    seen = set()
    unique_entries = []
    for e in all_entries:
        key = (e.get("word", "").lower().strip(),
               e.get("tome", 0),
               e.get("page", 0))
        if key not in seen:
            seen.add(key)
            unique_entries.append(e)
    print(f"Après dédoublonnage : {len(unique_entries)} entrées")

    # Sauvegarde
    suffix = "_test" if test_mode else ""
    out_path = PROJ / f"dico{suffix}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique_entries, f, ensure_ascii=False, indent=2)
    print(f"Sauvegardé : {out_path}")
    
    # Également sauvegarder au format JS (dico.js) pour support file:// hors ligne
    out_path_js = PROJ / f"dico{suffix}.js"
    with open(out_path_js, "w", encoding="utf-8") as f:
        f.write("window.dictionaryData = ")
        json.dump(unique_entries, f, ensure_ascii=False)
        f.write(";\n")
    print(f"Sauvegardé format JS : {out_path_js}")

    # Validation qualité
    print("Validation qualité ...")
    stats = validate(unique_entries)
    rapport_path = PROJ / "extraction" / f"rapport_qualite{suffix}.json"
    html_path    = PROJ / "extraction" / f"rapport_qualite{suffix}.html"
    with open(rapport_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    generate_html_report(unique_entries, stats, html_path)

    # Résumé
    dt_total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ FINAL")
    print(f"{'='*60}")
    print(f"  PDFs traités    : {len(pdf_files)}")
    print(f"  Entrées totales : {len(unique_entries)}")
    print(f"  Qualité estimée : {stats.get('quality_pct', '?')}%")
    print(f"  å corrigés auto : {stats.get('a_ring_corrected', 0)}")
    print(f"  À réviser       : {stats.get('needs_review', 0)}")
    print(f"  Mots vides      : {stats.get('word_empty', 0)}")
    print(f"  Defs vides      : {stats.get('def_empty', 0)}")
    print(f"  Durée totale    : {dt_total:.1f}s")
    print(f"\n  -> Rapport HTML  : {html_path}")
    print(f"  -> dico JSON     : {out_path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test = "--test" in sys.argv
    run(test_mode=test)
