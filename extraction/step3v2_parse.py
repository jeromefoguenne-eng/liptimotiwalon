#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Etape 3 v2 : Parser ameliore avec gestion du format en colonnes du Tome 3.

Format Tome 2 (wallon->francais):
  "abaye s. f. : abbaye, couvent"   (mot wallon : definition francaise)
  
Format Tome 3 (francais->wallon):
  Les colonnes sont fusionnees par pdfplumber en lignes melees.
  Exemple : "abandonner abann'ner; cwiter; dilèyî"
  => mot français | equivalent wallon sur la meme ligne
  
  Autre format frequent :
  "abattre abate (r-); fé tourner; crdwer;"
  
Strategie Tome 3 :
  - Chaque entree commence par UN MOT (ou groupe de mots) en francais SANS accent
    suivi directement par des mots wallons (avec accents wallons: â, ô, è, î etc.)
  - On split sur le premier token "wallon" (contenant des caracteres speciaux)
  - Fallback: les noms de chapitres "NOM1 — NOM2" en debut de page indiquent la plage
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

LIGATURES = {
    '\ufb01': 'fi', '\ufb02': 'fl', '\ufb00': 'ff',
    '\ufb03': 'ffi', '\ufb04': 'ffl',
}

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFC', text)
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    # Cesures : "dialo-\nge" -> "dialogue"
    text = re.sub(r'([a-zA-Záàâéèêëîïôùûüœæç])-\n([a-záàâéèêëîïôùûüœæç])', r'\1\2', text)
    text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text


def get_file_meta(filename: str) -> dict:
    m = re.match(r'tome(\d+)-(\d+)', filename, re.I)
    if not m:
        return {'tome': 0, 'page_offset': 0, 'dict_type': 'wallon-francais', 'slice': filename}
    tome_num, page_num = int(m.group(1)), int(m.group(2))
    dict_type = 'francais-wallon' if tome_num == 3 else 'wallon-francais'
    return {
        'tome': tome_num,
        'page_offset': page_num,
        'dict_type': dict_type,
        'slice': filename.replace('.txt', '.pdf')
    }


# ─── NOISE ────────────────────────────────────────────────────────────────────
NOISE_RE = re.compile(
    r'^(?:\d+\s*$'
    r'|[IVXivx]+\s*$'
    r'|={2,}|-{3,}|\*{3,}'
    r'|table\s+des|index\s+|bibliographie|avant-propos|introduction'
    r'|abr.viations?|corrections?\s|additions?\s'
    r'|tome\s+\d|vol\.?\s+\d)',
    re.I
)

def is_noise(line: str) -> bool:
    s = line.strip()
    if not s or len(s) < 2:
        return True
    if NOISE_RE.match(s):
        return True
    if re.match(r'^[\d\s\.\,\;\:\!\?\-\(\)\/\[\]]+$', s):
        return True
    return False


# ─── PARSER TOME 2 (wallon->francais) ─────────────────────────────────────────
# Format: mot_wallon [gram.] : definition_francaise
RE_T2 = re.compile(
    r'^([a-záàâéèêëîïôùûüœæçDJdj\'\-\(]{2,}(?:\s+[a-záàâéèêëîïôùûüœæçDJ\(\)\.]{1,15})*)'
    r'\s*[;:]\s*(.+)',
    re.IGNORECASE | re.UNICODE
)

def parse_tome2(lines: list[str], meta: dict) -> list[dict]:
    """Parse Tome 2 (wallon->francais) ligne par ligne."""
    entries = []
    current_word = None
    current_def = []
    page = meta['page_offset']

    for line in lines:
        line = line.strip()
        pm = re.match(r'=== PAGE (\d+) ===', line)
        if pm:
            page = int(pm.group(1))
            continue
        if is_noise(line):
            continue

        m = RE_T2.match(line)
        if m:
            # Sauvegarder l'entree precedente
            if current_word and current_def:
                defn = ' '.join(current_def).strip()
                if len(defn) > 2:
                    entries.append({
                        'word': current_word,
                        'definition': defn,
                        'type': 'wallon-francais',
                        'tome': meta['tome'],
                        'page': page,
                        'slice': meta['slice']
                    })
            current_word = m.group(1).strip().rstrip('.,;:')
            current_def = [m.group(2).strip()]
        elif current_word and line:
            current_def.append(line)

    if current_word and current_def:
        defn = ' '.join(current_def).strip()
        if len(defn) > 2:
            entries.append({
                'word': current_word,
                'definition': defn,
                'type': 'wallon-francais',
                'tome': meta['tome'],
                'page': page,
                'slice': meta['slice']
            })
    return entries


# ─── PARSER TOME 3 (francais->wallon) ─────────────────────────────────────────
# Format colonne : "MOT_FRANÇAIS equivalent_wallon_avec_accents"
# Le mot français est sans accents wallons, la def contient des accents (â,ô,è,î,û,dj,dji)
#
# Caracteres typiquement wallons : â, ô, û, î, dj, dji, ès, èl, on, etc.
# Le split se fait quand on trouve le premier token avec accent wallon apres le mot fr.

WALLON_CHARS = re.compile(r'[âôûîèêëœæ]|(?:dj[ie]?)|(?:on\s)|(?:ès?\s)|(?:al\s)', re.U)

# Pattern principal T3: mot(s) français + : + wallon
# Le ":" peut etre absent, les mots wallons commencent apres le dernier mot francais "propre"
RE_T3_COLON = re.compile(
    r'^([A-ZÀÂÈÉÊËÎÏÔÙÛÜa-zàâèéêëîïôùûü][A-ZÀÂÈÉÊËÎÏÔÙÛÜa-zàâèéêëîïôùûü\'\- ]{1,60}?)'
    r'\s*[;:]\s*'
    r'(.+)',
    re.UNICODE
)

# Pattern secondaire : "MOT_FR equiv_wallon" sans separateur explicite
# On detecte la frontiere ou les accents wallons apparaissent
RE_T3_NO_SEP = re.compile(
    r'^([A-Za-zàâèéêëîïôùûüÀÂÈÉÊËÎÏÔÙÛÜ][a-zA-Zàâèéêëîïôùûü\-\' ]{1,40}?)\s+'
    r'([a-záàâéèêëîïôùûüœæçDJdj\-\']{2,}.+)',
    re.UNICODE
)

def has_wallon_chars(text: str) -> bool:
    """Verifie si le texte contient des caracteres/patterns typiquement wallons."""
    return bool(WALLON_CHARS.search(text))

def parse_tome3(lines: list[str], meta: dict) -> list[dict]:
    """
    Parse Tome 3 (francais->wallon).
    Les lignes sont souvent le melange de deux colonnes concatenees.
    Strategie: chercher le pattern 'mot_fr : equiv_wallon' ou 'mot_fr equiv_wallon'
    """
    entries = []
    page = meta['page_offset']
    
    # Reconstituer les blocs d'entrees
    # Dans ce format, chaque entree est generalement sur 1-3 lignes
    # On joint les lignes courtes et on re-split
    
    all_text = '\n'.join(lines)
    # Supprimer les marqueurs de page
    all_text = re.sub(r'=== PAGE \d+ ===', '\n', all_text)
    
    # Chercher toutes les entrees avec le pattern "MOT : wallon"
    # On split le texte en segments a chaque fois qu'on trouve un debut d'entree
    
    # Collecte avec pattern colon d'abord (plus fiable)
    for line in all_text.splitlines():
        line = line.strip()
        if is_noise(line):
            continue
        
        # Essai pattern avec ":"
        m = RE_T3_COLON.match(line)
        if m:
            word_fr = m.group(1).strip().rstrip('.,;:- ')
            definition = m.group(2).strip()
            
            # Valider: le mot fr ne doit pas etre trop court ou ressembler a du bruit
            if len(word_fr) < 2 or len(word_fr) > 60:
                continue
            if len(definition) < 2:
                continue
            # La definition doit contenir quelque chose de wallon ou fr
            if not re.search(r'[a-zA-Záàâéèêëîïôùûüœæç]', definition):
                continue
            
            entries.append({
                'word': word_fr,
                'definition': definition,
                'type': 'francais-wallon',
                'tome': meta['tome'],
                'page': page,
                'slice': meta['slice']
            })
        
    return entries


def deduplicate(entries: list[dict]) -> list[dict]:
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
        print('[ERREUR] extraction_summary.json introuvable.')
        sys.exit(1)

    with open(summary_path, encoding='utf-8') as f:
        summaries = json.load(f)

    all_entries = []
    per_file = {}

    for i, s in enumerate(summaries, 1):
        if not s.get('success') or not s.get('text_file'):
            continue
        text_path = Path(s['text_file'])
        if not text_path.exists():
            continue

        meta = get_file_meta(text_path.stem)
        meta['slice'] = text_path.stem + '.pdf'

        with open(text_path, encoding='utf-8') as f:
            lines = [normalize(l) for l in f.readlines()]

        print(f'  [{i}/{len(summaries)}] {text_path.name} (tome {meta["tome"]}, {meta["dict_type"]})', end='', flush=True)

        if meta['dict_type'] == 'wallon-francais':
            entries = parse_tome2(lines, meta)
        else:
            entries = parse_tome3(lines, meta)

        print(f' -> {len(entries)} entrees')
        per_file[text_path.stem] = len(entries)
        all_entries.extend(entries)

    print(f'\nTotal brut: {len(all_entries)}')
    final = deduplicate(all_entries)
    
    wf = sum(1 for e in final if e['type'] == 'wallon-francais')
    fw = sum(1 for e in final if e['type'] == 'francais-wallon')
    print(f'Apres deduplication: {len(final)} entrees')
    print(f'  Wallon->Francais : {wf}')
    print(f'  Francais->Wallon : {fw}')

    out = PARSED_DIR / 'all_entries_raw.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    stats = PARSED_DIR / 'per_file_stats.json'
    with open(stats, 'w', encoding='utf-8') as f:
        json.dump(per_file, f, ensure_ascii=False, indent=2)

    print(f'\nDonnees sauvees: {out}')
    return final


if __name__ == '__main__':
    print('=' * 70)
    print('  LI PTIT MOTI WALON -- Etape 3 v2 : Parsing ameliore')
    print('=' * 70)
    process_all()
