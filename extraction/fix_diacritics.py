"""
Correction des diacritiques wallons dans dico.json.

Stratégie: Le 'å' wallon (a avec rond en chef) apparaît dans des mots spécifiques du
dialecte liégeois. On utilise une liste de référence des mots connus avec å pour corriger
automatiquement le dico.json.

Sources de référence:
- Jean Haust, Dictionnaire Liégeois (DL), 1929-1933
- Les mots en å typiques du liégeois
"""
import json, re, os

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'

# ============================================================
# DICTIONNAIRE DE CORRECTIONS: formes sans diacritique -> avec
# Basé sur les mots wallons liégeois connus avec å (a-ring)
# ============================================================

# Mots-vedettes du DL avec å (extrait du livre physique)
# Format: "forme_sans_diacritique": "forme_correcte"
CORRECTIONS_A_ROND = {
    # Mots commençant par å (extrait visuel du scan)
    "abalowe": "åbalowe",
    "abastri": "åbastri",
    "abastrèye": "åbastrèye",
    "abastrir": "åbastrir",
    "abèye": "åbèye",
    # Ajouter au fur et à mesure des vérifications
}

# ============================================================
# ANALYSE: trouver TOUS les mots suspects dans le dico
# qui correspondent à des patterns å connus en wallon liégeois
# ============================================================

with open(os.path.join(PROJ, 'dico.json'), encoding='utf-8') as f:
    dico = json.load(f)

print(f"Total entrées: {len(dico)}")

# Chercher les mots qui matchent nos corrections
corrections_appliquees = []
for entry in dico:
    word = entry.get('word', '')
    word_lower = word.lower().strip()
    for bad, good in CORRECTIONS_A_ROND.items():
        if word_lower == bad or word_lower.startswith(bad + ' ') or word_lower.startswith(bad + ','):
            corrections_appliquees.append((word, good, bad))
            print(f"  MATCH: '{word}' -> '{good}'")

print(f"\nCorrections trouvées: {len(corrections_appliquees)}")

# Afficher aussi les premiers mots du dico pour repérer d'autres candidats
print("\n=== Premiers 50 mots du dico (ordre alphabétique) ===")
sorted_words = sorted(set(e.get('word','').strip() for e in dico))
for w in sorted_words[:50]:
    print(f"  {w}")
