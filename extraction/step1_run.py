#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script de scraping - version corrigee pour Windows (sans emojis)

import sys
import re
import time
import json
import requests
import urllib3
from pathlib import Path
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = Path("C:/Users/TrendingPC/.gemini/antigravity/scratch/liptimotiwalon/extraction")
PDF_DIR = BASE / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {"url": "https://www.provincedeliege.be/fr/viewallonne/dicowallon/francais-liegeois", "label": "francais-liegeois"},
    {"url": "https://www.provincedeliege.be/fr/viewallonne/dicowallon/liegeois", "label": "liegeois"}
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

all_pdfs = []
seen = set()

for page in PAGES:
    url = page["url"]
    print(f"\n[SCRAPING] {url}")
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ERREUR: {e}")
        continue

    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
    print(f"  Liens PDF trouves: {len(links)}")

    for link in links:
        href = link.get("href", "").strip()
        if not href:
            continue
        if href.startswith("http://"):
            href = "https://" + href[7:]  # Force HTTPS
        elif not href.startswith("http"):
            href = "https://www.provincedeliege.be" + href
        if href not in seen:
            seen.add(href)
            fname = href.split("/")[-1].split("?")[0]
            entry = {
                "url": href,
                "label": link.text.strip(),
                "source_page": page["label"],
                "filename": fname,
                "downloaded": False,
                "local_path": None
            }
            all_pdfs.append(entry)
            print(f"  + {fname} ({link.text.strip()[:40]})")

print(f"\nTotal PDFs uniques: {len(all_pdfs)}")

# Telecharger chaque PDF
print("\n[TELECHARGEMENT]")
for i, pdf in enumerate(all_pdfs, 1):
    dest = PDF_DIR / pdf["filename"]
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  [{i}/{len(all_pdfs)}] Deja present: {pdf['filename']} ({dest.stat().st_size//1024} KB)")
        pdf["downloaded"] = True
        pdf["local_path"] = str(dest)
        continue

    print(f"  [{i}/{len(all_pdfs)}] Telechargement: {pdf['filename']}", end="", flush=True)
    try:
        r = requests.get(pdf["url"], headers=HEADERS, verify=False, timeout=60, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        print(f" -> OK ({size_kb} KB)")
        pdf["downloaded"] = True
        pdf["local_path"] = str(dest)
    except Exception as e:
        print(f" -> ERREUR: {e}")

    time.sleep(0.5)

# Sauvegarder le manifest
manifest = BASE / "pdf_manifest.json"
with open(manifest, "w", encoding="utf-8") as f:
    json.dump(all_pdfs, f, ensure_ascii=False, indent=2)

ok = sum(1 for p in all_pdfs if p["downloaded"])
fail = sum(1 for p in all_pdfs if not p["downloaded"])
print(f"\n[RESULTAT] OK: {ok} | Echecs: {fail}")
print(f"Manifest: {manifest}")
