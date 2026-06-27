"""
Diagnostic: comment le å wallon est encodé dans les PDFs Haust.
Compare pdfplumber vs pymupdf sur une page contenant "åbalowe".
"""
import fitz
import pdfplumber
import os, re

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
PDF_DIR = os.path.join(PROJ, 'extraction', 'pdfs')

# tome2-08.pdf contient abalow/abastri
pdf_path = os.path.join(PDF_DIR, 'tome2-08.pdf')

print("=" * 60)
print("DIAGNOSTIC PyMuPDF vs pdfplumber")
print("=" * 60)

# --- PyMuPDF ---
print("\n=== PyMuPDF (fitz) ===")
doc = fitz.open(pdf_path)
for page_num in range(min(len(doc), 30)):
    page = doc[page_num]
    text = page.get_text("text")
    if 'abalow' in text.lower() or 'abastri' in text.lower():
        print(f"[Page {page_num+1}] FOUND!")
        # Chercher le contexte
        for line in text.split('\n'):
            if 'abalow' in line.lower() or 'abastri' in line.lower():
                print(f"  Texte: {repr(line)}")
                # Afficher les codes Unicode de chaque caractère
                for c in line[:30]:
                    if ord(c) > 127:
                        print(f"    Char: {repr(c)} = U+{ord(c):04X}")
        break

print("\n=== PyMuPDF - extraction par caractère (rawdict) ===")
doc2 = fitz.open(pdf_path)
for page_num in range(min(len(doc2), 30)):
    page = doc2[page_num]
    text = page.get_text("text")
    if 'abalow' in text.lower():
        # Extraction détaillée par bloc/ligne/span/char
        blocks = page.get_text("rawdict")["blocks"]
        for b in blocks:
            if b.get("type") == 0:
                for line in b.get("lines", []):
                    line_text = "".join(
                        c.get("c", "") for s in line.get("spans", [])
                        for c in s.get("chars", [])
                    )
                    if 'abalow' in line_text.lower():
                        print(f"  Ligne brute: {repr(line_text)}")
                        # Afficher chaque char avec son origine
                        for span in line.get("spans", []):
                            for ch in span.get("chars", []):
                                c = ch.get("c", "")
                                if c.strip():
                                    print(f"    [{c}] U+{ord(c):04X} @ x={ch.get('origin',(0,0))[0]:.1f}")
        break

# --- pdfplumber (comparaison) ---
print("\n=== pdfplumber (ancien extracteur) ===")
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages[:30]):
        text = page.extract_text() or ""
        if 'abalow' in text.lower():
            print(f"[Page {page_num+1}] FOUND!")
            for line in text.split('\n'):
                if 'abalow' in line.lower():
                    print(f"  Texte: {repr(line)}")
            break

print("\nDIAGNOSTIC TERMINÉ")
