"""
extract_v2.py — Extracteur colonne par colonne du Dictionnaire Liégeois (Haust).

Architecture:
1. PyMuPDF extraie tous les spans avec métadonnées (position, police, taille, gras)
2. Séparation gauche/droite par détection automatique du milieu de page
3. Regroupement par lignes (tolérance Y ±3pt)
4. Suppression en-têtes et pieds de page
5. Retourne une liste de lignes structurées par colonne
"""

import fitz
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
Y_HEADER_MAX  = 158   # Ignorer tout ce qui est au-dessus (catchwords, n° page)
Y_FOOTER_MIN  = 820   # Ignorer tout ce qui est en-dessous
LINE_MERGE_Y  = 3.5   # Tolérance en points pour fusionner deux spans sur même ligne
COL_MARGIN    = 18    # Marge gauche pour détection début d'entrée


# ---------------------------------------------------------------------------
# Helpers détection style
# ---------------------------------------------------------------------------
def _is_bold(span: dict) -> bool:
    flags = span.get("flags", 0)
    font  = span.get("font", "")
    return bool(flags & (1 << 4)) or "bold" in font.lower() or "Bold" in font

def _is_italic(span: dict) -> bool:
    flags = span.get("flags", 0)
    font  = span.get("font", "")
    return bool(flags & (1 << 1)) or "italic" in font.lower() or "Italic" in font


# ---------------------------------------------------------------------------
# Extraction d'une page
# ---------------------------------------------------------------------------
def extract_page_spans(page: fitz.Page) -> list[dict]:
    """Retourne tous les spans d'une page avec leurs métadonnées."""
    spans = []
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                bbox = span.get("bbox", [0, 0, 0, 0])
                x0, y0, x1, y1 = bbox[0], bbox[1], bbox[2], bbox[3]
                spans.append({
                    "text"    : text,
                    "bold"    : _is_bold(span),
                    "italic"  : _is_italic(span),
                    "size"    : round(span.get("size", 0), 1),
                    "font"    : span.get("font", ""),
                    "x0"      : round(x0, 1),
                    "y0"      : round(y0, 1),
                    "x1"      : round(x1, 1),
                    "x_center": round((x0 + x1) / 2, 1),
                })
    return spans


def detect_col_split(spans: list[dict]) -> float:
    """Détecte la frontière entre les deux colonnes par analyse de la distribution X."""
    if not spans:
        return 300.0
    xs = sorted(s["x_center"] for s in spans)
    x_min, x_max = xs[0], xs[-1]
    # On cherche le "vide" au milieu : gap le plus grand dans la plage centrale
    mid_lo = x_min + (x_max - x_min) * 0.35
    mid_hi = x_min + (x_max - x_min) * 0.65
    central = [x for x in xs if mid_lo <= x <= mid_hi]
    if len(central) < 2:
        return (x_min + x_max) / 2
    # Gap le plus large dans la zone centrale
    best_gap = 0
    best_x   = (x_min + x_max) / 2
    for i in range(len(central) - 1):
        gap = central[i+1] - central[i]
        if gap > best_gap:
            best_gap = gap
            best_x   = (central[i] + central[i+1]) / 2
    # Si pas de gap significatif, utiliser le milieu simple
    if best_gap < 5:
        best_x = (x_min + x_max) / 2
    return best_x


def group_into_lines(spans: list[dict], y_tol: float = LINE_MERGE_Y) -> list[list[dict]]:
    """Regroupe les spans par ligne (même Y ± y_tol), triés par X dans chaque ligne."""
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: (s["y0"], s["x0"]))
    lines = []
    current = [sorted_spans[0]]
    cur_y   = sorted_spans[0]["y0"]
    for span in sorted_spans[1:]:
        if abs(span["y0"] - cur_y) <= y_tol:
            current.append(span)
        else:
            lines.append(sorted(current, key=lambda s: s["x0"]))
            current = [span]
            cur_y   = span["y0"]
    if current:
        lines.append(sorted(current, key=lambda s: s["x0"]))
    return lines


def filter_header_footer(lines: list[list[dict]]) -> list[list[dict]]:
    """Supprime les lignes d'en-tête, pied de page et numéros de page isolés."""
    result = []
    for line in lines:
        y = line[0]["y0"]
        # Zone en-tête ou pied
        if y < Y_HEADER_MAX or y > Y_FOOTER_MIN:
            continue
        # Numéro de page isolé (ligne = 1 ou 2 spans = chiffre seul)
        full = " ".join(s["text"].strip() for s in line)
        if re.match(r'^\s*\d{1,4}\s*$', full):
            continue
        result.append(line)
    return result


def extract_columns(page: fitz.Page) -> tuple[list, list]:
    """
    Extrait le texte d'une page en deux colonnes ordonnées.
    Retourne (col_left, col_right), chacune étant une liste de lignes.
    Chaque ligne est une liste de spans {text, bold, italic, size, x0, y0, ...}.
    """
    spans    = extract_page_spans(page)
    col_split = detect_col_split(spans)

    left_spans  = [s for s in spans if s["x_center"] <  col_split]
    right_spans = [s for s in spans if s["x_center"] >= col_split]

    col_left  = filter_header_footer(group_into_lines(left_spans))
    col_right = filter_header_footer(group_into_lines(right_spans))

    return col_left, col_right, col_split


def col_left_x(lines: list[list[dict]]) -> float:
    """Retourne le X minimal (marge gauche) d'une colonne."""
    if not lines:
        return 130.0
    return min(span["x0"] for line in lines for span in line)
