import json, sys, fitz
sys.path.insert(0, 'extraction')
from extract_v2 import extract_columns
from parse_entries_v2 import parse_column_entries

with open('dico_test.json', encoding='utf-8') as f:
    dico = json.load(f)

print(f'Total: {len(dico)} entrees')
print()
print('=== 10 premieres entrees ===')
for e in dico[:10]:
    t = e.get('tome','?')
    p = e.get('page','?')
    w = e.get('word','')[:40]
    d = e.get('definition','')[:60]
    print(f'  [T{t}/p{p}] {repr(w)} | {repr(d)}')

print()
revs = [e for e in dico if e.get('needs_review')]
print(f'=== needs_review: {len(revs)} ===')
for e in revs[:5]:
    print(f'  {repr(e.get("word","")[:50])}')

empties = [e for e in dico if not e.get('word','').strip() or not e.get('definition','').strip()]
print(f'\n=== Entrees vides: {len(empties)} ===')
for e in empties[:5]:
    w = e.get('word','')[:40]
    d = e.get('definition','')[:40]
    print(f'  word={repr(w)} def={repr(d)}')

# Tome3 debug
print('\n=== tome3-05 debug ===')
doc = fitz.open('extraction/pdfs/tome3-05.pdf')
print(f'Pages: {len(doc)}')
for page_num in range(min(3, len(doc))):
    page = doc[page_num]
    l, r, split = extract_columns(page)
    print(f'  Page {page_num+1}: left={len(l)} lines, right={len(r)} lines, split_x={split:.0f}')
    if l:
        for line in l[:3]:
            text = ' '.join(s.get('text','') for s in line)
            print(f'    L: {text[:70]}')
    # Tester le parseur
    from extract_v2 import col_left_x
    clx = col_left_x(l) if l else 133.0
    entries = parse_column_entries(l, clx, 3, page_num+1, 'tome3-05.pdf')
    print(f'  -> {len(entries)} entrees en col gauche')
    for e in entries[:2]:
        print(f'     {repr(e.get("word","")[:40])}')
doc.close()
