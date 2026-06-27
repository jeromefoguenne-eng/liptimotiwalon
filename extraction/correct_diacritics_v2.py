"""
correct_diacritics_v2.py — Application du å wallon sur les entrées extraites.
"""

import json
import re
from pathlib import Path

PROJ = Path(__file__).parent.parent

# Charger le mapping wa.wiktionary
_MAP_FILE = PROJ / "extraction" / "wallon_a_rond_clean.json"


def _load_mapping() -> dict:
    if not _MAP_FILE.exists():
        return {}
    with open(_MAP_FILE, encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("mapping", {})
    # Filtrer : >= 4 chars pour éviter faux positifs
    return {k: v for k, v in raw.items() if len(k) >= 4}


MAPPING = _load_mapping()
MAPPING_KEYS_SORTED = sorted(MAPPING.keys(), key=len, reverse=True)

# Caractères valides dans un mot wallon
_WAL_CHARS = r"a-zàâéèêëîïôùûüçœæåÅ'\-\ufffd"
_BOUNDARY = rf"(?<![{_WAL_CHARS}]){{}}(?![{_WAL_CHARS}])"


def make_accent_insensitive_regex(key: str) -> re.Pattern:
    """
    Génère un regex pour la clé qui tolère les variations d'accents du PDF.
    Ex: 'awe' -> matches '[aàâå\ufffd]w[eéèêë]'
    """
    pattern_parts = []
    for char in key.lower():
        if char == 'a':
            pattern_parts.append('[aàâäå\ufffd]')
        elif char == 'e':
            pattern_parts.append('[eéèêë]')
        elif char == 'i':
            pattern_parts.append('[iîï]')
        elif char == 'o':
            pattern_parts.append('[oô]')
        elif char == 'u':
            pattern_parts.append('[uûù]')
        else:
            pattern_parts.append(re.escape(char))

    pattern_str = "".join(pattern_parts)
    return re.compile(
        _BOUNDARY.format(pattern_str),
        re.IGNORECASE
    )


def apply_a_ring_to_text(text: str) -> tuple[str, bool]:
    """
    Applique les corrections å sur un texte quelconque.
    Retourne (texte_corrigé, modifié).
    """
    if not text:
        return text, False

    result = text
    modified = False

    for key in MAPPING_KEYS_SORTED:
        val = MAPPING[key]
        if key == val.lower():
            continue
        pattern = make_accent_insensitive_regex(key)
        new_result = pattern.sub(val, result)
        if new_result != result:
            result = new_result
            modified = True

    return result, modified


def correct_entry(entry: dict) -> dict:
    """
    Applique les corrections å sur le mot-vedette et la définition d'une entrée.
    """
    entry = dict(entry)  # Copie

    word, word_changed = apply_a_ring_to_text(entry.get("word", ""))
    defn, defn_changed = apply_a_ring_to_text(entry.get("definition", ""))

    entry["word"] = word
    entry["definition"] = defn
    entry["a_ring_corrected"] = word_changed or defn_changed

    # Heuristique supplémentaire : mots-vedettes commençant par "a"
    w = entry["word"].lower()
    if (not entry["a_ring_corrected"]
            and w and w[0] in 'aàâäå\ufffd'
            and len(w) >= 4
            and len(w) <= 25
            and not w.startswith("av")
            and not w.startswith("au")
            and not w.startswith("af")
            and re.match(r'^[aàâäå\ufffd][bcdfghjklmnpqrstvwxyz]', w)):
        entry["needs_review"] = True

    return entry
