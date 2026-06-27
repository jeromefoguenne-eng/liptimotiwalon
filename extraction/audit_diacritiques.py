"""
audit_diacritiques.py -- Audit complet des caracteres speciaux dans dico.json.

Analyse :
1. Tous les caracteres Unicode non-ASCII presents
2. Les caracteres wallons attendus vs manquants
3. Les entrees a corriger (a rond manquant, etc.)
4. Rapport HTML + JSON
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json, re, unicodedata
from pathlib import Path
from collections import Counter, defaultdict

PROJ     = Path(__file__).parent.parent
DICO_IN  = PROJ / "dico.json"
OUT_JSON = PROJ / "extraction" / "audit_diacritiques.json"
OUT_HTML = PROJ / "extraction" / "audit_diacritiques.html"

# ---------------------------------------------------------------------------
# Caractères wallons connus (liégeois Jean Haust)
# ---------------------------------------------------------------------------
WALLON_CHARS_EXPECTED = {
    # Voyelles avec diacritiques usuels
    'à', 'â', 'ä', 'è', 'é', 'ê', 'ë', 'î', 'ï', 'ô', 'ö', 'ù', 'û', 'ü',
    # Majuscules
    'À', 'Â', 'È', 'É', 'Ê', 'Î', 'Ô', 'Ù', 'Û',
    # å — LE caractère wallon central (a rond en chef)
    'å', 'Å',
    # Autres caractères liégeois
    'ç', 'Ç',
    # Tirets et apostrophes typographiques
    ''', ''', '«', '»', '–', '—',
}

# Mots wallons courants avec å — référence pour les faux positifs
WALLON_A_ROND_PATTERNS = [
    # Préfixes wallons typiques avec å
    r'\båb', r'\båd', r'\båg', r'\bål', r'\båm', r'\åns', r'\åp', r'\år', r'\åt', r'\åv',
    r'\bblå', r'\bbåy', r'\bcåf', r'\bdåm',
]

# ---------------------------------------------------------------------------
# Caractères suspects : ASCII qui devrait probablement être un diacritique
# ---------------------------------------------------------------------------
# En wallon, le 'a' seul en position initiale est souvent 'å'
# On détecte les tokens qui commencent par 'a' suivi de consonnes typiques
SUSPECT_A_PATTERNS = re.compile(
    r'\b(a(?:dje|bon|lon|ble|gra|bri|lou|mon|men|men|toû|we|ye|re|rca|rma|rmon|rsin|rme|rtif|rcad|balo|yna|bol|tchet|vin|via))\b',
    re.IGNORECASE
)

def get_unicode_chars(text: str) -> set:
    """Retourne tous les caractères non-ASCII d'une chaîne."""
    return {c for c in text if ord(c) > 127}

def char_name(c: str) -> str:
    try:
        return unicodedata.name(c)
    except ValueError:
        return f"U+{ord(c):04X}"

# ---------------------------------------------------------------------------
# Audit principal
# ---------------------------------------------------------------------------
print(f"Chargement de {DICO_IN} ...")
with open(DICO_IN, encoding='utf-8') as f:
    dico = json.load(f)

print(f"[OK] {len(dico)} entrees chargees.")

# Compteurs globaux
all_special_chars   = Counter()
missing_a_rond      = []   # Entrées où 'a' devrait être 'å'
has_a_rond          = 0
missing_chars       = defaultdict(list)  # char → entrées affectées
entries_by_issue    = defaultdict(list)
char_samples        = defaultdict(list)  # char → [exemples de mots]

total_words_with_special = 0
total_defs_with_special  = 0

for i, entry in enumerate(dico):
    word = entry.get('word', '')
    defn = entry.get('definition', '')
    tome = entry.get('tome', '?')
    page = entry.get('page', '?')
    ref  = f"T{tome}p{page}"

    # Chars spéciaux dans le mot-vedette
    wchars = get_unicode_chars(word)
    if wchars:
        total_words_with_special += 1
    for c in wchars:
        all_special_chars[c] += 1
        if len(char_samples[c]) < 5:
            char_samples[c].append(word[:40])

    # Chars spéciaux dans la définition
    dchars = get_unicode_chars(defn)
    if dchars:
        total_defs_with_special += 1
    for c in dchars:
        all_special_chars[c] += 1

    # Détecter å présent
    if 'å' in word or 'å' in defn or 'Å' in word or 'Å' in defn:
        has_a_rond += 1

    # Détecter les 'a' suspects (qui devraient être å)
    word_lower = word.lower()
    defn_lower = defn.lower()
    m_word = SUSPECT_A_PATTERNS.search(word_lower)
    m_defn = SUSPECT_A_PATTERNS.search(defn_lower)
    if m_word or m_defn:
        missing_a_rond.append({
            'word': word[:60],
            'definition': defn[:100],
            'match_word': m_word.group(0) if m_word else None,
            'match_def': m_defn.group(0) if m_defn else None,
            'tome': tome,
            'page': page,
        })

# ---------------------------------------------------------------------------
# Statistiques sur les caractères
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"CARACTÈRES SPÉCIAUX DANS LE DICO")
print(f"{'='*60}")
print(f"  Entrées totales         : {len(dico)}")
print(f"  Mots avec diacritiques  : {total_words_with_special}")
print(f"  Defs avec diacritiques  : {total_defs_with_special}")
print(f"  Entrées avec å/Å        : {has_a_rond}")
print(f"  Entrées suspects (a→å?) : {len(missing_a_rond)}")
print(f"\n  Caractères Unicode trouvés ({len(all_special_chars)}):")
for c, count in sorted(all_special_chars.items(), key=lambda x: -x[1]):
    expected = "✓" if c in WALLON_CHARS_EXPECTED else "⚠"
    name = char_name(c)
    samples = char_samples.get(c, [])
    sample_str = " | ".join(samples[:3])
    print(f"    {expected} '{c}' (U+{ord(c):04X}) [{name}]  ×{count:5d}  ex: {sample_str}")

print(f"\n  Entrées suspectes (a qui devrait être å) — {len(missing_a_rond)} cas:")
for e in missing_a_rond[:20]:
    print(f"    T{e['tome']}p{e['page']}  '{e['word'][:40]}'  match: {e['match_word'] or e['match_def']}")

# ---------------------------------------------------------------------------
# Rapport JSON
# ---------------------------------------------------------------------------
rapport = {
    "total_entries": len(dico),
    "words_with_special_chars": total_words_with_special,
    "defs_with_special_chars": total_defs_with_special,
    "entries_with_a_rond": has_a_rond,
    "entries_suspect_missing_a_rond": len(missing_a_rond),
    "all_special_chars": {
        c: {
            "count": count,
            "unicode_name": char_name(c),
            "code_point": f"U+{ord(c):04X}",
            "is_expected_wallon": c in WALLON_CHARS_EXPECTED,
            "samples": char_samples.get(c, [])[:5],
        }
        for c, count in sorted(all_special_chars.items(), key=lambda x: -x[1])
    },
    "missing_a_rond_sample": missing_a_rond[:50],
}

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(rapport, f, ensure_ascii=False, indent=2)
print(f"\n[JSON] Rapport JSON : {OUT_JSON}")

# ---------------------------------------------------------------------------
# Rapport HTML
# ---------------------------------------------------------------------------
chars_rows = ""
for c, info in rapport["all_special_chars"].items():
    color = "#27ae60" if info["is_expected_wallon"] else "#e74c3c"
    icon  = "✓" if info["is_expected_wallon"] else "⚠"
    samples = " | ".join(info["samples"][:3])
    chars_rows += f"""
    <tr>
      <td style="font-size:1.5em;text-align:center">{c}</td>
      <td style="color:{color};font-weight:bold">{icon}</td>
      <td style="font-family:monospace">{info['code_point']}</td>
      <td>{info['unicode_name']}</td>
      <td style="text-align:right"><strong>{info['count']}</strong></td>
      <td style="font-size:.85em;color:#555">{samples}</td>
    </tr>"""

suspect_rows = ""
for e in missing_a_rond[:100]:
    suspect_rows += f"""
    <tr>
      <td>T{e['tome']} p.{e['page']}</td>
      <td><strong>{e['word'][:50]}</strong></td>
      <td style="color:#e67e22"><em>{e['match_word'] or ''}</em></td>
      <td style="color:#c0392b"><em>{e['match_def'] or ''}</em></td>
      <td style="font-size:.8em">{e['definition'][:80]}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Audit diacritiques — Dictionnaire Wallon</title>
<style>
  body {{ font-family: 'Georgia', serif; max-width: 1400px; margin: 0 auto; padding: 20px;
         background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ color: #e94560; border-bottom: 3px solid #e94560; padding-bottom: 10px; }}
  h2 {{ color: #0f3460; background: #e94560; padding: 8px 15px; border-radius: 4px; color: white; }}
  .stats {{ display: flex; gap: 15px; flex-wrap: wrap; margin: 20px 0; }}
  .stat {{ background: #16213e; border-radius: 8px; padding: 15px 20px;
           box-shadow: 0 2px 8px rgba(0,0,0,.3); min-width: 140px; border: 1px solid #0f3460; }}
  .stat .val {{ font-size: 2em; font-weight: bold; color: #e94560; }}
  .stat .lbl {{ font-size: .8em; color: #aaa; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: #16213e;
           box-shadow: 0 2px 8px rgba(0,0,0,.3); border-radius: 8px;
           overflow: hidden; margin: 15px 0; }}
  th {{ background: #0f3460; color: white; padding: 10px 12px; text-align: left; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #0f3460; vertical-align: top; }}
  tr:hover {{ background: #1a1a3e; }}
</style>
</head>
<body>
<h1>🔤 Audit des diacritiques — Dictionnaire Wallon (Jean Haust)</h1>

<div class="stats">
  <div class="stat"><div class="val">{len(dico)}</div><div class="lbl">Entrées totales</div></div>
  <div class="stat"><div class="val">{total_words_with_special}</div><div class="lbl">Mots avec diacritiques</div></div>
  <div class="stat"><div class="val" style="color:#27ae60">{has_a_rond}</div><div class="lbl">Entrées avec å</div></div>
  <div class="stat"><div class="val" style="color:#f39c12">{len(missing_a_rond)}</div><div class="lbl">Suspects a→å manquant</div></div>
  <div class="stat"><div class="val">{len(all_special_chars)}</div><div class="lbl">Chars Unicode uniques</div></div>
</div>

<h2>Inventaire des caractères Unicode</h2>
<table>
  <tr><th>Char</th><th>Statut</th><th>Code</th><th>Nom Unicode</th><th>Occurrences</th><th>Exemples</th></tr>
  {chars_rows}
</table>

<h2>Entrées suspectes — 'a' qui devrait être 'å' ({len(missing_a_rond)} cas)</h2>
<table>
  <tr><th>Réf.</th><th>Mot-vedette</th><th>Match mot</th><th>Match def</th><th>Extrait définition</th></tr>
  {suspect_rows}
</table>

</body>
</html>"""

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"[HTML] Rapport HTML : {OUT_HTML}")
print("\nTermine OK")
