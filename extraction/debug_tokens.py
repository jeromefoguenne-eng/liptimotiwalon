"""Debug: comprendre pourquoi les tokens ne matchent pas."""
import json, os, re

PROJ    = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
MAP_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_clean.json')
DICO_IN  = os.path.join(PROJ, 'dico.json')

with open(MAP_FILE, encoding='utf-8') as f:
    mapping = json.load(f)["mapping"]

with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)

# Chercher des entrées qui contiennent "abalowe", "abitude", "ame", "ardjint"
test_keys = ['abalowe', 'abitude', 'ame', 'ardjint', 'alouwete', 'arnesse']

for key in test_keys:
    hits = [e for e in dico if key in e.get('word', '').lower()]
    print(f"\n=== '{key}' dans dico ({len(hits)} entrées) ===")
    for h in hits[:3]:
        w = h.get('word', '')
        print(f"  word: {repr(w[:70])}")
        # Tester l'extraction du premier token
        word_no_num = re.sub(r'^\d+\.\s*', '', w)
        tokens = re.split(r'[\s,;:()\[\]\.!?\\/\'\"«»]', word_no_num.strip())
        first = next((t for t in tokens if t), '').lower()
        print(f"  first_token: {repr(first)}")
        print(f"  in mapping: {first in mapping}")

# Aussi afficher les 20 premiers mots du dico pour voir le format
print("\n=== 20 premiers mots (triés) ===")
all_words = sorted(e.get('word', '') for e in dico)
for w in all_words[:20]:
    word_no_num = re.sub(r'^\d+\.\s*', '', w)
    tokens = re.split(r'[\s,;:()\[\]\.!?\\/\'\"«»]', word_no_num.strip())
    first = next((t for t in tokens if t), '').lower()
    print(f"  {repr(w[:50])} -> first_token={repr(first)}")
