"""
Correction finale v3: corriger les mots avec å dans les DÉFINITIONS aussi,
pas seulement dans les mots-vedettes.

Les mots wallons avec å apparaissent dans les définitions sous forme de
renvois (voy. abalowe, etc.) où le å a été perdu.
On corrige aussi bien le champ 'word' que 'definition'.
"""
import json, os, re

PROJ     = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
MAP_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_clean.json')
DICO_IN  = os.path.join(PROJ, 'dico.json')
DICO_OUT = os.path.join(PROJ, 'dico.json')
RAPPORT  = os.path.join(PROJ, 'extraction', 'rapport_corrections_final.json')

with open(MAP_FILE, encoding='utf-8') as f:
    data = json.load(f)
mapping = data["mapping"]   # {sans_å_lower: avec_å}

# Ne garder que les mots >= 4 chars pour éviter les faux positifs
# (ex: 'ame', 'are', 'abe' sont trop communs en français)
mapping_safe = {k: v for k, v in mapping.items() if len(k) >= 4}
# Exceptions: mots très spécifiques au wallon qu'on peut corriger
# même s'ils sont courts
wallon_specific_short = {
    'åme', 'åbe', 'åre', 'åwe', 'åye', 'ågne'
}
for w in wallon_specific_short:
    k = w.replace('å', 'a')
    mapping_safe[k] = w  # ajouter quand même

print(f"Mapping sûr: {len(mapping_safe)} entrées (>= 4 chars + exceptions)")

# Construire le pattern regex: chercher les mots exacts (boundary \b)
# On trie par longueur décroissante pour éviter les remplacements partiels
sorted_keys = sorted(mapping_safe.keys(), key=len, reverse=True)

def correct_text(text):
    """Applique les corrections å sur un texte, mot entier uniquement."""
    if not text:
        return text, []
    applied = []
    result = text
    for key in sorted_keys:
        val = mapping_safe[key]
        # Chercher le mot entier (insensible à la casse)
        # \b ne fonctionne pas bien avec les caractères non-ASCII, on utilise
        # un pattern plus large: lookbehind/ahead sur séparateurs
        pattern = re.compile(
            r'(?<![a-zA-ZàâéèêëîïôùûüçœæÀÂÉÈÊËÎÏÔÙÛÜÇŒÆ])' +
            re.escape(key) +
            r'(?![a-zA-ZàâéèêëîïôùûüçœæÀÂÉÈÊËÎÏÔÙÛÜÇŒÆ])',
            re.IGNORECASE
        )
        new_result = pattern.sub(val, result)
        if new_result != result:
            applied.append((key, val))
            result = new_result
    return result, applied

# Charger et corriger le dico
with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)

print(f"Dico: {len(dico)} entrées\n")

corrections_word = []
corrections_def  = []
dico_corr = []

for entry in dico:
    new_entry = dict(entry)

    # Corriger le mot-vedette
    word = entry.get('word', '')
    new_word, applied_w = correct_text(word)
    if applied_w:
        new_entry['word'] = new_word
        corrections_word.append({
            'original': word, 'corrected': new_word,
            'changes': applied_w,
            'tome': entry.get('tome'), 'page': entry.get('page')
        })

    # Corriger la définition
    defn = entry.get('definition', '')
    new_defn, applied_d = correct_text(defn)
    if applied_d:
        new_entry['definition'] = new_defn
        corrections_def.append({
            'word': new_word,
            'changes': applied_d,
            'tome': entry.get('tome'), 'page': entry.get('page')
        })

    dico_corr.append(new_entry)

# Rapport
total = len(corrections_word) + len(corrections_def)
print(f"{'='*60}")
print(f"CORRECTIONS mot-vedette : {len(corrections_word)}")
print(f"CORRECTIONS définitions : {len(corrections_def)}")
print(f"TOTAL                   : {total}")
print(f"{'='*60}")

if corrections_word:
    print("\n--- Corrections mots-vedettes ---")
    for c in corrections_word:
        print(f"  {repr(c['original'][:50])} -> {repr(c['corrected'][:50])}")
        print(f"     [tome {c['tome']}, p.{c['page']}]")

if corrections_def:
    print(f"\n--- Exemples corrections définitions (10 premiers) ---")
    for c in corrections_def[:10]:
        print(f"  Mot: {repr(c['word'][:40])}, changements: {c['changes']}")

# Sauvegarder
with open(DICO_OUT, 'w', encoding='utf-8') as f:
    json.dump(dico_corr, f, ensure_ascii=False, indent=2)
print(f"\n✅ dico.json mis à jour")

with open(RAPPORT, 'w', encoding='utf-8') as f:
    json.dump({
        'corrections_word': len(corrections_word),
        'corrections_definition': len(corrections_def),
        'total': total,
        'details_word': corrections_word,
        'details_def': corrections_def[:200]
    }, f, ensure_ascii=False, indent=2)
print(f"📋 Rapport sauvegardé")
