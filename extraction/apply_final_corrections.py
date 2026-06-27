"""
Correction finale et sûre des diacritiques å dans dico.json.
Utilise le mapping propre issu de wa.wiktionary (correspondance exacte sur premier mot).
"""
import json, os, re

PROJ    = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
DICO_IN  = os.path.join(PROJ, 'dico.json')
DICO_OUT = os.path.join(PROJ, 'dico.json')          # Écraser l'original
RAPPORT  = os.path.join(PROJ, 'extraction', 'rapport_corrections_final.json')
MAP_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_clean.json')

# ============================================================
# Charger le mapping
# ============================================================
with open(MAP_FILE, encoding='utf-8') as f:
    data = json.load(f)

mapping = data["mapping"]  # {forme_sans_å: forme_avec_å}

# Filtrer: exclure les mots trop courts (< 3 chars) pour éviter les faux positifs
# ex: 'ad' -> 'åd' pourrait corriger des mots français "ad-"
mapping_safe = {k: v for k, v in mapping.items() if len(k) >= 3}

print(f"Mapping chargé: {len(mapping)} entrées, {len(mapping_safe)} sûres (>=3 chars)")
print("Mapping utilisé:")
for k, v in sorted(mapping_safe.items()):
    print(f"  '{k}' -> '{v}'")

# ============================================================
# Charger le dico
# ============================================================
with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)
print(f"\nDico chargé: {len(dico)} entrées")

# ============================================================
# Appliquer les corrections
# ============================================================
corrections = []
dico_corr = []

for entry in dico:
    new_entry = dict(entry)
    word = entry.get('word', '').strip()

    # Normaliser: enlever numéro initial "1. " ou "2. "
    word_no_num = re.sub(r'^\d+\.\s*', '', word)

    # Extraire le premier token (mot vedette principal)
    # On split sur les séparateurs habituels
    tokens = re.split(r'[\s,;:()\[\]\.!?\\/\'"«»]', word_no_num.strip())
    first_token = next((t for t in tokens if t), '').lower()

    if len(first_token) >= 3 and first_token in mapping_safe:
        correct_form = mapping_safe[first_token]

        # Construire le nouveau mot: remplacer le premier token
        # en préservant la casse et les suffixes
        def replace_first_token(original_word, old_token, new_token):
            """Remplace le premier token dans le mot original (insensible à la casse)."""
            pattern = re.compile(
                r'^(\d+\.\s*)?' + re.escape(old_token),
                re.IGNORECASE
            )
            def replacer(m):
                prefix = m.group(1) if m.lastindex else ''
                return (prefix or '') + new_token
            return pattern.sub(replacer, original_word, count=1)

        new_word = replace_first_token(word, first_token, correct_form)

        if new_word != word:
            new_entry['word'] = new_word
            corrections.append({
                'original': word,
                'corrected': new_word,
                'token': first_token,
                'correct_form': correct_form,
                'tome': entry.get('tome'),
                'page': entry.get('page'),
                'slice': entry.get('slice')
            })

    dico_corr.append(new_entry)

# ============================================================
# Rapport
# ============================================================
print(f"\n{'='*60}")
print(f"CORRECTIONS APPLIQUÉES: {len(corrections)} / {len(dico)} entrées")
print(f"{'='*60}")
for c in corrections:
    orig = c['original'][:55]
    corr = c['corrected'][:55]
    print(f"  '{orig}' -> '{corr}'  [tome {c['tome']}, p.{c['page']}]")

# Sauvegarder le dico corrigé (remplace l'original)
with open(DICO_OUT, 'w', encoding='utf-8') as f:
    json.dump(dico_corr, f, ensure_ascii=False, indent=2)
print(f"\n✅ dico.json mis à jour: {DICO_OUT}")

# Rapport de corrections
with open(RAPPORT, 'w', encoding='utf-8') as f:
    json.dump({
        'total_corrections': len(corrections),
        'total_entries': len(dico),
        'mapping_size': len(mapping_safe),
        'corrections': corrections
    }, f, ensure_ascii=False, indent=2)
print(f"📋 Rapport: {RAPPORT}")
