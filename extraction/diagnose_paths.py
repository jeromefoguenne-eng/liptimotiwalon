"""
Diagnostic final : le 'rond en chef' wallon est-il un path graphique (cercle vectoriel)
plutôt qu'un caractère texte ? On examine les paths SVG/PDF de la page.
"""
import fitz
import os

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
PDF_DIR = os.path.join(PROJ, 'extraction', 'pdfs')

pdf_path = os.path.join(PDF_DIR, 'tome2-08.pdf')
doc = fitz.open(pdf_path)

# Trouver la page avec åbalowe - qui devrait être AVANT abalowe (mot-vedette)
# Le mot-vedette est en début d'entrée
print("=== Recherche pages candidates ===")
for i, page in enumerate(doc):
    text = page.get_text("text")
    if 'abalowe' in text.lower():
        print(f"  Page {i+1}: contient abalowe")
        # Chercher aussi les pages précédentes (mot-vedette peut être fin de page précédente)
        if i > 0:
            prev_text = doc[i-1].get_text("text")
            lines_end = prev_text.strip().split('\n')[-10:]
            print(f"  Page {i} (fin): {lines_end}")

# Examiner les drawings (paths graphiques) sur la page cible
target_page = None
for i, page in enumerate(doc):
    if 'abalowe' in page.get_text("text").lower():
        target_page = i
        break

if target_page is not None:
    page = doc[target_page]

    print(f"\n=== Drawings (paths) sur page {target_page+1} ===")
    drawings = page.get_drawings()
    print(f"Nombre de drawings: {len(drawings)}")

    # Filtrer les petits cercles/ellipses (= ronds diacritiques)
    small_circles = []
    for d in drawings:
        rect = d.get("rect")
        if rect:
            w = rect.width
            h = rect.height
            # Un rond diacritique est très petit (< 5x5 points)
            if w < 8 and h < 8 and w > 0 and h > 0:
                small_circles.append((rect.x0, rect.y0, w, h, d.get("type", "?"), d.get("color")))

    print(f"Petits cercles/paths (< 8x8): {len(small_circles)}")
    for x, y, w, h, t, c in small_circles[:20]:
        print(f"  @ ({x:.1f}, {y:.1f}) size={w:.1f}x{h:.1f} type={t} color={c}")

    # Afficher aussi le texte ligne par ligne pour trouver où est åbalowe
    print(f"\n=== Texte de la page {target_page+1} (premières lignes) ===")
    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b.get("type") == 0:
            for line in b.get("lines", [])[:5]:
                text = " ".join(s.get("text", "") for s in line.get("spans", []))
                y = line["bbox"][1]
                print(f"  y={y:.0f}: {text[:80]}")

    # Comparer: où sont les chars 'a' de début de ligne vs petits paths
    print(f"\n=== Chars 'a' en début de span (mots-vedettes potentiels) ===")
    rawdict = page.get_text("rawdict")
    for b in rawdict["blocks"]:
        if b.get("type") == 0:
            for line in b.get("lines", []):
                spans = line.get("spans", [])
                if spans:
                    first_span = spans[0]
                    chars = first_span.get("chars", [])
                    if chars and chars[0].get("c", "").lower() == "a":
                        # Premier char est 'a' - pourrait être un mot-vedette avec å
                        first_char = chars[0]
                        x0, y0 = first_char.get("origin", (0,0))
                        span_text = first_span.get("text","")
                        print(f"  'a' @ ({x0:.1f},{y0:.1f}): {repr(span_text[:30])}")
                        # Chercher un path/drawing à cette position (au-dessus: y0-6 à y0-2)
                        for cx, cy, cw, ch, ct, cc in small_circles:
                            if abs(cx - x0) < 5 and (cy < y0) and (y0 - cy) < 12:
                                print(f"    -> ROND DÉTECTÉ! path @ ({cx:.1f},{cy:.1f})")

print("\n=== DIAGNOSTIC PATHS TERMINÉ ===")
