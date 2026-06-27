import json
with open('dico_test.json', encoding='utf-8') as f:
    dico = json.load(f)

print('=== 20 premieres entrees ===')
for e in dico[:20]:
    t = e.get('tome','?')
    p = e.get('page','?')
    w = e.get('word','')[:35]
    d = e.get('definition','')[:55]
    print(f'  [T{t}p{p}] {repr(w):40s} | {repr(d)}')

print()
print('=== Entrees needs_review ===')
for e in dico:
    if e.get('needs_review'):
        w = e.get('word','')[:50]
        d = e.get('definition','')[:50]
        print(f'  {repr(w)} | {repr(d)}')

print()
print('=== Entrees def vide ===')
for e in dico:
    if not e.get('definition','').strip():
        w = e.get('word','')[:50]
        print(f'  {repr(w)}')
