#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Etape 2 : Extraction du texte de chaque PDF (version Windows-compatible, sans emojis).
Utilise PyMuPDF (fitz) avec fallback pdfplumber.
"""

import sys
import json
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import fitz
    HAS_FITZ = True
    print("[OK] PyMuPDF disponible")
except ImportError:
    HAS_FITZ = False
    print("[WARN] PyMuPDF absent")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
    print("[OK] pdfplumber disponible")
except ImportError:
    HAS_PDFPLUMBER = False
    print("[WARN] pdfplumber absent")

if not HAS_FITZ and not HAS_PDFPLUMBER:
    print("[ERREUR] Aucune bibliotheque PDF. Installez: pip install pymupdf pdfplumber")
    sys.exit(1)

BASE = Path("C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/extraction")
TEXT_DIR = BASE / "texts"
TEXT_DIR.mkdir(exist_ok=True)

manifest_path = BASE / "pdf_manifest.json"
if not manifest_path.exists():
    print("[ERREUR] pdf_manifest.json introuvable. Lancez d'abord step1_run.py")
    sys.exit(1)

with open(manifest_path, encoding="utf-8") as f:
    pdf_list = json.load(f)

print(f"\nPDFs a traiter: {len(pdf_list)}")
summaries = []
scanned_count = 0

for i, pdf_info in enumerate(pdf_list, 1):
    if not pdf_info.get("downloaded") or not pdf_info.get("local_path"):
        print(f"  [{i}/{len(pdf_list)}] IGNORE (non telecharge): {pdf_info['filename']}")
        continue

    pdf_path = Path(pdf_info["local_path"])
    if not pdf_path.exists():
        print(f"  [{i}/{len(pdf_list)}] INTROUVABLE: {pdf_path}")
        continue

    print(f"  [{i}/{len(pdf_list)}] Extraction: {pdf_path.name}", end="", flush=True)

    # ----- Detection du type de PDF -----
    pdf_type = "unknown"
    total_chars = 0
    all_pages = []

    if HAS_FITZ:
        try:
            doc = fitz.open(str(pdf_path))
            num_pages = len(doc)

            for page_num, page in enumerate(doc, 1):
                # Extraction avec preservation complete de l'encodage
                text = page.get_text("text")
                total_chars += len(text.strip())
                if text.strip():
                    # Normalisation NFC pour reunifier les caracteres composes
                    text_nfc = unicodedata.normalize("NFC", text)
                    all_pages.append({"page": page_num, "text": text_nfc})

            doc.close()

            if total_chars > 50:
                pdf_type = "native_text"
            else:
                pdf_type = "scanned_image"
                scanned_count += 1

        except Exception as e:
            print(f" -> ERREUR fitz: {e}")
            pdf_type = "error"

    # Fallback pdfplumber si fitz echoue ou absent
    if not all_pages and HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    if text.strip():
                        text_nfc = unicodedata.normalize("NFC", text)
                        total_chars += len(text_nfc)
                        all_pages.append({"page": page_num, "text": text_nfc})
            if all_pages:
                pdf_type = "native_text_plumber"
        except Exception as e:
            print(f" -> ERREUR pdfplumber: {e}")

    # ----- Sauvegarde du texte -----
    success = bool(all_pages) and pdf_type not in ("scanned_image", "error")

    if success:
        text_file = TEXT_DIR / f"{pdf_path.stem}.txt"
        full_text = ""
        for p in all_pages:
            full_text += f"\n\n=== PAGE {p['page']} ===\n\n{p['text']}"

        with open(text_file, "w", encoding="utf-8") as f:
            f.write(full_text.strip())

        print(f" -> OK ({total_chars:,} chars, {len(all_pages)} pages, type={pdf_type})")
    else:
        text_file = None
        print(f" -> {pdf_type.upper()} (extraction impossible)")

    summaries.append({
        "filename": pdf_path.name,
        "source_page": pdf_info.get("source_page", ""),
        "label": pdf_info.get("label", ""),
        "type": pdf_type,
        "total_chars": total_chars,
        "num_pages": len(all_pages),
        "success": success,
        "text_file": str(text_file) if text_file else None
    })

# Sauvegarder le resume
summary_path = BASE / "extraction_summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summaries, f, ensure_ascii=False, indent=2)

ok = sum(1 for s in summaries if s["success"])
print(f"\n[RESULTAT] Extraits avec succes: {ok}/{len(summaries)}")
if scanned_count:
    print(f"[WARN] PDFs scannes (OCR requis): {scanned_count}")
print(f"Resume sauvegarde: {summary_path}")
