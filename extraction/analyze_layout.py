"""
Analyse structurelle approfondie d'une page du Dictionnaire Liégeois.
But: comprendre le layout (colonnes, polices, styles) pour concevoir
un extracteur précis.
"""
import fitz, json, os

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
PDF  = os.path.join(PROJ, 'extraction', 'pdfs', 'tome2-08.pdf')

doc = fitz.open(PDF)

# Analyser page 7 (contient abalowe) et page 8
for page_num in [6, 7]:
    page = doc[page_num]
    print(f"\n{'='*70}")
    print(f"PAGE {page_num+1}  |  Dimensions: {page.rect}")
    print(f"{'='*70}")

    # Extraire tous les spans avec métadonnées complètes
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    
    spans_data = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                font   = span.get("font", "")
                size   = round(span.get("size", 0), 1)
                flags  = span.get("flags", 0)
                color  = span.get("color", 0)
                bbox   = span.get("bbox", [0,0,0,0])
                x0, y0, x1, y1 = bbox
                
                is_bold   = bool(flags & 2**4) or "bold" in font.lower() or "Bold" in font
                is_italic = bool(flags & 2**1) or "italic" in font.lower() or "Italic" in font
                
                spans_data.append({
                    "text": text,
                    "font": font,
                    "size": size,
                    "bold": is_bold,
                    "italic": is_italic,
                    "color": color,
                    "x0": round(x0, 1),
                    "y0": round(y0, 1),
                    "x1": round(x1, 1),
                    "x_center": round((x0+x1)/2, 1)
                })
    
    # Identifier les colonnes (distribution des x)
    x_centers = [s["x_center"] for s in spans_data]
    if x_centers:
        x_min, x_max = min(x_centers), max(x_centers)
        mid = (x_min + x_max) / 2
        col1 = [s for s in spans_data if s["x_center"] < mid]
        col2 = [s for s in spans_data if s["x_center"] >= mid]
        print(f"X range: {x_min:.0f} - {x_max:.0f}, milieu: {mid:.0f}")
        print(f"Colonne 1: {len(col1)} spans | Colonne 2: {len(col2)} spans")
    
    # Afficher les polices uniques
    fonts = {}
    for s in spans_data:
        key = f"{s['font']} | size={s['size']} | bold={s['bold']} | italic={s['italic']}"
        fonts[key] = fonts.get(key, 0) + 1
    print(f"\nPolices utilisées ({len(fonts)} types):")
    for font, count in sorted(fonts.items(), key=lambda x: -x[1])[:10]:
        print(f"  [{count:3d}x] {font}")
    
    # Afficher les 40 premiers spans pour comprendre le pattern
    print(f"\nPremiers 40 spans (col 1 triés par Y):")
    col1_sorted = sorted(col1, key=lambda s: s["y0"])
    for s in col1_sorted[:40]:
        style = ""
        if s["bold"]: style += "B"
        if s["italic"]: style += "I"
        col_flag = "font=" + s["font"][:25]
        print(f"  [{style:2s}] x={s['x0']:5.0f}-{s['x1']:5.0f} y={s['y0']:5.0f} size={s['size']} | {repr(s['text'][:60])}")

doc.close()
