#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, unicodedata
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

new = json.load(open('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/dico.json', encoding='utf-8'))
old = json.load(open('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/dico_backup_old.json', encoding='utf-8'))

print('=== COMPARAISON ANCIEN vs NOUVEAU DICO.JSON ===')
print()
print(f'Ancien : {len(old):>6,} entrees')
print(f'Nouveau: {len(new):>6,} entrees (UTF-8 propre, parsing ameliore)')
print()

wf = [e for e in new if e['type'] == 'wallon-francais']
fw = [e for e in new if e['type'] == 'francais-wallon']
print(f'  Wallon->Francais : {len(wf):,}')
print(f'  Francais->Wallon : {len(fw):,}')
print()

# Verifier les accents
chars = {}
for e in new:
    w = e.get('word', '')
    d = e.get('definition', '')
    for ch in w + d:
        if ord(ch) > 127:
            chars[ch] = chars.get(ch, 0) + 1

print('=== CARACTERES SPECIAUX (top 15) ===')
for ch, cnt in sorted(chars.items(), key=lambda x: -x[1])[:15]:
    name = unicodedata.name(ch, '?')[:30]
    print(f'  {repr(ch):5s} U+{ord(ch):04X}  x{cnt:6,}  {name}')
print()

# Exemples wallon->fr
print('=== EXEMPLES WALLON->FRANCAIS ===')
for e in wf[100:105]:
    mot = e.get('word', '')
    defn = e.get('definition', '')[:100]
    print(f'  MOT: {mot}')
    print(f'  DEF: {defn}')
    print()

# Exemples fr->wallon
print('=== EXEMPLES FRANCAIS->WALLON ===')
for e in fw[50:55]:
    mot = e.get('word', '')
    defn = e.get('definition', '')[:100]
    print(f'  MOT: {mot}')
    print(f'  DEF: {defn}')
    print()

# Artefacts d'encodage
pound = sum(1 for e in new if chr(0x00A3) in e.get('word','') + e.get('definition',''))
print(f'Artefacts encodage (symbole livre U+00A3): {pound} (0 = parfait)')

# Entrees vides ou suspectes
short_def = sum(1 for e in new if len(e.get('definition','')) < 5)
print(f'Definitions tres courtes (<5 chars)      : {short_def}')

# Longueur moyenne des definitions
avg_def = sum(len(e.get('definition','')) for e in new) / len(new)
print(f'Longueur moyenne definition              : {avg_def:.0f} chars')
