"""
Correction des diacritiques å dans dico.json.

Après avoir récupéré la liste de référence des mots wallons avec å depuis
wa.wiktionary.org, on applique les corrections sur dico.json.

Algorithme:
1. Charger la liste de référence (wallon_a_rond_reference.json)
2. Construire un dictionnaire de mapping: forme_sans_å -> forme_avec_å
3. Pour chaque entrée du dico, comparer le mot (sans å) avec le mapping
4. Appliquer la correction si match trouvé
5. Sauvegarder dico_corrected.json + rapport de corrections
"""
import json, os, re, unicodedata

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
DICO_IN  = os.path.join(PROJ, 'dico.json')
DICO_OUT = os.path.join(PROJ, 'dico_corrected.json')
REF_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_reference.json')
RAPPORT  = os.path.join(PROJ, 'extraction', 'rapport_corrections_a_rond.json')

def strip_a_ring(text):
    """Remplace å/Å par a/A pour comparaison."""
    return text.replace('å', 'a').replace('Å', 'A')

def normalize_for_lookup(word):
    """Normalise un mot pour la comparaison (minuscules, strip)."""
    return strip_a_ring(word.lower().strip())

# ============================================================
# CHARGER LA RÉFÉRENCE
# ============================================================

if not os.path.exists(REF_FILE):
    print(f"ERREUR: Fichier de référence non trouvé: {REF_FILE}")
    print("Lancez d'abord scrape_wallon_complet.py")
    exit(1)

with open(REF_FILE, encoding='utf-8') as f:
    reference_words = json.load(f)

print(f"Référence chargée: {len(reference_words)} mots")

# Construire le mapping: forme_sans_å (lowercase) -> forme_avec_å
mapping = {}
for w in reference_words:
    if 'å' in w or 'Å' in w:
        key = normalize_for_lookup(w)
        # Garder le plus court si plusieurs matchent (éviter les expressions composées)
        if key not in mapping or len(w) < len(mapping[key]):
            mapping[key] = w

print(f"Mapping construit: {len(mapping)} entrées")
print("Exemples:")
for k, v in list(mapping.items())[:15]:
    print(f"  '{k}' -> '{v}'")

# ============================================================
# CHARGER LE DICO
# ============================================================

with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)

print(f"\nDico chargé: {len(dico)} entrées")

# ============================================================
# APPLIQUER LES CORRECTIONS
# ============================================================

corrections = []
dico_corr = []

for entry in dico:
    new_entry = dict(entry)
    word = entry.get('word', '')
    
    # Essayer de trouver le mot dans le mapping
    # On extrait le premier "vrai mot" (avant virgule, parenthèse, espace)
    # car certains mots-vedettes ont des variantes: "abalowe, abastri, f."
    
    # Nettoyer le mot: prendre jusqu'à la première ponctuation
    word_clean = re.split(r'[\s,;:()\[\]\.!?]', word.strip())[0].lower()
    
    corrected = False
    
    # Chercher dans le mapping
    if word_clean in mapping:
        correct_form = mapping[word_clean]
        # Appliquer: remplacer la partie initiale du mot
        new_word = word.replace(word_clean, correct_form, 1)
        if new_word != word:
            new_entry['word'] = new_word
            corrections.append({
                'original': word,
                'corrected': new_word,
                'source': 'wa.wiktionary',
                'tome': entry.get('tome'),
                'page': entry.get('page')
            })
            corrected = True
    
    # Aussi chercher dans le mot complet (expressions)
    if not corrected:
        for key, val in mapping.items():
            if key in word.lower() and key != normalize_for_lookup(word)[:len(key)]:
                # Le mot contient une forme sans å au milieu
                # Remplacer prudemment
                pattern = re.compile(re.escape(key), re.IGNORECASE)
                new_word = pattern.sub(val, word, count=1)
                if new_word != word:
                    new_entry['word'] = new_word
                    corrections.append({
                        'original': word,
                        'corrected': new_word,
                        'source': 'wa.wiktionary (milieu)',
                        'key': key,
                        'val': val
                    })
                    corrected = True
                    break
    
    dico_corr.append(new_entry)

# ============================================================
# RAPPORT
# ============================================================

print(f"\n{'='*60}")
print(f"CORRECTIONS APPLIQUÉES: {len(corrections)}")
print(f"{'='*60}")
for c in corrections[:30]:
    print(f"  {repr(c['original'][:40])} -> {repr(c['corrected'][:40])}")

# Sauvegarder le dico corrigé
with open(DICO_OUT, 'w', encoding='utf-8') as f:
    json.dump(dico_corr, f, ensure_ascii=False, indent=2)
print(f"\nDico corrigé sauvegardé: {DICO_OUT}")

# Sauvegarder le rapport
with open(RAPPORT, 'w', encoding='utf-8') as f:
    json.dump({
        'total_corrections': len(corrections),
        'total_entries': len(dico),
        'corrections': corrections
    }, f, ensure_ascii=False, indent=2)
print(f"Rapport sauvegardé: {RAPPORT}")
