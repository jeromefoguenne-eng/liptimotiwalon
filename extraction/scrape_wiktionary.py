"""
Scraping du Wiktionnaire wallon pour extraire tous les mots avec å (a-ring).
Utilise l'API MediaWiki avec User-Agent correct.
"""
import requests, json, os, time, re
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
OUTPUT = os.path.join(PROJ, 'extraction', 'wallon_a_rond_reference.json')

HEADERS = {
    'User-Agent': 'LiPtitMotiWalon/1.0 (Dictionnaire liégeois numérique; jerome@liptitmotiwalon.be) python-requests/2.31'
}

BASE_URL = "https://fr.wiktionary.org/w/api.php"

# ============================================================
# STRATÉGIE 1: Chercher toutes les pages qui commencent par å
# ============================================================

def get_pages_starting_with(prefix, lang_code="wa"):
    """Récupère les pages du Wiktionnaire commençant par un préfixe."""
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": 500,
        "apfrom": prefix,
        "apto": prefix + "zzz",  # limiter à ce préfixe
        "format": "json"
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, verify=False, timeout=20)
    if r.status_code == 200:
        data = r.json()
        pages = data.get("query", {}).get("allpages", [])
        return [p["title"] for p in pages]
    return []

# ============================================================
# STRATÉGIE 2: Utiliser la catégorie "wallon" sur fr.wiktionary
# et chercher les mots avec å
# ============================================================

def search_wallon_words_with_a_ring():
    """Recherche directe des mots wallons avec å via l'API."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": "å incategory:wallon",
        "srnamespace": 0,
        "srlimit": 100,
        "format": "json"
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, verify=False, timeout=20)
    if r.status_code == 200:
        data = r.json()
        results = data.get("query", {}).get("search", [])
        return [res["title"] for res in results if "å" in res["title"]]
    return []

# ============================================================
# STRATÉGIE 3: Wiktionnaire wallon (wa.wiktionary.org)
# ============================================================

def get_wa_wiktionary_a_ring():
    """Cherche sur wa.wiktionary.org (Wiktionnaire en wallon)."""
    wa_url = "https://wa.wiktionary.org/w/api.php"
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": 500,
        "apfrom": "å",
        "format": "json"
    }
    r = requests.get(wa_url, params=params, headers=HEADERS, verify=False, timeout=20)
    if r.status_code == 200:
        data = r.json()
        pages = data.get("query", {}).get("allpages", [])
        # Filtrer pour garder seulement ceux avec å
        return [p["title"] for p in pages if "å" in p["title"]]
    return []

# ============================================================
# STRATÉGIE 4: Recherche plein texte sur fr.wiktionary
# ============================================================

def fulltext_search_wallon_a_ring():
    """Recherche plein texte de 'å' dans les pages de catégorie wallon."""
    all_words = set()
    # Chercher les pages qui contiennent == wallon == et le caractère å
    params = {
        "action": "query",
        "list": "search",
        "srsearch": "å",
        "srnamespace": 0,
        "srlimit": 500,
        "format": "json",
        "srprop": "snippet|title"
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, verify=False, timeout=30)
    if r.status_code == 200:
        data = r.json()
        results = data.get("query", {}).get("search", [])
        for res in results:
            title = res.get("title", "")
            snippet = res.get("snippet", "")
            if "å" in title:
                all_words.add(title)
            # Chercher les formes avec å dans le snippet
            matches = re.findall(r'[åÅ][a-zàâéèêëîïôùûüç\'àéèêëîïôùûüç-]*', snippet)
            all_words.update(matches)
    return list(all_words)

print("=" * 60)
print("SCRAPING WIKTIONNAIRE - Mots wallons avec å")
print("=" * 60)

all_a_ring_words = set()

# Stratégie 1: Pages commençant par å sur fr.wiktionary
print("\n[1] Pages fr.wiktionary commençant par 'å'...")
pages_a = get_pages_starting_with("å")
print(f"    -> {len(pages_a)} pages trouvées")
for p in pages_a:
    if "å" in p:
        all_a_ring_words.add(p)
        print(f"    {p}")

time.sleep(1)

# Stratégie 2: Recherche wallon + å
print("\n[2] Recherche 'å incategory:wallon'...")
words_search = search_wallon_words_with_a_ring()
print(f"    -> {len(words_search)} résultats")
all_a_ring_words.update(words_search)
for w in words_search[:20]:
    print(f"    {w}")

time.sleep(1)

# Stratégie 3: wa.wiktionary.org
print("\n[3] wa.wiktionary.org (Wiktionnaire en wallon)...")
wa_words = get_wa_wiktionary_a_ring()
print(f"    -> {len(wa_words)} mots")
all_a_ring_words.update(wa_words)
for w in wa_words[:20]:
    print(f"    {w}")

time.sleep(1)

# Stratégie 4: Recherche plein texte
print("\n[4] Recherche plein texte å sur fr.wiktionary...")
ft_words = fulltext_search_wallon_a_ring()
print(f"    -> {len(ft_words)} résultats")
all_a_ring_words.update(ft_words)

print(f"\n{'='*60}")
print(f"TOTAL mots avec å trouvés: {len(all_a_ring_words)}")
print("Exemples:", sorted(list(all_a_ring_words))[:30])

# Sauvegarder
result = sorted(list(all_a_ring_words))
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nSauvegardé: {OUTPUT}")
