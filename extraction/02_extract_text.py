#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Étape 2 : Extraction du texte brut depuis chaque PDF.
Utilise PyMuPDF (fitz) en priorité, avec fallback sur pdfplumber.
Préserve tous les accents et caractères spéciaux wallons (UTF-8).
"""

import json
import os
import re
import sys
from pathlib import Path

# Tentative d'import PyMuPDF
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("⚠️  PyMuPDF non disponible")

# Tentative d'import pdfplumber
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("⚠️  pdfplumber non disponible")

if not HAS_FITZ and not HAS_PDFPLUMBER:
    print("❌ Aucune bibliothèque PDF disponible. Installez: pip install pymupdf pdfplumber")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
TEXT_DIR = BASE_DIR / "texts"
TEXT_DIR.mkdir(exist_ok=True)


def detect_pdf_type(pdf_path: Path) -> str:
    """Détecte si le PDF contient du texte natif ou des images scannées."""
    if not HAS_FITZ:
        return "unknown"

    try:
        doc = fitz.open(str(pdf_path))
        total_chars = 0
        total_images = 0

        for page_num in range(min(3, len(doc))):  # Vérifie les 3 premières pages
            page = doc[page_num]
            text = page.get_text()
            total_chars += len(text.strip())
            total_images += len(page.get_images())

        doc.close()

        if total_chars > 100:
            return "native_text"
        elif total_images > 0:
            return "scanned_image"
        else:
            return "empty"
    except Exception as e:
        return f"error: {e}"


def extract_with_fitz(pdf_path: Path) -> list[dict]:
    """Extraction page par page avec PyMuPDF — préserve l'encodage UTF-8."""
    pages = []
    try:
        doc = fitz.open(str(pdf_path))
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")  # Mode texte natif UTF-8
            if text.strip():
                pages.append({
                    "page": page_num,
                    "text": text,
                    "method": "fitz"
                })
        doc.close()
    except Exception as e:
        print(f"    ⚠️  Erreur fitz: {e}")
    return pages


def extract_with_pdfplumber(pdf_path: Path) -> list[dict]:
    """Extraction avec pdfplumber (fallback)."""
    pages = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    pages.append({
                        "page": page_num,
                        "text": text,
                        "method": "pdfplumber"
                    })
    except Exception as e:
        print(f"    ⚠️  Erreur pdfplumber: {e}")
    return pages


def extract_pdf(pdf_path: Path) -> dict:
    """Extrait le texte d'un PDF avec la meilleure méthode disponible."""
    pdf_type = detect_pdf_type(pdf_path)
    result = {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "type": pdf_type,
        "pages": [],
        "total_chars": 0,
        "success": False
    }

    if pdf_type == "scanned_image":
        print(f"    ⚠️  PDF scanné (image) — texte non extractible sans OCR")
        return result

    # Essai avec PyMuPDF
    if HAS_FITZ:
        pages = extract_with_fitz(pdf_path)
        if pages:
            result["pages"] = pages
            result["total_chars"] = sum(len(p["text"]) for p in pages)
            result["success"] = True
            return result

    # Fallback sur pdfplumber
    if HAS_PDFPLUMBER:
        pages = extract_with_pdfplumber(pdf_path)
        if pages:
            result["pages"] = pages
            result["total_chars"] = sum(len(p["text"]) for p in pages)
            result["success"] = True
            return result

    return result


def process_all_pdfs():
    manifest_path = BASE_DIR / "pdf_manifest.json"
    if not manifest_path.exists():
        print("❌ Manifest non trouvé. Exécutez d'abord 01_scrape_and_download.py")
        sys.exit(1)

    with open(manifest_path, encoding="utf-8") as f:
        pdf_list = json.load(f)

    results = []
    scanned_pdfs = []

    for i, pdf_info in enumerate(pdf_list, 1):
        if not pdf_info.get("downloaded") or not pdf_info.get("local_path"):
            print(f"  ⏭️  [{i}/{len(pdf_list)}] Ignoré (non téléchargé): {pdf_info['filename']}")
            continue

        pdf_path = Path(pdf_info["local_path"])
        if not pdf_path.exists():
            print(f"  ❌ [{i}/{len(pdf_list)}] Fichier introuvable: {pdf_path}")
            continue

        print(f"  📖 [{i}/{len(pdf_list)}] Extraction: {pdf_path.name}")
        extraction = extract_pdf(pdf_path)
        extraction["source_page"] = pdf_info.get("source_page", "unknown")
        extraction["label"] = pdf_info.get("label", "")

        print(f"     Type: {extraction['type']} | Caractères: {extraction['total_chars']:,} | Pages: {len(extraction['pages'])}")

        # Sauvegarde texte brut
        if extraction["success"]:
            text_file = TEXT_DIR / f"{pdf_path.stem}.txt"
            full_text = "\n\n--- PAGE {} ---\n\n".join([""])
            all_text = ""
            for p in extraction["pages"]:
                all_text += f"\n\n--- PAGE {p['page']} ---\n\n{p['text']}"

            with open(text_file, "w", encoding="utf-8") as f:
                f.write(all_text)
            print(f"     💾 Texte sauvé: {text_file.name}")

        if extraction["type"] == "scanned_image":
            scanned_pdfs.append(pdf_path.name)

        # On ne stocke pas le texte complet dans le JSON pour économiser la mémoire
        extraction_summary = {
            "filename": extraction["filename"],
            "source_page": extraction["source_page"],
            "label": extraction["label"],
            "type": extraction["type"],
            "total_chars": extraction["total_chars"],
            "num_pages": len(extraction["pages"]),
            "success": extraction["success"],
            "text_file": str(TEXT_DIR / f"{pdf_path.stem}.txt") if extraction["success"] else None
        }
        results.append(extraction_summary)

    # Rapport final
    summary_path = BASE_DIR / "extraction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["success"])
    print(f"\n📊 Résultats:")
    print(f"   ✅ PDFs extraits avec succès: {ok}/{len(results)}")
    if scanned_pdfs:
        print(f"   ⚠️  PDFs scannés (OCR requis): {len(scanned_pdfs)}")
        for name in scanned_pdfs:
            print(f"      - {name}")
    print(f"   📋 Résumé: {summary_path}")


if __name__ == "__main__":
    print("=" * 70)
    print("  LI PTIT MOTI WALON — Étape 2 : Extraction du texte")
    print("=" * 70)
    process_all_pdfs()
