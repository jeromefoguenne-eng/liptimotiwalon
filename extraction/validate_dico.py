"""
validate_dico.py — Validateur qualité du dico.json reconstruit.

Génère un rapport JSON + un rapport HTML de 200 entrées aléatoires.
"""

import json, random, os, re
from pathlib import Path
from datetime import datetime

PROJ = Path(__file__).parent.parent


def validate(dico: list[dict]) -> dict:
    """Analyse la qualité du dico et retourne un rapport."""
    total = len(dico)
    if total == 0:
        return {"error": "Dico vide"}

    stats = {
        "total"              : total,
        "needs_review"       : 0,
        "a_ring_corrected"   : 0,
        "word_empty"         : 0,
        "word_too_long"      : 0,   # > 60 chars
        "def_empty"          : 0,
        "def_too_short"      : 0,   # < 10 chars
        "def_too_long"       : 0,   # > 2000 chars (fusion de définitions)
        "by_tome"            : {},
        "by_letter"          : {},
    }

    issues = []

    for e in dico:
        word = e.get("word", "").strip()
        defn = e.get("definition", "").strip()
        tome = e.get("tome", 0)
        page = e.get("page", 0)

        if e.get("needs_review"):
            stats["needs_review"] += 1
        if e.get("a_ring_corrected"):
            stats["a_ring_corrected"] += 1

        # Mot vide
        if not word:
            stats["word_empty"] += 1
            issues.append({"type": "word_empty", "tome": tome, "page": page})
            continue

        # Mot trop long (probable erreur de découpage)
        if len(word) > 60:
            stats["word_too_long"] += 1
            issues.append({"type": "word_too_long", "word": word[:80],
                           "tome": tome, "page": page})

        # Définition vide
        if not defn:
            stats["def_empty"] += 1
            issues.append({"type": "def_empty", "word": word[:40],
                           "tome": tome, "page": page})

        # Définition trop courte
        elif len(defn) < 10:
            stats["def_too_short"] += 1

        # Définition trop longue (fusion probable)
        elif len(defn) > 2000:
            stats["def_too_long"] += 1
            issues.append({"type": "def_too_long", "word": word[:40],
                           "len": len(defn), "tome": tome, "page": page})

        # Stats par tome
        t = str(tome)
        stats["by_tome"][t] = stats["by_tome"].get(t, 0) + 1

        # Stats par lettre initiale
        letter = word[0].lower() if word else "?"
        # Normaliser å → a pour le comptage
        letter = letter.replace("å", "a").replace("Å", "a")
        stats["by_letter"][letter] = stats["by_letter"].get(letter, 0) + 1

    # Taux de qualité estimé
    problematic = (stats["word_empty"] + stats["word_too_long"] +
                   stats["def_empty"] + stats["def_too_long"])
    stats["quality_pct"] = round((1 - problematic / total) * 100, 1)
    stats["issues_sample"] = issues[:50]

    return stats


def generate_html_report(dico: list[dict], stats: dict,
                          output_path: Path, sample_size: int = 200):
    """Génère un rapport HTML avec des entrées aléatoires pour révision."""
    sample = random.sample(dico, min(sample_size, len(dico)))
    sample.sort(key=lambda e: (e.get("tome", 0), e.get("page", 0)))

    rows = []
    for e in sample:
        word = e.get("word", "—")
        defn = e.get("definition", "—")[:300]
        tome = e.get("tome", "?")
        page = e.get("page", "?")
        gram = e.get("grammar", "")
        flags = []
        if e.get("needs_review"):
            flags.append('<span class="flag review">⚠ révision</span>')
        if e.get("a_ring_corrected"):
            flags.append('<span class="flag ring">å corrigé</span>')

        row = f"""
        <tr class="{'review' if e.get('needs_review') else ''}">
          <td class="word">{word}</td>
          <td class="gram">{gram}</td>
          <td class="def">{defn}</td>
          <td class="meta">T{tome} p.{page}<br>{''.join(flags)}</td>
        </tr>"""
        rows.append(row)

    quality_pct   = stats.get("quality_pct", 0)
    quality_color = "#2ecc71" if quality_pct >= 90 else \
                    "#f39c12" if quality_pct >= 75 else "#e74c3c"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport qualité — Dictionnaire Liégeois</title>
<style>
  body {{ font-family: 'Georgia', serif; max-width: 1400px; margin: 0 auto; padding: 20px;
          background: #fafafa; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  .stats {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }}
  .stat {{ background: white; border-radius: 8px; padding: 15px 20px;
           box-shadow: 0 2px 4px rgba(0,0,0,.1); min-width: 140px; }}
  .stat .val {{ font-size: 2em; font-weight: bold; color: #3498db; }}
  .stat .lbl {{ font-size: .85em; color: #777; }}
  .quality {{ color: {quality_color} !important; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           box-shadow: 0 2px 8px rgba(0,0,0,.1); border-radius: 8px;
           overflow: hidden; margin-top: 20px; }}
  th {{ background: #2c3e50; color: white; padding: 12px; text-align: left; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:hover {{ background: #f0f7ff; }}
  tr.review {{ background: #fff8e1; }}
  .word {{ font-weight: bold; color: #2c3e50; min-width: 150px; font-size: 1.05em; }}
  .gram {{ color: #7f8c8d; font-style: italic; min-width: 60px; font-size: .9em; }}
  .def  {{ font-size: .9em; line-height: 1.4; }}
  .meta {{ font-size: .8em; color: #95a5a6; min-width: 100px; }}
  .flag {{ display: inline-block; padding: 2px 6px; border-radius: 4px;
           font-size: .75em; margin: 2px; }}
  .flag.review {{ background: #f39c12; color: white; }}
  .flag.ring   {{ background: #3498db; color: white; }}
  .issues {{ background: #fff3cd; border-radius: 8px; padding: 15px; margin: 15px 0; }}
</style>
</head>
<body>
<h1>📖 Rapport qualité — Dictionnaire Liégeois (Haust)</h1>
<p>Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} | {stats['total']} entrées totales</p>

<div class="stats">
  <div class="stat"><div class="val quality">{quality_pct}%</div>
    <div class="lbl">Qualité estimée</div></div>
  <div class="stat"><div class="val">{stats['total']}</div>
    <div class="lbl">Entrées totales</div></div>
  <div class="stat"><div class="val" style="color:#e74c3c">{stats['needs_review']}</div>
    <div class="lbl">À réviser (å?)</div></div>
  <div class="stat"><div class="val" style="color:#27ae60">{stats['a_ring_corrected']}</div>
    <div class="lbl">å corrigés auto</div></div>
  <div class="stat"><div class="val" style="color:#e74c3c">{stats['word_empty']}</div>
    <div class="lbl">Mots vides</div></div>
  <div class="stat"><div class="val" style="color:#e74c3c">{stats['def_empty']}</div>
    <div class="lbl">Defs vides</div></div>
  <div class="stat"><div class="val" style="color:#e74c3c">{stats['word_too_long']}</div>
    <div class="lbl">Mots trop longs</div></div>
</div>

<h2>Échantillon aléatoire ({len(sample)} entrées)</h2>
<table>
  <tr><th>Mot-vedette</th><th>Gramm.</th><th>Définition</th><th>Réf.</th></tr>
  {''.join(rows)}
</table>

<h2>Problèmes détectés (50 premiers)</h2>
<div class="issues">
  <pre>{json.dumps(stats.get('issues_sample', []), ensure_ascii=False, indent=2)}</pre>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
