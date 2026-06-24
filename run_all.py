#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur principal — Lance toutes les étapes dans l'ordre.

Usage:
  python run_all.py           # Toutes les étapes
  python run_all.py --step 1  # Étape spécifique
  python run_all.py --skip-validation  # Sans Ollama
"""

import argparse
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "extraction"))

def banner(title, step, total=4):
    print(f"\n{'='*70}")
    print(f"  ÉTAPE {step}/{total}: {title}")
    print(f"{'='*70}")

def run_step1():
    banner("Scraping + Téléchargement des PDFs", 1)
    from extraction import scrape_and_download_module
    import importlib, importlib.util
    spec = importlib.util.spec_from_file_location(
        "step1", BASE_DIR / "extraction" / "01_scrape_and_download.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pdfs = mod.scrape_pdf_links()
    results = mod.download_pdfs(pdfs)
    import json
    manifest_path = BASE_DIR / "extraction" / "pdf_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results

def run_step2():
    banner("Extraction du texte des PDFs", 2)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "step2", BASE_DIR / "extraction" / "02_extract_text.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BASE_DIR = BASE_DIR / "extraction"
    mod.TEXT_DIR = BASE_DIR / "extraction" / "texts"
    mod.TEXT_DIR.mkdir(exist_ok=True)
    mod.process_all_pdfs()

def run_step3():
    banner("Parsing des entrées du dictionnaire", 3)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "step3", BASE_DIR / "extraction" / "03_parse_entries.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BASE_DIR = BASE_DIR / "extraction"
    mod.TEXT_DIR = BASE_DIR / "extraction" / "texts"
    mod.PARSED_DIR = BASE_DIR / "extraction" / "parsed"
    mod.PARSED_DIR.mkdir(exist_ok=True)
    mod.process_all_texts()

def run_step4(use_ollama=True):
    banner("Validation Ollama + Génération dico.json", 4)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "step4", BASE_DIR / "extraction" / "04_validate_and_build_json.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.BASE_DIR = BASE_DIR / "extraction"
    mod.PARSED_DIR = BASE_DIR / "extraction" / "parsed"
    mod.build_final_json(use_ollama_validation=use_ollama)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Li Ptit Moti Walon — Extraction complète")
    parser.add_argument("--step", type=int, choices=[1,2,3,4], help="Lancer seulement une étape")
    parser.add_argument("--skip-validation", action="store_true", help="Ignorer la validation Ollama")
    args = parser.parse_args()

    start = time.time()

    try:
        if args.step == 1 or args.step is None:
            run_step1()
        if args.step == 2 or args.step is None:
            run_step2()
        if args.step == 3 or args.step is None:
            run_step3()
        if args.step == 4 or args.step is None:
            run_step4(use_ollama=not args.skip_validation)
    except KeyboardInterrupt:
        print("\n⚠️  Interruption utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n🏁 Terminé en {elapsed/60:.1f} minutes")
