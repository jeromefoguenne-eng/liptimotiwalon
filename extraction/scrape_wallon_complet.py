"""
Phase 2: Extraction complète des mots wallons avec å depuis wa.wiktionary.org.
On parcourt toutes les pages en wallon et on extrait les mots avec å.
"""
import requests, json, os, time, re
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
OUTPUT = os.path.join(PROJ, 'extraction', 'wallon_a_rond_reference.json')

HEADERS = {
    'User-Agent': 'LiPtitMotiWalon/1.0 (Dictionnaire liégeois; contact: projet-wallon) python-requests/2.31'
}

WA_URL = "https://wa.wiktionary.org/w/api.php"
FR_URL = "https://fr.wiktionary.org/w/api.php"

# ============================================================
# 1. Récupérer TOUTES les pages wa.wiktionary avec å dans le titre
# ============================================================

def get_all_wa_pages_with_a_ring():
    """Parcourt tout wa.wiktionary pour trouver les mots avec å."""
    all_words = []
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": 500,
        "format": "json"
    }
    
    continue_token = None
    page_count = 0
    
    while True:
        if continue_token:
            params["apcontinue"] = continue_token
        
        r = requests.get(WA_URL, params=params, headers=HEADERS, verify=False, timeout=30)
        if r.status_code != 200:
            print(f"Erreur HTTP {r.status_code}")
            break
        
        data = r.json()
        pages = data.get("query", {}).get("allpages", [])
        
        for p in pages:
            title = p["title"]
            if "å" in title or "Å" in title:
                all_words.append(title)
        
        page_count += len(pages)
        
        # Continuer ?
        cont = data.get("continue", {})
        if "apcontinue" in cont:
            continue_token = cont["apcontinue"]
            time.sleep(0.5)
        else:
            break
    
    print(f"  Parcouru {page_count} pages wa.wiktionary, trouvé {len(all_words)} avec å")
    return all_words

# ============================================================
# 2. Récupérer les pages fr.wiktionary avec tag wallon ET å
# ============================================================

def get_fr_wallon_pages_with_a_ring():
    """Cherche sur fr.wiktionary les entrées wallon avec å."""
    # Catégorie wallon sur fr.wiktionary
    words_found = set()
    
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Catégorie:wallon",
        "cmlimit": 500,
        "cmnamespace": 0,
        "format": "json"
    }
    
    continue_token = None
    page_count = 0
    
    while True:
        if continue_token:
            params["cmcontinue"] = continue_token
        
        r = requests.get(FR_URL, params=params, headers=HEADERS, verify=False, timeout=30)
        if r.status_code != 200:
            break
        
        data = r.json()
        members = data.get("query", {}).get("categorymembers", [])
        
        for m in members:
            title = m["title"]
            if "å" in title or "Å" in title:
                words_found.add(title)
                print(f"    [FR wallon avec å] {title}")
        
        page_count += len(members)
        
        cont = data.get("continue", {})
        if "cmcontinue" in cont:
            continue_token = cont["cmcontinue"]
            time.sleep(0.3)
            if page_count > 5000:  # Sécurité
                print(f"  Arrêt après {page_count} membres")
                break
        else:
            break
    
    print(f"  Parcouru {page_count} mots de catégorie wallon, {len(words_found)} avec å")
    return list(words_found)

# ============================================================
# 3. Récupérer le wikitext d'une page pour extraire les formes
# ============================================================

def get_page_content(title, base_url=FR_URL):
    """Récupère le wikitext d'une page."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json"
    }
    r = requests.get(base_url, params=params, headers=HEADERS, verify=False, timeout=20)
    if r.status_code == 200:
        data = r.json()
        return data.get("parse", {}).get("wikitext", {}).get("*", "")
    return ""

# ============================================================
# 4. Extraire les formes dérivées depuis le wikitext
# ============================================================

def extract_wallon_forms(wikitext, base_word):
    """Extrait les formes wallonnes avec å depuis le wikitext d'une page."""
    forms = set()
    forms.add(base_word)
    
    # Chercher les formes dans le wikitext
    # Pattern: | mot = xxx ou '''xxx''' dans section wallon
    
    # Section wallon
    in_wallon = False
    for line in wikitext.split('\n'):
        if '== {{langue|wa}}' in line or '==wallon==' in line.replace(' ', '').lower():
            in_wallon = True
        elif line.startswith('== ') and in_wallon:
            in_wallon = False
        
        if in_wallon:
            # Formes en gras: '''mot'''
            matches = re.findall(r"'''([^']+)'''", line)
            for m in matches:
                if 'å' in m or 'Å' in m:
                    forms.add(m)
            # Liens: [[mot]] ou [[mot|texte]]
            matches = re.findall(r'\[\[([^\]|]+)', line)
            for m in matches:
                if 'å' in m or 'Å' in m:
                    forms.add(m)
    
    return list(forms)

# ============================================================
# EXÉCUTION
# ============================================================

print("=" * 60)
print("EXTRACTION COMPLÈTE - Mots wallons avec å")
print("=" * 60)

all_wallon_a_ring = set()

# Phase 1: wa.wiktionary
print("\n[1] Parcours wa.wiktionary.org...")
wa_words = get_all_wa_pages_with_a_ring()
all_wallon_a_ring.update(wa_words)
print(f"    Exemples: {wa_words[:10]}")

time.sleep(1)

# Phase 2: fr.wiktionary catégorie wallon
print("\n[2] Catégorie wallon sur fr.wiktionary...")
fr_words = get_fr_wallon_pages_with_a_ring()
all_wallon_a_ring.update(fr_words)

time.sleep(1)

# Phase 3: Récupérer les pages individuelles wa.wiktionary pour mots importants
print("\n[3] Détail des 50 premières pages wa.wiktionary avec å...")
important_wa = [w for w in wa_words if len(w) > 2][:50]
extra_forms = set()
for word in important_wa:
    content = get_page_content(word, WA_URL)
    if content:
        forms = extract_wallon_forms(content, word)
        extra_forms.update(forms)
    time.sleep(0.3)

all_wallon_a_ring.update(extra_forms)
print(f"    Formes supplémentaires trouvées: {len(extra_forms)}")

# Résultat final
final_list = sorted(list(all_wallon_a_ring))
print(f"\n{'='*60}")
print(f"TOTAL: {len(final_list)} mots/formes wallons avec å")
print("\n30 premiers:")
for w in final_list[:30]:
    print(f"  {w}")

# Sauvegarder
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(final_list, f, ensure_ascii=False, indent=2)
print(f"\nSauvegardé dans: {OUTPUT}")
