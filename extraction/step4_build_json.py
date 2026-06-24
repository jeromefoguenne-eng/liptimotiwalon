#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Etape 4 : Validation par Gemma 4 (Ollama local) + generation du dico.json final.
Format de sortie compatible avec app.js : [{word, definition, type, tome, page, slice}]
"""

import sys
import json
import re
import time
import unicodedata
import requests
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/extraction')
PARSED_DIR = BASE / 'parsed'
OUTPUT = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/dico.json')
BACKUP = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/dico_backup_old.json')

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'gemma4:latest'  # Leger et rapide pour la validation

def ollama_ok() -> bool:
    try:
        r = requests.get('http://localhost:11434/api/tags', timeout=5)
        return r.status_code == 200
    except:
        return False

def validate_batch(batch: list[dict]) -> list[bool]:
    """Valide 10 entrees avec Gemma 4. Retourne True=valide, False=bruit."""
    lines = []
    for i, e in enumerate(batch, 1):
        w = e['word'][:40]
        d = e['definition'][:60]
        lines.append(f'{i}. MOT: "{w}" | DEF: "{d}"')
    prompt = (
        'Tu es expert en dictionnaires wallons-liegeois. '
        'Pour chaque entree ci-dessous, reponds VALIDE ou BRUIT '
        '(BRUIT = en-tete, numero de page, separateur, texte non-lexical).\n'
        'Format: "1. VALIDE" ou "1. BRUIT" uniquement.\n\n'
        + '\n'.join(lines)
        + '\n\nReponse:'
    )
    try:
        r = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'temperature': 0.05, 'num_predict': 150}
        }, timeout=90)
        response = r.json().get('response', '')
        results = [True] * len(batch)
        for line in response.splitlines():
            m = re.match(r'(\d+)\.\s*(VALIDE|BRUIT)', line.strip(), re.I)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(batch):
                    results[idx] = m.group(2).upper() == 'VALIDE'
        return results
    except Exception as e:
        print(f'   [WARN] Ollama erreur: {e}')
        return [True] * len(batch)

NOISE_PATTERNS = [
    re.compile(r'^\d+$'),
    re.compile(r'^[IVXivx]{1,5}$'),
    re.compile(r'^[=\-\*\.]{3,}$'),
    re.compile(r'^(table|index|bibliographie|avant-propos|introduction|corrections?|additions?)', re.I),
    re.compile(r'^(tome|vol\.?|fig\.?)\s+\d', re.I),
]

def fast_noise_filter(entries: list[dict]) -> list[dict]:
    """Filtrage rapide par regex avant validation Ollama."""
    clean = []
    for e in entries:
        w = e['word'].strip()
        d = e['definition'].strip()
        if not w or not d:
            continue
        if len(w) < 2 or len(w) > 100:
            continue
        if len(d) < 3:
            continue
        if w.lower() == d.lower():
            continue
        is_noise = False
        for pat in NOISE_PATTERNS:
            if pat.match(w):
                is_noise = True
                break
        if not is_noise:
            clean.append(e)
    return clean

def build_json():
    parsed_path = PARSED_DIR / 'all_entries_raw.json'
    if not parsed_path.exists():
        print('[ERREUR] all_entries_raw.json introuvable. Lancez step3_parse.py')
        sys.exit(1)

    with open(parsed_path, encoding='utf-8') as f:
        raw = json.load(f)
    print(f'Entrees chargees: {len(raw)}')

    # Filtrage rapide
    cleaned = fast_noise_filter(raw)
    removed = len(raw) - len(cleaned)
    print(f'Apres filtre rapide: {len(cleaned)} (retire {removed} bruits)')

    # Validation Ollama (Gemma 4)
    final = cleaned
    if ollama_ok():
        print(f'\nValidation Gemma 4 ({MODEL})...')
        validated = []
        BATCH = 10

        # Sur grands corpus, echantillonner les zones a risque (debut/fin)
        if len(cleaned) > 8000:
            print(f'  Grand corpus ({len(cleaned)}) - validation echantillon 1000 entrees')
            sample_n = 500
            to_validate = cleaned[:sample_n] + cleaned[-sample_n:]
            middle = cleaned[sample_n:-sample_n]
            for i in range(0, len(to_validate), BATCH):
                b = to_validate[i:i+BATCH]
                results = validate_batch(b)
                validated.extend([e for e, ok in zip(b, results) if ok])
                if (i // BATCH) % 20 == 0:
                    pct = (i + BATCH) / len(to_validate) * 100
                    print(f'  {pct:.0f}%...', end='\r', flush=True)
            validated.extend(middle)
        else:
            for i in range(0, len(cleaned), BATCH):
                b = cleaned[i:i+BATCH]
                results = validate_batch(b)
                validated.extend([e for e, ok in zip(b, results) if ok])
                if (i // BATCH) % 20 == 0:
                    pct = (i + BATCH) / len(cleaned) * 100
                    print(f'  {pct:.0f}%...', end='\r', flush=True)

        print(f'\nApres validation Gemma 4: {len(validated)} entrees')
        final = validated
    else:
        print('[WARN] Ollama non disponible - validation ignoree')

    # Normalisation finale NFC
    for e in final:
        e['word'] = unicodedata.normalize('NFC', e['word'])
        e['definition'] = unicodedata.normalize('NFC', e['definition'])

    # Tri alphabetique wallon (insensible aux accents)
    final.sort(key=lambda x: unicodedata.normalize('NFD', x['word'].lower()))

    # Backup de l'ancien dico.json
    if OUTPUT.exists():
        import shutil
        shutil.copy2(OUTPUT, BACKUP)
        print(f'Backup: {BACKUP}')

    # Sauvegarde du nouveau dico.json
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    wf = sum(1 for e in final if e['type'] == 'wallon-francais')
    fw = sum(1 for e in final if e['type'] == 'francais-wallon')

    print(f'\n{"="*70}')
    print(f'  TERMINE!')
    print(f'  Entrees totales   : {len(final):,}')
    print(f'  Wallon->Francais  : {wf:,}')
    print(f'  Francais->Wallon  : {fw:,}')
    print(f'  Taille dico.json  : {size_mb:.1f} MB')
    print(f'  Fichier           : {OUTPUT}')
    print(f'{"="*70}')

if __name__ == '__main__':
    print('=' * 70)
    print('  LI PTIT MOTI WALON -- Etape 4 : Build dico.json')
    print('=' * 70)
    build_json()
