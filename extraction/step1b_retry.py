#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, requests, urllib3, time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = Path('C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/extraction')
PDF_DIR = BASE / 'pdfs'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

with open(BASE / 'pdf_manifest.json', encoding='utf-8') as f:
    pdfs = json.load(f)

failed = [p for p in pdfs if not p['downloaded']]
print(f'Echecs a relancer: {len(failed)}')

for pdf in failed:
    dest = PDF_DIR / pdf['filename']
    fname = pdf['filename']
    print(f'Retry: {fname}', end='', flush=True)
    try:
        r = requests.get(pdf['url'], headers=HEADERS, verify=False, timeout=180, stream=True)
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        print(f' -> OK ({size_kb} KB)')
        pdf['downloaded'] = True
        pdf['local_path'] = str(dest)
    except Exception as e:
        print(f' -> ERREUR: {e}')
    time.sleep(2)

with open(BASE / 'pdf_manifest.json', 'w', encoding='utf-8') as f:
    json.dump(pdfs, f, ensure_ascii=False, indent=2)

ok = sum(1 for p in pdfs if p['downloaded'])
print(f'\nTotal telecharges: {ok}/{len(pdfs)}')
