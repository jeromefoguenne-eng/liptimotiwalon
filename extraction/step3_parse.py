#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Etape 3 : Parsing des entrees du dictionnaire wallon.

Format des tomes :
  Tome 2 (wallon->francais) : "MOT, gram. : definition francaise : exemples wallons"
  Tome 3 (francais->wallon) : "MOT français : equivalent(s) wallon(s) [, synonymes...]"

Logique : analyse ligne a ligne avec une machine d'etats.
"""

import sys
import re
import json
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/extraction')
TEXT_DIR = BASE / 'texts'
PARSED_DIR = BASE / 'parsed'
PARSED_DIR.mkdir(exist_ok=True)

# ─── Correspondances fichier -> (tome, lettre, type) ──────────────────────────
def get_file_meta(filename: str) -> dict:
    """Extrait les metadonnees depuis le nom de fichier."""
    m = re.match(r'(tome(\d+))-(\d+)', filename, re.I)
    if not m:
        return {'tome': 0, 'page_offset': 0, 'dict_type': 'wallon-francais'}
    tome_str, tome_num, page_str = m.group(1), int(m.group(2)), int(m.group(3))
    dict_type = 'francais-wallon' if tome_num == 3 else 'wallon-francais'
    return {
        'tome': tome_num,
        'page_offset': page_str,
        'slice': filename + '.txt',
        'dict_type': dict_type
    }

# ─── Nettoyage de base ─────────────────────────────────────────────────────────
LIGATURES = {
    '\ufb01': 'fi', '\ufb02': 'fl', '\ufb00': 'ff',
    '\ufb03': 'ffi', '\ufb04': 'ffl',
}

def normalize(text: str) -> str:
    """Normalise NFC, ligatures, espaces, sans toucher aux accents wallons."""
    text = unicodedata.normalize('NFC', text)
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    # Reunification des tirets de cesure : "dialo-\nge" -> "dialogue"
    text = re.sub(r'([a-zA-Záàâéèêëîïôùûüœæç])-\n([a-záàâéèêëîïôùûüœæç])', r'\1\2', text)
    # Nettoyer caracteres de controle (sauf \n)
    text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', '', text)
    # Normaliser espaces horizontaux
    text = re.sub(r'[ \t]+', ' ', text)
    return text

# ─── Detection d'un debut d'entree ────────────────────────────────────────────
# Tome 2 (wallon->fr) : Les entrees commencent par un mot en debut de ligne,
# souvent suivi de la categorie gram. entre parenth. et d'un point-virgule ou ":"
# Exemple : "abaye s. f. : abbaye"
# Exemple : "abeter v. tr. : habituer, accoutumer..."

# Tome 3 (fr->wallon) : Les entrees commencent par un mot français en maj/min,
# suivi de ":" et des equivalents wallons
# Exemple : "ABANDONNER : lèyî, èrlèyî, baukî, kwiter"

RE_ENTRY_T2 = re.compile(
    r'^([a-záàâéèêëîïôùûüœæçDJdj\'\-]{2,}(?:\s+[a-záàâéèêëîïôùûüœæçDJ]{1,12})?)'
    r'\s*(?:\(.*?\))?\s*(?:v\.\s*\w+\.?|s\.\s*\w+\.?|adj\.?|adv\.?|prép\.?|conj\.?|interj\.?)?'
    r'\s*[;:]\s*(.+)',
    re.IGNORECASE | re.UNICODE
)

RE_ENTRY_T3 = re.compile(
    r'^([A-ZÁÀÂÉÈÊËÎÏÔÙÛÜ][A-ZÁÀÂÉÈÊËÎÏÔÙÛÜa-z\'\- ]{1,50}?)\s*[;:]\s*(.+)',
    re.UNICODE
)

# Motifs de bruit a filtrer
NOISE_RE = re.compile(
    r'^(\d+\s*$'            # numero seul
    r'|[IVXivx]+\s*$'       # chiffre romain seul
    r'|={3,}'               # separateurs
    r'|-{3,}'
    r'|\*{3,}'
    r'|table\s+des'         # table des matieres
    r'|index\s+'            # index
    r'|bibliographie'
    r'|corrections\s+'
    r'|avant-propos'
    r'|introduction'
    r'|abreviations?'
    r'|tome\s+\d'
    r')',
    re.IGNORECASE
)

def is_noise_line(line: str) -> bool:
    line = line.strip()
    if not line or len(line) < 2:
        return True
    if NOISE_RE.search(line):
        return True
    # Ligne ne contenant que des chiffres/ponctuation
    if re.match(r'^[\d\s\.\,\;\:\!\?\-\(\)\/]+$', line):
        return True
    return False

# ─── Parser principal ─────────────────────────────────────────────────────────
def parse_text_file(text_path: Path, meta: dict) -> list[dict]:
    """Parse un fichier texte extrait d'un PDF et retourne les entrees."""
    with open(text_path, encoding='utf-8') as f:
        raw = f.read()

    text = normalize(raw)
    # Supprimer les marqueurs de page
    text = re.sub(r'\n?=== PAGE \d+ ===\n?', '\n', text)
    lines = text.splitlines()

    dict_type = meta['dict_type']
    entries = []
    current_word = None
    current_def_parts = []
    current_page = meta['page_offset']

    pattern = RE_ENTRY_T2 if dict_type == 'wallon-francais' else RE_ENTRY_T3

    for line in lines:
        line = line.strip()

        # Mise a jour du numero de page si marqueur
        pm = re.match(r'=== PAGE (\d+) ===', line)
        if pm:
            current_page = meta['page_offset'] * 100 + int(pm.group(1))
            continue

        if is_noise_line(line):
            continue

        m = pattern.match(line)
        if m:
            # Sauvegarder l'entree precedente
            if current_word and current_def_parts:
                definition = ' '.join(current_def_parts).strip()
                if len(definition) > 3:
                    entries.append({
                        'word': current_word,
                        'definition': definition,
                        'type': dict_type,
                        'tome': meta['tome'],
                        'page': current_page,
                        'slice': meta.get('slice', text_path.name)
                    })
            # Nouvelle entree
            current_word = m.group(1).strip().rstrip('.,;:')
            current_def_parts = [m.group(2).strip()]
        elif current_word and line:
            # Continuation de la definition precedente
            # Sauf si c'est visiblement un nouveau paragraphe sans entree
            current_def_parts.append(line)

    # Derniere entree
    if current_word and current_def_parts:
        definition = ' '.join(current_def_parts).strip()
        if len(definition) > 3:
            entries.append({
                'word': current_word,
                'definition': definition,
                'type': dict_type,
                'tome': meta['tome'],
                'page': current_page,
                'slice': meta.get('slice', text_path.name)
            })

    return entries


def deduplicate(entries: list[dict]) -> list[dict]:
    """Deduplique en gardant la definition la plus complete par mot+type."""
    seen = {}
    for e in entries:
        key = (unicodedata.normalize('NFD', e['word'].lower().strip()), e['type'])
        if key not in seen or len(e['definition']) > len(seen[key]['definition']):
            seen[key] = e
    result = list(seen.values())
    result.sort(key=lambda x: unicodedata.normalize('NFD', x['word'].lower()))
    return result


def process_all():
    summary_path = BASE / 'extraction_summary.json'
    if not summary_path.exists():
        print('[ERREUR] extraction_summary.json introuvable. Lancez step2_extract.py')
        sys.exit(1)

    with open(summary_path, encoding='utf-8') as f:
        summaries = json.load(f)

    all_entries = []
    per_file_stats = {}

    for i, s in enumerate(summaries, 1):
        if not s.get('success') or not s.get('text_file'):
            fname = s.get('filename', '?')
            print(f'  [{i}/{len(summaries)}] IGNORE: {fname}')
            continue

        text_path = Path(s['text_file'])
        if not text_path.exists():
            print(f'  [{i}/{len(summaries)}] INTROUVABLE: {text_path.name}')
            continue

        meta = get_file_meta(text_path.stem)
        meta['slice'] = text_path.stem + '.pdf'

        print(f'  [{i}/{len(summaries)}] Parsing: {text_path.name} '
              f'(tome {meta["tome"]}, {meta["dict_type"]})', end='', flush=True)

        entries = parse_text_file(text_path, meta)
        print(f' -> {len(entries)} entrees')
        per_file_stats[text_path.stem] = len(entries)
        all_entries.extend(entries)

    print(f'\nTotal brut: {len(all_entries)} entrees')

    # Deduplication
    final = deduplicate(all_entries)
    print(f'Apres deduplication: {len(final)} entrees')

    # Stats par type
    wf = sum(1 for e in final if e['type'] == 'wallon-francais')
    fw = sum(1 for e in final if e['type'] == 'francais-wallon')
    print(f'  Wallon->Francais : {wf}')
    print(f'  Francais->Wallon : {fw}')

    # Sauvegarde
    out = PARSED_DIR / 'all_entries_raw.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    stats_out = PARSED_DIR / 'per_file_stats.json'
    with open(stats_out, 'w', encoding='utf-8') as f:
        json.dump(per_file_stats, f, ensure_ascii=False, indent=2)

    print(f'\nDonnees sauvees: {out}')
    return final


if __name__ == '__main__':
    print('=' * 70)
    print('  LI PTIT MOTI WALON -- Etape 3 : Parsing des entrees')
    print('=' * 70)
    process_all()
