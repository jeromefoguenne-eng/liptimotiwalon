"""
Scraping approfondi : récupérer le CONTENU des pages wa.wiktionary
pour trouver les définitions wallonnes et leurs formes avec å.

On cible spécifiquement les mots communs (minuscules, longueur >= 3).
"""
import requests, json, os, time, re
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
REF_FILE = os.path.join(PROJ, 'extraction', 'wallon_a_rond_reference.json')
OUTPUT   = os.path.join(PROJ, 'extraction', 'wallon_common_a_rond.json')

HEADERS = {
    'User-Agent': 'LiPtitMotiWalon/1.0 (Dictionnaire liégeois; jerome.foguenne@liptitmotiwalon.be) python-requests/2.31'
}

WA_URL = "https://wa.wiktionary.org/w/api.php"

# Récupérer toutes les pages commençant par des lettres minuscules avec å
# en parcourant alphabétiquement: åa, åb, åc... et aussi a*, b*, c* en cherchant å dans le contenu

def get_pages_range(from_title, to_title=None, limit=500):
    """Récupère les pages dans une plage alphabétique."""
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": limit,
        "apfrom": from_title,
        "format": "json"
    }
    if to_title:
        params["apto"] = to_title

    try:
        r = requests.get(WA_URL, params=params, headers=HEADERS, verify=False, timeout=20)
        if r.status_code == 200:
            data = r.json()
            return data.get("query", {}).get("allpages", [])
        elif r.status_code == 429:
            print("  Rate limited, attente 5s...")
            time.sleep(5)
            return []
    except Exception as e:
        print(f"  Erreur: {e}")
    return []

def get_page_wikitext(title):
    """Récupère le wikitext d'une page."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json"
    }
    try:
        r = requests.get(WA_URL, params=params, headers=HEADERS, verify=False, timeout=15)
        if r.status_code == 200:
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                revs = page.get("revisions", [])
                if revs:
                    return revs[0].get("slots", {}).get("main", {}).get("*", "")
    except:
        pass
    return ""

def extract_wallon_words_with_a_ring(wikitext, page_title):
    """Extrait toutes les formes avec å depuis le wikitext d'une page wallon."""
    words = set()
    if "å" in page_title:
        words.add(page_title)

    # Chercher les formes en gras avec å
    for m in re.findall(r"'''([^']*å[^']*)'''", wikitext):
        if len(m) >= 2:
            words.add(m)

    # Chercher dans les liens
    for m in re.findall(r'\[\[([^\]|]*å[^\]|]*)', wikitext):
        if len(m) >= 2 and not m.startswith('Categoreye') and not m.startswith('Imådje'):
            words.add(m)

    # Chercher les entrées de flexion (formes fléchies)
    for m in re.findall(r'=====?\s*([^=\n]*å[^=\n]*)\s*=====?', wikitext):
        words.add(m.strip())

    return words

print("=" * 60)
print("SCRAPING APPROFONDI wa.wiktionary - mots communs avec å")
print("=" * 60)

all_common = {}  # word -> {'forms': [...], 'wikitext': '...'}

# 1. Pages commençant par å (minuscule)
print("\n[1] Pages commençant par å...")
a_ring_pages = get_pages_range("å", "åzzz")
print(f"    {len(a_ring_pages)} pages")

# 2. Récupérer le contenu de chaque page å pour extraire les formes
print("\n[2] Analyse du contenu de chaque page å...")
for page in a_ring_pages:
    title = page["title"]
    if title.startswith("Categoreye") or title.startswith("Imådje"):
        continue

    wikitext = get_page_wikitext(title)
    forms = extract_wallon_words_with_a_ring(wikitext, title)

    all_common[title] = list(forms)
    print(f"    {title}: {list(forms)[:5]}")
    time.sleep(0.3)

# 3. Chercher dans d'autres plages les mots qui contiennent å
print("\n[3] Recherche par plethtext sur wa.wiktionary...")
params = {
    "action": "query",
    "list": "search",
    "srsearch": "å",
    "srnamespace": 0,
    "srlimit": 500,
    "srprop": "title|snippet",
    "format": "json"
}
try:
    r = requests.get(WA_URL, params=params, headers=HEADERS, verify=False, timeout=30)
    if r.status_code == 200:
        results = r.json().get("query", {}).get("search", [])
        print(f"    {len(results)} résultats de recherche")
        for res in results:
            title = res["title"]
            snippet = res.get("snippet", "")
            # Extraire les mots avec å du snippet
            words_in_snippet = re.findall(r'[åÅ][a-zàâéèêëîïôùûæœç\'åÅ-]*|[a-zàâéèêëîïôùûæœç\']+å[a-zàâéèêëîïôùûæœç\'åÅ-]*', snippet, re.IGNORECASE)
            for w in words_in_snippet:
                w = re.sub(r'<[^>]+>', '', w)  # Enlever les tags HTML
                if 'å' in w.lower() and len(w) >= 2:
                    if title not in all_common:
                        all_common[title] = []
                    if w not in all_common[title]:
                        all_common[title].append(w)
except Exception as e:
    print(f"    Erreur: {e}")

# Consolider tous les mots uniques avec å
all_words_with_a_ring = set()
for title, forms in all_common.items():
    if "å" in title:
        all_words_with_a_ring.add(title)
    all_words_with_a_ring.update(forms)

# Filtrer: mots communs uniquement (minuscule, longueur >= 2)
common_wallon = sorted([w for w in all_words_with_a_ring
                        if len(w) >= 2 and not w.startswith('-')
                        and 'å' in w.lower()])

print(f"\n{'='*60}")
print(f"TOTAL mots communs wallons avec å: {len(common_wallon)}")
print("\nAperçu:")
for w in common_wallon[:50]:
    print(f"  {w}")

# Sauvegarder
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump({
        "common_words": common_wallon,
        "by_page": all_common
    }, f, ensure_ascii=False, indent=2)
print(f"\nSauvegardé: {OUTPUT}")
