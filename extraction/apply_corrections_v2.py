"""
Correction chirurgicale : uniquement les mots communs wallons avec å,
correspondance sur le MOT ENTIER uniquement (pas sous-chaîne).

La liste wa.wiktionary contient beaucoup de noms propres et de suffixes.
On filtre pour ne garder que les mots communs utiles.
"""
import json, os, re

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
DICO_IN  = os.path.join(PROJ, 'dico.json')
DICO_OUT = os.path.join(PROJ, 'dico_corrected.json')
REF_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_reference.json')
RAPPORT  = os.path.join(PROJ, 'extraction', 'rapport_corrections_a_rond.json')

# ============================================================
# CHARGER ET FILTRER LA RÉFÉRENCE
# ============================================================

with open(REF_FILE, encoding='utf-8') as f:
    reference_words = json.load(f)

# Filtrer: garder uniquement les mots communs (minuscule, longueur >= 3, pas de suffixe)
# Exclure: noms propres (majuscule), suffixes (-xxx), expressions trop longues
common_words = []
for w in reference_words:
    # Exclure suffixes/préfixes (commencent par - ou sont très courts)
    if w.startswith('-') or w.startswith('Å') or len(w) < 3:
        continue
    # Exclure noms propres (commence par majuscule) SAUF si le å est clairement dans un mot commun
    # On garde les mots qui commencent par å (minuscule)
    if w[0].isupper() and 'å' not in w.lower():
        continue
    # Exclure les expressions trop longues (phrases)
    if len(w.split()) > 3:
        continue
    # Le mot doit contenir un å
    if 'å' not in w and 'Å' not in w:
        continue
    common_words.append(w)

print(f"Référence totale: {len(reference_words)}")
print(f"Mots communs filtrés: {len(common_words)}")
print("\nMots communs retenus:")
for w in sorted(common_words)[:60]:
    print(f"  {w}")

# Construire le mapping: forme_sans_å (lowercase) -> forme_avec_å
# UNIQUEMENT correspondance exacte sur mot entier
mapping = {}
for w in common_words:
    key = w.lower().replace('å', 'a').replace('Å', 'A')
    if key not in mapping:
        mapping[key] = w

print(f"\nMapping exact: {len(mapping)} entrées")

# ============================================================
# CHARGER LE DICO
# ============================================================

with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)

print(f"Dico: {len(dico)} entrées")

# ============================================================
# APPLIQUER LES CORRECTIONS - CORRESPONDANCE EXACTE SEULEMENT
# ============================================================

corrections = []
dico_corr = []

for entry in dico:
    new_entry = dict(entry)
    word = entry.get('word', '').strip()
    
    # Extraire le(s) mot(s) vedette(s)
    # Supprimer les numéros en début (ex: "1. balowe" ou "2. balowe")
    word_clean = re.sub(r'^\d+\.\s*', '', word)
    
    # Prendre le premier token significatif
    # (avant virgule, parenthèse, espace, point)
    first_token = re.split(r'[\s,;:()\[\]\.!?/]', word_clean.strip())[0].lower()
    
    corrected = False
    
    # Correspondance exacte sur le premier mot
    if first_token in mapping and len(first_token) >= 3:
        correct_form = mapping[first_token]
        # Remplacer dans le mot original (conserver la casse du reste)
        # Chercher first_token au début du word_clean (insensible à la casse)
        pattern = re.compile(r'^(\d+\.\s*)?' + re.escape(first_token), re.IGNORECASE)
        new_word = pattern.sub(lambda m: (m.group(1) or '') + correct_form, word)
        
        if new_word != word:
            new_entry['word'] = new_word
            corrections.append({
                'original': word,
                'corrected': new_word,
                'matched_token': first_token,
                'correct_form': correct_form,
                'tome': entry.get('tome'),
                'page': entry.get('page'),
                'slice': entry.get('slice')
            })
            corrected = True
    
    dico_corr.append(new_entry)

# ============================================================
# RAPPORT
# ============================================================

print(f"\n{'='*60}")
print(f"CORRECTIONS APPLIQUÉES: {len(corrections)}")
print(f"{'='*60}")
for c in corrections:
    print(f"  '{c['original'][:50]}' -> '{c['corrected'][:50]}'")
    print(f"     token='{c['matched_token']}' -> '{c['correct_form']}'")
    print(f"     tome {c['tome']}, page {c['page']}")
    print()

# Sauvegarder
with open(DICO_OUT, 'w', encoding='utf-8') as f:
    json.dump(dico_corr, f, ensure_ascii=False, indent=2)
print(f"Dico corrigé sauvegardé: {DICO_OUT}")

with open(RAPPORT, 'w', encoding='utf-8') as f:
    json.dump({
        'total_corrections': len(corrections),
        'total_entries': len(dico),
        'reference_words_used': len(common_words),
        'corrections': corrections
    }, f, ensure_ascii=False, indent=2)
print(f"Rapport: {RAPPORT}")
