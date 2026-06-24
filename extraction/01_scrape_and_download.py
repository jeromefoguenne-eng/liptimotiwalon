#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Étape 1+2 : Scraper les liens PDF et télécharger tous les fichiers
depuis les deux pages du dictionnaire wallon de la Province de Liège.
"""

import os
import re
import time
import json
import requests
import urllib3
from pathlib import Path
from bs4 import BeautifulSoup

# Désactiver les avertissements SSL (certificat local non reconnu)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PDF_DIR = BASE_DIR / "pdfs"
PDF_DIR.mkdir(exist_ok=True)

PAGES = [
    {
        "url": "https://www.provincedeliege.be/fr/viewallonne/dicowallon/francais-liegeois",
        "label": "francais-liegeois"
    },
    {
        "url": "https://www.provincedeliege.be/fr/viewallonne/dicowallon/liegeois",
        "label": "liegeois"
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ─── Scraping des liens PDF ───────────────────────────────────────────────────
def scrape_pdf_links():
    all_pdfs = []
    seen = set()

    for page in PAGES:
        print(f"\n📄 Scraping: {page['url']}")
        try:
            r = requests.get(page["url"], headers=HEADERS, verify=False, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))

        for link in links:
            href = link.get("href", "").strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = "https://www.provincedeliege.be" + href

            if href not in seen:
                seen.add(href)
                entry = {
                    "url": href,
                    "label": link.text.strip(),
                    "source_page": page["label"],
                    "filename": href.split("/")[-1].split("?")[0]
                }
                all_pdfs.append(entry)
                print(f"  ✅ {entry['label'][:60]:60s} → {entry['filename']}")

    print(f"\n📊 Total PDFs uniques trouvés: {len(all_pdfs)}")
    return all_pdfs


# ─── Téléchargement des PDFs ──────────────────────────────────────────────────
def download_pdfs(pdf_list):
    results = []

    for i, pdf in enumerate(pdf_list, 1):
        dest = PDF_DIR / pdf["filename"]

        if dest.exists():
            print(f"  ⏭️  [{i}/{len(pdf_list)}] Déjà téléchargé: {pdf['filename']}")
            pdf["local_path"] = str(dest)
            pdf["downloaded"] = True
            results.append(pdf)
            continue

        print(f"  ⬇️  [{i}/{len(pdf_list)}] Téléchargement: {pdf['filename']}")
        try:
            r = requests.get(pdf["url"], headers=HEADERS, verify=False,
                             timeout=60, stream=True)
            r.raise_for_status()

            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_kb = dest.stat().st_size // 1024
            print(f"     ✅ {size_kb} KB")
            pdf["local_path"] = str(dest)
            pdf["downloaded"] = True

        except Exception as e:
            print(f"     ❌ Erreur: {e}")
            pdf["local_path"] = None
            pdf["downloaded"] = False

        results.append(pdf)
        time.sleep(0.5)  # Pause polie entre les requêtes

    return results


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  LI PTIT MOTI WALON — Étape 1 : Scraping + Téléchargement PDFs")
    print("=" * 70)

    pdfs = scrape_pdf_links()

    if not pdfs:
        print("\n❌ Aucun PDF trouvé. Vérifiez les URLs et la connectivité.")
        exit(1)

    print(f"\n⬇️  Début du téléchargement de {len(pdfs)} PDFs...")
    results = download_pdfs(pdfs)

    # Sauvegarde de la liste pour les étapes suivantes
    manifest_path = BASE_DIR / "pdf_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r["downloaded"])
    fail = sum(1 for r in results if not r["downloaded"])
    print(f"\n✅ Téléchargés: {ok} | ❌ Échecs: {fail}")
    print(f"📋 Manifest sauvé: {manifest_path}")
