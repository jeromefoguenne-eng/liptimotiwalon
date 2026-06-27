import json, os
PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
with open(os.path.join(PROJ, 'dico.json'), encoding='utf-8') as f:
    dico = json.load(f)

hits = [e for e in dico if 'abalow' in e.get('word','').lower() or 'abalow' in e.get('definition','').lower()]
print(f'Entrees avec abalow: {len(hits)}')
for h in hits[:5]:
    w = h["word"][:60]
    d = h["definition"][:100]
    print(f'  word: {repr(w)}')
    print(f'  def:  {repr(d)}')
    print()

# Aussi chercher abastri
hits2 = [e for e in dico if 'abastr' in e.get('word','').lower() or 'abastr' in e.get('definition','').lower()]
print(f'Entrees avec abastri: {len(hits2)}')
for h in hits2[:3]:
    w = h["word"][:60]
    d = h["definition"][:100]
    print(f'  word: {repr(w)}')
    print(f'  def:  {repr(d)}')
