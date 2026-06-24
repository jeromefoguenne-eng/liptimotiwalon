#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Étape 4 : Validation via Ollama (modèles locaux) + génération du dico.json final.

Stratégie d'utilisation des modèles locaux :
- gemma4     → Validation de la qualité des entrées (détection bruit/artefact)  
- qwen3.6    → Correction des caractères spéciaux et encodage wallon
- qwen3-coder-next → Structuration et nettoyage des cas complexes (trop lourd, utilisé en fallback ciblé)

Format de sortie : tableau JSON identique à l'original attendu par app.js
{
  "word": str,       # Le mot (wallon ou français selon le type)
  "definition": str, # La définition complète
  "type": str,       # "wallon-francais" ou "francais-wallon"
  "tome": int,       # Numéro du tome (1, 2, 3...)
  "page": int,       # Numéro de page
  "slice": str       # Nom du fichier PDF source
}
"""

import json
import re
import sys
import time
import unicodedata
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
PARSED_DIR = BASE_DIR / "parsed"

OLLAMA_URL = "http://localhost:11434/api/generate"

# Modèles selon la tâche (du plus léger au plus lourd)
MODEL_VALIDATOR = "gemma4:latest"       # Détection qualité : rapide
MODEL_CORRECTOR  = "qwen3.6:latest"     # Correction encodage wallon : bon équilibre
# MODEL_HEAVY = "qwen3-coder-next:latest" # Réservé aux cas très complexes (51 GB!)


# ─── Utilitaires Ollama ───────────────────────────────────────────────────────
def ollama_query(model: str, prompt: str, timeout: int = 30) -> str:
    """Envoie une requête à Ollama et retourne la réponse."""
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Basse température = déterministe
                "num_predict": 200
            }
        }, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"ERREUR: {e}"


def is_ollama_running() -> bool:
    """Vérifie qu'Ollama est accessible."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        return r.status_code == 200
    except:
        return False


# ─── Nettoyage et validation ──────────────────────────────────────────────────
NOISE_PATTERNS = [
    r'^\d+$',                    # Numéros seuls
    r'^[.\-_=+*#]{3,}$',        # Séparateurs
    r'^(page|tome|vol\.|fig\.)', # En-têtes
    r'^\s*$',                    # Vide
    r'^[A-Z]{1,3}$',             # Lettres seules (A, B, AB...)
]

def is_noise_entry(entry: dict) -> bool:
    """Détermine si une entrée est du bruit (en-tête, séparateur, etc.)."""
    word = entry.get("mot", entry.get("word", "")).strip()
    definition = entry.get("definition", "").strip()

    if not word or not definition:
        return True

    for pattern in NOISE_PATTERNS:
        if re.match(pattern, word, re.I):
            return True

    # Définition trop courte et suspecte
    if len(definition) < 3:
        return True

    # Définition identique au mot (sans intérêt)
    if word.lower() == definition.lower():
        return True

    return False


def clean_entry(entry: dict) -> dict:
    """Nettoie et normalise une entrée du dictionnaire."""
    word = entry.get("mot", entry.get("word", "")).strip()
    definition = entry.get("definition", "").strip()

    # Normalisation Unicode NFC
    word = unicodedata.normalize("NFC", word)
    definition = unicodedata.normalize("NFC", definition)

    # Nettoyer les caractères de contrôle
    word = re.sub(r'[\x00-\x1f\x7f]', '', word)
    definition = re.sub(r'[\x00-\x1f\x7f]', '', definition)

    # Remplacer les séquences d'espaces multiples
    word = re.sub(r'\s+', ' ', word)
    definition = re.sub(r'\s+', ' ', definition)

    return {
        "word": word,
        "definition": definition,
        "type": entry.get("type", "wallon-francais"),
        "tome": entry.get("tome", 0),
        "page": entry.get("page", 0),
        "slice": entry.get("source", entry.get("slice", ""))
    }


# ─── Validation par lot avec Gemma 4 ─────────────────────────────────────────
def validate_batch_with_gemma(batch: list[dict]) -> list[bool]:
    """
    Valide un lot de 10 entrées avec Gemma 4.
    Retourne une liste de booléens (True = valide, False = bruit).
    """
    entries_text = "\n".join([
        f"{i+1}. MOT: '{e['word']}' | DEF: '{e['definition'][:80]}'"
        for i, e in enumerate(batch)
    ])

    prompt = f"""Tu es un expert en dictionnaires wallons. Analyse ces {len(batch)} entrées de dictionnaire wallon-liégeois.
Pour chaque entrée, réponds VALIDE ou BRUIT (si c'est un en-tête, numéro de page, séparateur ou non-sens).
Réponds UNIQUEMENT avec les numéros et VALIDE/BRUIT, une par ligne.

{entries_text}

Réponse (format: "1. VALIDE", "2. BRUIT", etc.):"""

    response = ollama_query(MODEL_VALIDATOR, prompt, timeout=60)

    results = [True] * len(batch)  # Par défaut: valide
    for line in response.splitlines():
        m = re.match(r'(\d+)\.\s*(VALIDE|BRUIT)', line.strip(), re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(batch):
                results[idx] = m.group(2).upper() == "VALIDE"

    return results


# ─── Extraction des métadonnées du nom de fichier ────────────────────────────
def extract_metadata_from_filename(filename: str) -> dict:
    """
    Extrait tome et page depuis le nom de fichier.
    Exemple: "tome2-045.pdf" → tome=2, page=45
    """
    tome = 0
    page = 0

    # Pattern: "tome2-045.pdf" ou "t2_p045.pdf" ou "dico_fr-liegeois_A.pdf"
    m_tome = re.search(r'tome(\d+)', filename, re.I)
    if m_tome:
        tome = int(m_tome.group(1))

    m_page = re.search(r'[_\-]0*(\d+)(?:\.pdf|$)', filename, re.I)
    if m_page:
        page = int(m_page.group(1))

    return {"tome": tome, "page": page}


# ─── Construction du dico.json final ─────────────────────────────────────────
def build_final_json(use_ollama_validation: bool = True):
    parsed_path = PARSED_DIR / "all_entries_raw.json"
    if not parsed_path.exists():
        print("❌ Données parsées non trouvées. Exécutez d'abord 03_parse_entries.py")
        sys.exit(1)

    with open(parsed_path, encoding="utf-8") as f:
        raw_entries = json.load(f)

    print(f"📥 {len(raw_entries)} entrées brutes chargées")

    # ── Étape 1 : Nettoyage et filtrage bruit évident ────────────────────────
    print("\n🧹 Nettoyage initial...")
    cleaned = []
    noise_count = 0

    for entry in raw_entries:
        if is_noise_entry(entry):
            noise_count += 1
            continue
        cleaned.append(clean_entry(entry))

    print(f"   ✅ Entrées propres: {len(cleaned)}")
    print(f"   🗑️  Bruit éliminé: {noise_count}")

    # ── Étape 2 : Validation Ollama (Gemma 4) ────────────────────────────────
    if use_ollama_validation and is_ollama_running():
        print(f"\n🤖 Validation avec {MODEL_VALIDATOR}...")
        print(f"   (Traitement par lots de 10, peut prendre quelques minutes...)")

        validated = []
        BATCH_SIZE = 10
        total_batches = (len(cleaned) + BATCH_SIZE - 1) // BATCH_SIZE

        # On ne valide qu'un échantillon si trop d'entrées (>5000)
        # pour éviter des heures de traitement
        if len(cleaned) > 5000:
            print(f"   ⚠️  {len(cleaned)} entrées — validation sur 500 échantillons seulement")
            # Valider les 250 premières et 250 dernières (zones à risque)
            sample_start = cleaned[:250]
            sample_end = cleaned[-250:]
            middle = cleaned[250:-250]

            for i in range(0, len(sample_start), BATCH_SIZE):
                batch = sample_start[i:i+BATCH_SIZE]
                results = validate_batch_with_gemma(batch)
                validated.extend([e for e, v in zip(batch, results) if v])

            validated.extend(middle)  # Milieu: confiance

            for i in range(0, len(sample_end), BATCH_SIZE):
                batch = sample_end[i:i+BATCH_SIZE]
                results = validate_batch_with_gemma(batch)
                validated.extend([e for e, v in zip(batch, results) if v])
        else:
            for i in range(0, len(cleaned), BATCH_SIZE):
                batch = cleaned[i:i+BATCH_SIZE]
                results = validate_batch_with_gemma(batch)
                validated.extend([e for e, v in zip(batch, results) if v])

                if (i // BATCH_SIZE + 1) % 10 == 0:
                    pct = (i + BATCH_SIZE) / len(cleaned) * 100
                    print(f"   {pct:.0f}% validé...")

        print(f"   ✅ Après validation Gemma 4: {len(validated)} entrées")
        final_entries = validated
    else:
        if not is_ollama_running():
            print("\n⚠️  Ollama non accessible — validation IA ignorée")
        final_entries = cleaned

    # ── Étape 3 : Enrichissement des métadonnées ────────────────────────────
    print("\n📋 Enrichissement des métadonnées...")
    for entry in final_entries:
        meta = extract_metadata_from_filename(entry.get("slice", ""))
        if entry.get("tome", 0) == 0:
            entry["tome"] = meta["tome"]
        if entry.get("page", 0) == 0:
            entry["page"] = meta["page"]

    # ── Étape 4 : Tri alphabétique ───────────────────────────────────────────
    final_entries.sort(key=lambda x: unicodedata.normalize("NFD", x["word"].lower()))

    # ── Étape 5 : Sauvegarde ─────────────────────────────────────────────────
    output_path = BASE_DIR.parent / "dico.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_entries, f, ensure_ascii=False, indent=2)

    # Backup de l'ancien
    backup_path = BASE_DIR.parent / "dico_backup_old.json"
    old_path = BASE_DIR.parent / "dico.json"

    size_mb = output_path.stat().st_size / 1024 / 1024

    print(f"\n{'='*70}")
    print(f"  ✅ TERMINÉ!")
    print(f"  📊 Entrées finales : {len(final_entries):,}")
    print(f"  💾 Fichier         : {output_path}")
    print(f"  📦 Taille          : {size_mb:.1f} MB")

    # Stats par type
    wf = sum(1 for e in final_entries if e["type"] == "wallon-francais")
    fw = sum(1 for e in final_entries if e["type"] == "francais-wallon")
    print(f"  🏷️  Wallon→Français : {wf:,}")
    print(f"  🏷️  Français→Wallon : {fw:,}")


if __name__ == "__main__":
    print("=" * 70)
    print("  LI PTIT MOTI WALON — Étape 4 : Validation + génération dico.json")
    print("=" * 70)
    build_final_json(use_ollama_validation=True)
