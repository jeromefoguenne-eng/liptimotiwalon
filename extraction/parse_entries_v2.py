"""
parse_entries_v2.py — Parseur d'entrées du Dictionnaire Liégeois (Haust).
Optimisé avec règles de marges d'indentation (Hanging Indent) et styles de police (Times-Italic / Times-Bold).
"""

import re
from extract_v2 import COL_MARGIN

# ---------------------------------------------------------------------------
# Marqueurs grammaticaux et de source du DL
# ---------------------------------------------------------------------------
# Correction du trailing boundary bug: utilisation de (?![a-zA-Zàâéèêëîïôùûüœæç]) à la place de \b
GRAMMAR_MARKERS = re.compile(
    r'\b('
    r'm\.|f\.|î\.|v\.|adj\.|adv\.|prép\.|conj\.|interj\.|loc\.|'
    r'n\.pr\.|pron\.|num\.|art\.|part\.|suff\.|préf\.|'
    r'v\.\s*tr\.|v\.\s*intr\.|v\.\s*réfl\.|v\.\s*imp\.'
    r')(?![a-zA-Zàâéèêëîïôùûüœæç])',
    re.IGNORECASE
)

SOURCE_MARKERS = re.compile(
    r'\big\b|\bF\b|\bDefr\b|\bRemacle\b|\bSimonon\b|\bForir\b|\bErn\b|\bGdf\b|\bDR\b|\bDL\b|\bALW\b|\bWall\b|\bLiég\b|\bVerviers\b|\bNamur\b|\bCharleroi\b|\bMons\b|\bHain\b',
    re.IGNORECASE
)

# Numéro d'homographe en début de ligne : "1.mot" ou "1. mot" ou "2.mot"
HOMOGRAPH_RE = re.compile(r'^\d+\.\s*[a-zàâéèêëîïôùûüçœæå\'''-]', re.IGNORECASE)

# Sous-entrée (tiret long wallon) — pas une nouvelle entrée autonome
SUBENTRY_RE = re.compile(r'^[—–-]\s+')


def line_to_text(line: list[dict]) -> str:
    """Concatène les spans d'une ligne en texte brut (avec espaces)."""
    parts = []
    prev_x1 = None
    for span in line:
        x0 = span.get("x0")
        x1 = span.get("x1")
        if prev_x1 is not None and x0 is not None and x0 - prev_x1 > 2:
            parts.append(" ")
        parts.append(span["text"])
        prev_x1 = x1
    return "".join(parts).strip()


def line_to_rich(line: list[dict]) -> list[dict]:
    """Retourne une liste [{text, bold, italic}] pour la ligne."""
    return [{"text": s["text"], "bold": s["bold"], "italic": s["italic"]} for s in line]


def is_entry_start(line: list[dict], col_x_min: float, tome: int) -> bool:
    """
    Détermine si une ligne commence une nouvelle entrée du dictionnaire.
    Utilise l'indentation (margin) et les styles de police (italique pour T2, régulier pour T3).
    """
    if not line:
        return False

    first_span = line[0]
    x0   = first_span["x0"]
    text = line_to_text(line).strip()

    if not text:
        return False

    # 1. Vérification de l'indentation (marge)
    # L'entrée commence toujours légèrement indentée vers la droite (entre +3.0 et +18.0 pt)
    is_indented = (col_x_min + 3.0 <= x0 <= col_x_min + 18.0)
    if not is_indented:
        return False

    # 2. Exclure les légendes de figures ou pages
    if text.startswith("Fig.") or text.startswith("=== PAGE"):
        return False

    # 3. Exclure la ponctuation initiale
    first_char = text[0]
    if first_char in '—–-[]{}().,;:!?*#°':
        return False

    # 4. Exclure si le premier mot est un nombre ou un chiffre romain seul (qui n'est pas un homographe)
    first_word = text.split()[0].rstrip('.,;:')
    if re.match(r'^\d+$', first_word) or re.match(r'^[IVXivx]+$', first_word):
        if not HOMOGRAPH_RE.match(text):
            return False

    # 5. Validation selon le Tome
    if tome == 2:
        # Tome 2 (Wallon-Français) : le mot-vedette commence par de l'Italien (Italic)
        first_span_italic = first_span["italic"] or "italic" in first_span["font"].lower()
        if first_span_italic:
            return True
            
        # Fallback pour les anomalies de police (ex: caractères Å/A représentés en Romain)
        if first_char.lower() in 'aàâäå\ufffd':
            prefix = text[:60]
            has_grammar = bool(GRAMMAR_MARKERS.search(prefix))
            has_colon = bool(re.search(r'\s*[:;]', prefix))
            if has_grammar or has_colon:
                return True
                
    elif tome == 3:
        # Tome 3 (Français-Wallon) : le mot-vedette français commence par du Romain (regular),
        # suivi par la traduction wallonne qui est en gras (Bold)
        first_span_bold = first_span["bold"] or "bold" in first_span["font"].lower()
        first_span_italic = first_span["italic"] or "italic" in first_span["font"].lower()
        has_bold = any(span["bold"] or "bold" in span["font"].lower() for span in line)
        if not first_span_bold and not first_span_italic and has_bold:
            return True

    return False


def split_entry_line(line: list[dict], tome: int) -> tuple[str, str, str]:
    """
    Sépare le mot-vedette, la catégorie grammaticale et le début de la définition d'une ligne d'entrée.
    Retourne (headword, grammar, definition_start).
    """
    text = line_to_text(line).strip()

    if tome == 2:
        # Nettoyage initial du numéro d'homographe (ex: "1. ")
        text_clean = re.sub(r'^\d+\.\s*', '', text)

        # A. Essai par catégorie grammaticale (m., f., adj., etc.)
        gm = GRAMMAR_MARKERS.search(text_clean)
        if gm:
            before_gm = text_clean[:gm.start()].strip().rstrip(',; ')
            gram = gm.group(0).rstrip('.')
            defn = text_clean[gm.end():].strip().lstrip(',;.: ')
            
            # Nettoyer "seul dans les cas suivants"
            seul_match = re.search(r',\s*seul[*t\.]?\s+dans\s+', before_gm, re.I)
            if seul_match:
                extra = before_gm[seul_match.start():].strip()
                before_gm = before_gm[:seul_match.start()].strip()
                defn = extra + " : " + defn
                
            return before_gm, gram, defn

        # B. Essai par séparateur de colon (ex: "bâcler : ...")
        colon_match = re.search(r'\s*[:;]\s*', text_clean)
        if colon_match:
            before_colon = text_clean[:colon_match.start()].strip()
            defn = text_clean[colon_match.end():].strip()
            
            # Nettoyer "seul dans les cas suivants"
            seul_match = re.search(r',\s*seul[*t\.]?\s+dans\s+', before_colon, re.I)
            if seul_match:
                extra = before_colon[seul_match.start():].strip()
                before_colon = before_colon[:seul_match.start()].strip()
                defn = extra + " : " + defn
                
            return before_colon, "", defn

        # C. Découpage par style : le mot-vedette est en italique
        hw_spans = []
        def_spans = []
        in_def = False
        for span in line:
            span_text = span["text"]
            if not hw_spans:
                span_text = re.sub(r'^\d+\.\s*', '', span_text)

            is_span_italic = span["italic"] or "italic" in span["font"].lower()
            if not in_def and not is_span_italic:
                in_def = True
            if in_def:
                def_spans.append(span["text"])
            else:
                hw_spans.append(span_text)

        hw = " ".join(hw_spans).strip().rstrip(',;.: ')
        defn = " ".join(def_spans).strip()
        return hw, "", defn

    elif tome == 3:
        # Le mot-vedette français est régulier, la définition wallonne commence au premier span gras
        hw_spans = []
        def_spans = []
        in_def = False
        for span in line:
            span_text = span["text"]
            is_span_bold = span["bold"] or "bold" in span["font"].lower()
            if not in_def and is_span_bold:
                in_def = True
            if in_def:
                def_spans.append(span["text"])
            else:
                hw_spans.append(span_text)

        hw = " ".join(hw_spans).strip().rstrip(',;.: ')
        defn = " ".join(def_spans).strip()
        return hw, "", defn

    return text, "", ""


def parse_column_entries(col_lines: list[list[dict]],
                         col_x_min: float,
                         tome: int,
                         page_num: int,
                         slice_name: str) -> list[dict]:
    """
    Parcourt les lignes d'une colonne et construit la liste des entrées.
    """
    entries = []
    current_word = None
    current_grammar = ""
    current_def_lines = []

    def flush_entry():
        if current_word is None:
            return
        definition = " ".join(line_to_text(l) for l in current_def_lines).strip()
        
        # Nettoyage de la définition si elle commence par le mot lui-même
        word_lower = current_word.lower()
        if definition.lower().startswith(word_lower):
            definition = definition[len(current_word):].lstrip(',;.: ')

        needs_review = (
            len(current_word) > 60 or
            len(definition) < 5 or
            '\n' in current_word
        )

        entries.append({
            "word"        : current_word,
            "definition"  : definition,
            "grammar"     : current_grammar,
            "type"        : "francais-wallon" if tome == 3 else "wallon-francais",
            "tome"        : tome,
            "page"        : page_num,
            "slice"       : slice_name,
            "needs_review": needs_review,
        })

    for line in col_lines:
        if is_entry_start(line, col_x_min, tome):
            flush_entry()
            hw, gram, defn_start = split_entry_line(line, tome)
            current_word = hw
            current_grammar = gram
            # On stocke le début de définition sous forme de span simulé
            current_def_lines = [[{
                "text": defn_start,
                "bold": False,
                "italic": False,
                "font": "",
                "size": 0.0,
                "x0": 0.0,
                "x1": 0.0
            }]] if defn_start.strip() else []
        else:
            if current_word is not None:
                current_def_lines.append(line)

    flush_entry()
    return entries
