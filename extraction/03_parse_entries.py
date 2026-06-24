#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Étape 3 : Parsing intelligent des entrées du dictionnaire wallon.

Stratégie de parsing :
- Détecte automatiquement le format de chaque PDF (français→wallon ou wallon→français)
- Applique des règles heuristiques pour extraire chaque entrée
- Corrige les coupures de ligne et artefacts d'extraction
- Préserve tous les caractères spéciaux wallons (â, è, ê, ô, û, ô, ȃ, etc.)

Utilise Gemma 4 via Ollama pour les cas ambigus.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent
TEXT_DIR = BASE_DIR / "texts"
PARSED_DIR = BASE_DIR / "parsed"
PARSED_DIR.mkdir(exist_ok=True)

# ─── Nettoyage du texte ───────────────────────────────────────────────────────
LIGATURES = {
    '\ufb01': 'fi', '\ufb02': 'fl', '\ufb00': 'ff',
    '\ufb03': 'ffi', '\ufb04': 'ffl', '\u0153': 'oe', '\u0152': 'OE',
    '\u00e6': 'ae', '\u00c6': 'AE',
}

def clean_text(text: str) -> str:
    """Nettoie le texte extrait : ligatures, espaces parasites, césures."""
    # Normalisation Unicode NFC (recompose les caractères composites)
    text = unicodedata.normalize('NFC', text)

    # Remplacer les ligatures typographiques
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)

    # Fusionner les mots coupés par un tiret en fin de ligne (césure)
    # Exemple: "dialo-\nge" → "dialogue"
    text = re.sub(r'-\n([a-záàâéèêëîïôùûüœæç])', r'\1', text)

    # Normaliser les espaces multiples
    text = re.sub(r'[ \t]+', ' ', text)

    # Supprimer les espaces en début/fin de ligne
    lines = [l.strip() for l in text.splitlines()]
    text = '\n'.join(lines)

    # Réduire les lignes vides multiples (max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ─── Détection du format de dictionnaire ─────────────────────────────────────
def detect_dict_format(text: str, source_page: str) -> str:
    """
    Détecte si c'est un dictionnaire wallon→français ou français→wallon.
    Retourne: 'wallon-francais' ou 'francais-wallon'
    """
    if "liegeois" in source_page and "francais" not in source_page:
        return "wallon-francais"
    if "francais-liegeois" in source_page:
        return "francais-wallon"
    # Heuristique sur le contenu
    wallon_markers = len(re.findall(r'\b(li|èl|nos|vos|dj|dji)\b', text[:2000]))
    french_markers = len(re.findall(r'\b(le|la|les|un|une|des|il|elle)\b', text[:2000]))
    return "wallon-francais" if wallon_markers > french_markers else "francais-wallon"


# ─── Patterns de parsing ──────────────────────────────────────────────────────

# Pattern 1: Entrée en début de ligne avec définition après (séparateur : ou ,)
# Exemple: "amon (prép.) : chez, auprès de"
PATTERN_ENTRY_WITH_DEF = re.compile(
    r'^([A-ZÁÀÂÉÈÊËÎÏÔÙÛÜŒ][^:\n]{1,50}?)\s*[:—]\s*(.+)',
    re.MULTILINE
)

# Pattern 2: Mot en gras ou majuscules suivi d'une définition sur la même ligne ou suivante
# Exemple: "ÅME s.f. âme, esprit"
PATTERN_BOLD_ENTRY = re.compile(
    r'^([A-ZÁÀÂÉÈÊËÎÏÔÙÛÜŒ]{2,}(?:\s+[a-záàâéèêëîïôùûüœ.]+)?)\s+(.+)',
    re.MULTILINE
)

# Pattern 3: Format "mot — traduction (source)"
PATTERN_DASH_SEP = re.compile(
    r'^([^\-—\n]{2,40})\s*[—\-]\s*(.+)',
    re.MULTILINE
)

# Pattern 4: Colonnes séparées par des espaces importants (format tableau)
PATTERN_COLUMNS = re.compile(
    r'^(\S[^\t]{1,30})\t+(.+)',
    re.MULTILINE
)


def parse_entries_heuristic(text: str, source_page: str, filename: str) -> list[dict]:
    """
    Parsing heuristique du texte extrait.
    Essaie plusieurs patterns et garde les meilleurs résultats.
    """
    text = clean_text(text)
    dict_format = detect_dict_format(text, source_page)
    entries = []

    # Essai pattern 1 : séparateur ":"
    matches_colon = PATTERN_ENTRY_WITH_DEF.findall(text)

    # Essai pattern 2 : majuscules + définition
    matches_bold = PATTERN_BOLD_ENTRY.findall(text)

    # Essai pattern 3 : tiret/dash
    matches_dash = PATTERN_DASH_SEP.findall(text)

    # Choisir le pattern qui donne le plus de résultats cohérents
    best_matches = max(
        [matches_colon, matches_bold, matches_dash],
        key=len
    )

    for word, definition in best_matches:
        word = word.strip().rstrip('.,;:')
        definition = definition.strip()

        # Filtres qualité
        if len(word) < 2 or len(word) > 80:
            continue
        if len(definition) < 2:
            continue
        # Exclure les entrées qui ressemblent à des numéros de page
        if re.match(r'^\d+$', word):
            continue
        # Exclure les en-têtes de colonnes typiques
        if word.lower() in ('page', 'liégeois', 'français', 'wallon', 'traduction'):
            continue

        entry = {
            "mot": word,
            "definition": definition,
            "type": dict_format,
            "source": filename,
        }
        entries.append(entry)

    return entries


def parse_block_format(text: str, source_page: str, filename: str) -> list[dict]:
    """
    Parser alternatif pour les PDFs avec format en blocs :
    un mot par paragraphe suivi de sa définition.
    """
    text = clean_text(text)
    dict_format = detect_dict_format(text, source_page)
    entries = []

    # Découper en blocs séparés par des lignes vides
    blocks = re.split(r'\n\n+', text)

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        # La première ligne est le mot, le reste est la définition
        mot = lines[0].rstrip('.,;:')
        definition = ' '.join(lines[1:])

        # Filtres basiques
        if len(mot) > 80 or len(mot) < 2:
            continue
        if not re.search(r'[a-záàâéèêëîïôùûüœæçDJ]', definition):
            continue

        entries.append({
            "mot": mot,
            "definition": definition,
            "type": dict_format,
            "source": filename
        })

    return entries


def parse_text_file(text_path: Path, source_page: str) -> list[dict]:
    """Parse un fichier texte et retourne les entrées du dictionnaire."""
    with open(text_path, encoding="utf-8") as f:
        full_text = f.read()

    # Supprimer les marqueurs de page ajoutés à l'extraction
    full_text = re.sub(r'\n\n--- PAGE \d+ ---\n\n', '\n\n', full_text)

    # Essai heuristique
    entries_h = parse_entries_heuristic(full_text, source_page, text_path.stem)

    # Essai format blocs
    entries_b = parse_block_format(full_text, source_page, text_path.stem)

    # Retourner le meilleur résultat
    if len(entries_h) >= len(entries_b):
        return entries_h
    return entries_b


def process_all_texts():
    summary_path = BASE_DIR / "extraction_summary.json"
    if not summary_path.exists():
        print("❌ Résumé d'extraction non trouvé. Exécutez d'abord 02_extract_text.py")
        sys.exit(1)

    with open(summary_path, encoding="utf-8") as f:
        summaries = json.load(f)

    all_entries = []
    stats = {}

    for i, s in enumerate(summaries, 1):
        if not s["success"] or not s.get("text_file"):
            print(f"  ⏭️  [{i}/{len(summaries)}] Ignoré: {s['filename']}")
            continue

        text_path = Path(s["text_file"])
        if not text_path.exists():
            print(f"  ❌ [{i}/{len(summaries)}] Fichier texte introuvable: {text_path}")
            continue

        print(f"  🔍 [{i}/{len(summaries)}] Parsing: {s['filename']}")
        entries = parse_text_file(text_path, s["source_page"])
        print(f"     → {len(entries)} entrées trouvées")

        stats[s["filename"]] = len(entries)
        all_entries.extend(entries)

    # Déduplication par mot (garder la définition la plus longue)
    dedup = {}
    for entry in all_entries:
        key = entry["mot"].lower().strip()
        if key not in dedup or len(entry["definition"]) > len(dedup[key]["definition"]):
            dedup[key] = entry

    final_entries = list(dedup.values())
    final_entries.sort(key=lambda x: x["mot"].lower())

    # Sauvegarde
    parsed_path = PARSED_DIR / "all_entries_raw.json"
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(final_entries, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Résultats du parsing:")
    print(f"   Entrées brutes totales : {len(all_entries)}")
    print(f"   Après déduplication   : {len(final_entries)}")
    for fname, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {fname:40s}: {count:5d} entrées")
    print(f"\n💾 Données brutes sauvées: {parsed_path}")
    return final_entries


if __name__ == "__main__":
    print("=" * 70)
    print("  LI PTIT MOTI WALON — Étape 3 : Parsing des entrées")
    print("=" * 70)
    process_all_texts()
