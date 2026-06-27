"""
Construction de la liste finale propre de mots wallons avec å,
en re-scrapant wa.wiktionary de façon robuste et en extrayant
uniquement les titres de pages (mots lemmes) commençant par å.

On complète avec une liste manuelle des mots les plus importants
du Dictionnaire Liégeois de Haust qu'on sait avoir un å.
"""
import requests, json, os, time, re
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PROJ = r'C:\Users\TrendingPC\.gemini\antigravity\scratch\liptimotiwalon'
OUTPUT = os.path.join(PROJ, 'extraction', 'wallon_a_rond_clean.json')

HEADERS = {'User-Agent': 'LiPtitMotiWalon/1.0 python-requests/2.31'}
WA_URL = "https://wa.wiktionary.org/w/api.php"

# ============================================================
# Récupérer les titres de pages commençant par å (plusieurs passes)
# ============================================================
all_lemmes = set()

print("[1] Récupération des pages wa.wiktionary commençant par å...")
continue_from = "å"
passes = 0
while passes < 20:
    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "aplimit": 500,
        "apfrom": continue_from,
        "apto": "åzzz",
        "format": "json"
    }
    try:
        r = requests.get(WA_URL, params=params, headers=HEADERS, verify=False, timeout=20)
        if r.status_code == 429:
            print("  Rate limit, attente 10s...")
            time.sleep(10)
            continue
        if r.status_code != 200:
            break
        data = r.json()
        pages = data.get("query", {}).get("allpages", [])
        for p in pages:
            t = p["title"]
            if "å" in t or "Å" in t:
                all_lemmes.add(t)
        
        cont = data.get("continue", {})
        if "apcontinue" in cont:
            continue_from = cont["apcontinue"]
            passes += 1
            time.sleep(0.5)
        else:
            break
    except Exception as e:
        print(f"  Erreur: {e}")
        break

print(f"  -> {len(all_lemmes)} lemmes trouvés avec å")

# ============================================================
# Filtrer: garder seulement les mots communs (minuscules, >= 2 chars,
# pas d'espace, pas de wikitexte)
# ============================================================
def is_common_word(w):
    """Retourne True si c'est un mot commun wallon (pas nom propre/phrase)."""
    if not w or len(w) < 2:
        return False
    if w.startswith('å') or w.startswith('Å'):
        # Mots commençant par å: garder si minuscule et simple
        if w[0] == 'å' and len(w.split()) <= 2:
            return True
    # Exclure: contient {, [, |, #, *
    if any(c in w for c in '{}[]|#*'):
        return False
    # Exclure: noms propres purs (première lettre majuscule, pas de å au début)
    if w[0].isupper() and 'å' in w[1:]:
        # Nom propre avec å au milieu: utile pour correction
        return len(w.split()) == 1  # un seul token
    return False

common = sorted([w for w in all_lemmes if is_common_word(w)])
print(f"\n[2] Mots communs filtrés: {len(common)}")

# Séparer mots simples (1 token) des expressions (multi-tokens)
single = [w for w in common if len(w.split()) == 1]
multi  = [w for w in common if len(w.split()) > 1]

print(f"  Mots simples: {len(single)}")
print(f"  Expressions: {len(multi)}")

# ============================================================
# Construire le mapping de correction:
# forme_sans_å (lowercase) -> forme_correcte_avec_å
# ============================================================
mapping = {}
for w in single:
    key = w.lower().replace('å', 'a').replace('Å', 'A')
    if key not in mapping:
        mapping[key] = w
    elif len(w) < len(mapping[key]):  # Préférer la forme plus courte
        mapping[key] = w

print(f"\n[3] Mapping de correction: {len(mapping)} entrées")
print("Aperçu (mots simples):")
for k, v in sorted(mapping.items())[:40]:
    if k != v.lower():  # Montrer seulement ceux où il y a vraiment un å
        print(f"  '{k}' -> '{v}'")

# ============================================================
# Sauvegarder
# ============================================================
result = {
    "single_words": single,
    "expressions": multi,
    "mapping": mapping,
    "total_lemmes": len(all_lemmes)
}
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nSauvegardé: {OUTPUT}")
