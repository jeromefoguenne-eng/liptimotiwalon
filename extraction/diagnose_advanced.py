"""
Diagnostic avancé : chercher le glyphe 'rond' (ring/circle) qui flotte au-dessus des lettres.
Dans les vieux PDFs typographiques, le å peut être :
1. Un glyphe séparé (cercle) à la même position X mais Y légèrement différent
2. Un caractère Unicode rare (comme ˚ U+02DA ou ° U+00B0)
3. Encodé dans une police custom avec un mapping non-standard

On cherche TOUS les caractères non-ASCII autour des pages avec abalow.
"""
import fitz
import os

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
PDF_DIR = os.path.join(PROJ, 'extraction', 'pdfs')

pdf_path = os.path.join(PDF_DIR, 'tome2-08.pdf')
doc = fitz.open(pdf_path)

target_page = None
for i, page in enumerate(doc):
    if 'abalow' in page.get_text("text").lower():
        target_page = i
        break

if target_page is None:
    print("Page non trouvée")
    exit()

print(f"Page cible: {target_page + 1}")
page = doc[target_page]

# Extraire TOUS les caractères avec leurs coordonnées
print("\n=== TOUS les chars non-ASCII sur cette page ===")
blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
all_chars = []
for b in blocks:
    if b.get("type") == 0:
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                for ch in span.get("chars", []):
                    c = ch.get("c", "")
                    x, y = ch.get("origin", (0, 0))
                    all_chars.append((x, y, c, ord(c)))
                    if ord(c) > 127:
                        print(f"  [{c}] U+{ord(c):04X} ({ord(c)}) @ x={x:.1f}, y={y:.1f}")

print(f"\nTotal chars: {len(all_chars)}")
print(f"Chars non-ASCII: {sum(1 for _,_,_,cp in all_chars if cp > 127)}")

# Chercher des patterns: char avec y légèrement différent (diacritique flottant)
# Trier par X pour trouver les superpositions
print("\n=== Recherche de glyphes superposés (même X ±2, Y différent) ===")
sorted_chars = sorted(all_chars, key=lambda c: (round(c[0]), c[1]))
for i, (x1, y1, c1, cp1) in enumerate(sorted_chars):
    for j, (x2, y2, c2, cp2) in enumerate(sorted_chars[i+1:i+5], i+1):
        if abs(x1 - x2) < 3 and abs(y1 - y2) > 2 and abs(y1 - y2) < 15:
            print(f"  SUPERPOSITION: [{c1}]U+{cp1:04X}@({x1:.1f},{y1:.1f}) + [{c2}]U+{cp2:04X}@({x2:.1f},{y2:.1f})")

# Chercher spécifiquement autour du mot "åbalowe" qui devrait être en gras/début
print("\n=== Recherche par type de polices (bold = mot-vedette) ===")
for b in blocks:
    if b.get("type") == 0:
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                font = span.get("font", "")
                text = span.get("text", "")
                size = span.get("size", 0)
                # Les mots-vedettes sont en gras
                if "bold" in font.lower() or "Bold" in font:
                    if text.strip():
                        print(f"  BOLD [{font}] size={size:.1f}: {repr(text[:60])}")

print("\nDIAGNOSTIC AVANCÉ TERMINÉ")
