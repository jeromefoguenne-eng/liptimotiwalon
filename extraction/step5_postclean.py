#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post-traitement : nettoyage final du dico.json
- Supprime les artefacts d'encodage (symbole £ U+00A3)
- Corrige les mots Tome 3 qui ont absorbe leur traduction wallon
- Filtre les mots commencant par des parentheses ou fragments parasites
- Normalise les em-dashes parasites en debut de definition
"""
import sys, json, re, unicodedata, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DICO = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/dico.json')

with open(DICO, encoding='utf-8') as f:
    entries = json.load(f)

print(f'Entrees avant nettoyage: {len(entries)}')

# Caracteres wallons typiques dans les equivalents
WALLON_ACCENT = re.compile(r'[âôûîèêëœæ]', re.U)

def clean_entry(e: dict) -> dict | None:
    word = e.get('word', '').strip()
    defn = e.get('definition', '').strip()
    dtype = e.get('type', 'wallon-francais')

    # --- Filtre: mot commence par parenthese ou signe parasite ---
    if re.match(r'^[\(\[\-\—\*\#\d]', word):
        return None

    # --- Filtre: mot trop court ou trop long ---
    if len(word) < 2 or len(word) > 80:
        return None

    # --- Nettoyer artefacts £ (U+00A3) -> e (souvent 'é' mal encode) ---
    word = word.replace('\u00a3', 'e')
    defn = defn.replace('\u00a3', 'e')

    # --- Normaliser NFC ---
    word = unicodedata.normalize('NFC', word)
    defn = unicodedata.normalize('NFC', defn)

    # --- Tome 3 (fr->wallon): extraire le mot propre si wallon colle ---
    # Exemple: "agacerie agacerèye" -> mot="agacerie", def="agacerèye ..."
    if dtype == 'francais-wallon':
        # Le mot ne devrait pas contenir de caracteres wallons accentues
        # Si le mot en contient, c'est que la traduction wallon y est collee
        parts = word.split()
        if len(parts) >= 2 and WALLON_ACCENT.search(parts[-1]):
            # Le dernier token est wallon -> le mettre dans la def
            true_word = ' '.join(parts[:-1])
            wallon_part = parts[-1]
            if len(true_word) >= 2:
                word = true_word
                defn = wallon_part + (' ' + defn if defn else '')

    # --- Nettoyer debut de definition (em-dash, points parasites) ---
    defn = re.sub(r'^[\—\-\.\;\,\s]+', '', defn).strip()

    # --- Filtre definition trop courte apres nettoyage ---
    if len(defn) < 3:
        return None

    # --- Filtre: definition identique au mot ---
    if word.lower() == defn.lower()[:len(word)]:
        pass  # Peut etre valide (definition commence par le mot)

    return {
        'word': word,
        'definition': defn,
        'type': dtype,
        'tome': e.get('tome', 0),
        'page': e.get('page', 0),
        'slice': e.get('slice', '')
    }

cleaned = []
removed = 0
for e in entries:
    result = clean_entry(e)
    if result:
        cleaned.append(result)
    else:
        removed += 1

# Deduplication finale
seen = {}
for e in cleaned:
    key = (unicodedata.normalize('NFD', e['word'].lower()), e['type'])
    if key not in seen or len(e['definition']) > len(seen[key]['definition']):
        seen[key] = e

final = list(seen.values())
final.sort(key=lambda x: unicodedata.normalize('NFD', x['word'].lower()))

print(f'Entrees supprimees: {removed}')
print(f'Apres deduplication finale: {len(final)}')

# Verifier artefacts restants
pound = sum(1 for e in final if '\u00a3' in e['word'] + e['definition'])
print(f'Artefacts £ restants: {pound}')

wf = sum(1 for e in final if e['type'] == 'wallon-francais')
fw = sum(1 for e in final if e['type'] == 'francais-wallon')
print(f'Wallon->Francais: {wf:,}')
print(f'Francais->Wallon: {fw:,}')

# Exemples corriges T3
print()
print('=== EXEMPLES FRANCAIS->WALLON (apres correction) ===')
fw_entries = [e for e in final if e['type'] == 'francais-wallon']
for e in fw_entries[50:55]:
    mot = e.get('word', '')
    defn = e.get('definition', '')[:80]
    print(f'  {mot:30s} : {defn}')

# Sauvegarder
shutil.copy2(DICO, str(DICO).replace('dico.json', 'dico_pre_clean.json'))
with open(DICO, 'w', encoding='utf-8') as f:
    json.dump(final, f, ensure_ascii=False, indent=2)

size_mb = DICO.stat().st_size / 1024 / 1024
print(f'\nSauvegarde: {DICO} ({size_mb:.1f} MB)')
