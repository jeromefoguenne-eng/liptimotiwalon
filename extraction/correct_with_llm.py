import json
import re
import sys
import time
import requests
from pathlib import Path

# Fix terminal encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROJ = Path(__file__).parent.parent
DICO_PATH = PROJ / "dico.json"
MAP_FILE = PROJ / "extraction" / "wallon_a_rond_clean.json"
COMMON_FILE = PROJ / "extraction" / "wallon_common_a_rond.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:latest"


# ---------------------------------------------------------------------------
# Vérification Ollama
# ---------------------------------------------------------------------------
def is_ollama_running() -> bool:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        return r.status_code == 200
    except:
        return False


def query_ollama(prompt: str) -> str:
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.05,
                "num_predict": 100
            }
        }, timeout=45)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"   [WARN] Erreur Ollama: {e}")
        return ""


# ---------------------------------------------------------------------------
# Chargement du Mapping & Dico
# ---------------------------------------------------------------------------
def load_mapping() -> dict:
    mapping = {}
    
    # 1. Base mapping (Wiktionary clean list)
    if MAP_FILE.exists():
        with open(MAP_FILE, encoding="utf-8") as f:
            data = json.load(f)
        mapping.update(data.get("mapping", {}))
        
    # 2. Extract words from common_words Wiktionary text
    if COMMON_FILE.exists():
        try:
            with open(COMMON_FILE, encoding="utf-8") as f:
                common_data = json.load(f)
            common_text = common_data.get("common_words", [])
            ref_words = set()
            for text in common_text:
                # Find all tokens containing å or Å
                tokens = re.findall(r'\b[a-zA-ZåÅàâéèêëîïôùûüçœæ\-\']*[åÅ][a-zA-ZåÅàâéèêëîïôùûüçœæ\-\']*\b', text)
                for t in tokens:
                    ref_words.add(t.strip())
            
            # Add to mapping
            added = 0
            for w in ref_words:
                w_lower = w.lower()
                # Create key by stripping all accents from a/e/i/o/u to get base letters
                key = w_lower.replace('å', 'a').replace('â', 'a').replace('à', 'a')
                if len(key) >= 3 and key not in mapping:
                    mapping[key] = w_lower
                    added += 1
            if added > 0:
                print(f"ℹ️ Enriched mapping with {added} words from common Wiktionary list.")
        except Exception as e:
            print(f"ℹ️ Could not load common_words: {e}")
            
    # 3. Enrich with wallon_a_rond_reference.json (856 reference words)
    ref_file = PROJ / "extraction" / "wallon_a_rond_reference.json"
    if ref_file.exists():
        try:
            with open(ref_file, encoding="utf-8") as f:
                ref_list = json.load(f)
            added = 0
            for w in ref_list:
                w_lower = w.lower().strip()
                # Create key by stripping all accents from a/e/i/o/u to get base letters
                key = w_lower.replace('å', 'a').replace('â', 'a').replace('à', 'a')
                if len(key) >= 3 and key not in mapping:
                    mapping[key] = w_lower
                    added += 1
            if added > 0:
                print(f"ℹ️ Enriched mapping with {added} words from wallon_a_rond_reference.json.")
        except Exception as e:
            print(f"ℹ️ Could not load wallon_a_rond_reference: {e}")
            
    return mapping


def save_mapping(mapping: dict):
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump({"mapping": mapping}, f, ensure_ascii=False, indent=2)
    print(f"💾 Mapping sauvegardé ({len(mapping)} mots) : {MAP_FILE}")


def load_dico() -> list[dict]:
    with open(DICO_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_dico(dico: list[dict]):
    with open(DICO_PATH, "w", encoding="utf-8") as f:
        json.dump(dico, f, ensure_ascii=False, indent=2)
    print(f"💾 dico.json sauvegardé ({len(dico)} entrées) : {DICO_PATH}")
    
    # Également sauvegarder au format JS pour support local file://
    js_path = DICO_PATH.with_suffix(".js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.dictionaryData = ")
        json.dump(dico, f, ensure_ascii=False)
        f.write(";\n")
    print(f"💾 dico.js sauvegardé : {js_path}")


# ---------------------------------------------------------------------------
# Accent-Insensitive Regex Generation
# ---------------------------------------------------------------------------
def make_accent_insensitive_regex(key: str) -> re.Pattern:
    """
    Génère un regex pour la clé qui tolère les variations d'accents du PDF.
    Ex: 'awe' -> matches '[aàâå]w[eéèêë]'
    """
    pattern_parts = []
    for char in key.lower():
        if char == 'a':
            pattern_parts.append('[aàâå]')
        elif char == 'e':
            pattern_parts.append('[eéèêë]')
        elif char == 'i':
            pattern_parts.append('[iîï]')
        elif char == 'o':
            pattern_parts.append('[oô]')
        elif char == 'u':
            pattern_parts.append('[uûù]')
        else:
            pattern_parts.append(re.escape(char))
            
    pattern_str = "".join(pattern_parts)
    return re.compile(
        r'(?<![a-zA-ZàâéèêëîïôùûüœæçåÅ\-\'])' + pattern_str + r'(?![a-zA-ZàâéèêëîïôùûüœæçåÅ\-\'])',
        re.IGNORECASE
    )


# ---------------------------------------------------------------------------
# Application du Mapping Statique (Version Flexible)
# ---------------------------------------------------------------------------
def apply_static_mapping(dico: list[dict], mapping: dict) -> tuple[list[dict], int, int]:
    print("\nApplying static mapping corrections (accent-insensitive lookup)...")
    
    # Préchauffer les regex pour toutes les clés
    sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
    regex_map = []
    for key in sorted_keys:
        val = mapping[key]
        if key == val.lower():
            continue  # Pas de correction nécessaire (le mot d'origine a déjà la bonne forme)
        regex_map.append((make_accent_insensitive_regex(key), val))

    word_corr = 0
    def_corr = 0
    corrected_dico = []

    for entry in dico:
        new_entry = dict(entry)
        
        # Corriger le mot-vedette (Tome 2 uniquement)
        if entry.get("type") == "wallon-francais":
            word = entry.get("word", "")
            word_changed = False
            for pattern, val in regex_map:
                new_word = pattern.sub(val, word)
                if new_word != word:
                    word = new_word
                    word_changed = True
            if word_changed:
                new_entry["word"] = word
                new_entry["a_ring_corrected"] = True
                word_corr += 1
                
        # Corriger la définition (deux tomes)
        defn = entry.get("definition", "")
        defn_changed = False
        for pattern, val in regex_map:
            new_defn = pattern.sub(val, defn)
            if new_defn != defn:
                defn = new_defn
                defn_changed = True
        if defn_changed:
            new_entry["definition"] = defn
            new_entry["a_ring_corrected"] = True
            def_corr += 1
            
        corrected_dico.append(new_entry)

    print(f"   -> Words corrected: {word_corr}")
    print(f"   -> Definitions corrected: {def_corr}")
    return corrected_dico, word_corr, def_corr


# ---------------------------------------------------------------------------
# Détection des Mots Suspects
# ---------------------------------------------------------------------------
def is_suspect(word: str) -> bool:
    w = word.lower().strip()
    w = re.sub(r'^\d+\.\s*', '', w)  # Homographe prefix
    w = re.split(r'[\s,;:()\[\]]', w)[0]  # First token
    
    if not w or w[0] not in 'aàâäå':
        return False
    if len(w) < 4 or len(w) > 20:
        return False
    if w.startswith("av") or w.startswith("au") or w.startswith("af"):
        return False
    if "å" in w or "Å" in w:
        return False
    return True


# ---------------------------------------------------------------------------
# Correction par LLM Local
# ---------------------------------------------------------------------------
def run_llm_corrections(dico: list[dict], mapping: dict) -> tuple[list[dict], dict]:
    if not is_ollama_running():
        print("\n[WARN] Ollama is not running. Skipping LLM corrections.")
        return dico, mapping

    print(f"\nRunning LLM corrections with {MODEL}...")
    suspect_entries = []
    
    # Trouver les suspects qui ne sont pas couverts par le mapping
    for idx, entry in enumerate(dico):
        if entry.get("type") == "wallon-francais":
            word = entry.get("word", "")
            if is_suspect(word):
                word_clean = re.sub(r'^\d+\.\s*', '', word).strip()
                first_token = re.split(r'[\s,;:()\[\]]', word_clean)[0].lower()
                # Supprimer les accents pour vérifier la présence dans le mapping
                key = first_token.replace('å', 'a').replace('â', 'a').replace('à', 'a')
                if key not in mapping:
                    suspect_entries.append((idx, entry, first_token, key))

    print(f"   Found {len(suspect_entries)} suspect words to check via LLM.")
    if not suspect_entries:
        return dico, mapping

    corrected_count = 0
    new_mappings = {}

    for count, (idx, entry, first_token, key) in enumerate(suspect_entries, 1):
        # Limiter à 150 appels pour éviter les temps de traitement excessifs si le jeu est grand
        if count > 150:
            print("   [INFO] Reached batch limit of 150 LLM requests. Saving progress.")
            break
            
        word = entry["word"]
        defn = entry["definition"]
        
        # Skip if we already checked it in this run
        if key in new_mappings:
            continue

        prompt = f"""Tu es un expert du dialecte wallon-liégeois de Jean Haust.
Détermine si le mot wallon suivant '{first_token}' (définition: '{defn[:120]}') doit s'écrire avec un 'å' initial (a rond en chef, typique du liégeois) ou s'il commence par un simple 'a'.
Réponds uniquement par le mot corrigé avec 'å' si c'est nécessaire, ou par le mot d'origine si aucun 'å' ne doit être mis.
Exemples :
- 'abaye' (définition: abbaye) -> 'åbaye'
- 'amich' (définition: ami) -> 'åmigh'
- 'acater' (définition: acheter) -> 'åcater'
- 'aler' (définition: aller) -> 'aler'

Mot à analyser : '{first_token}'
Définition : '{defn[:120]}'
Réponse (renvoie uniquement le mot corrigé ou d'origine) :"""

        print(f"[{count}/50] Checking '{first_token}' ...", end="", flush=True)
        llm_reply = query_ollama(prompt)
        llm_reply = re.sub(r'[^a-zA-ZåÅàâéèêëîïôùûüçœæ\-\']', '', llm_reply).strip()

        if llm_reply and "å" in llm_reply.lower() and llm_reply.lower() != first_token:
            print(f" -> Corrected to '{llm_reply}'")
            new_mappings[key] = llm_reply.lower()
            corrected_count += 1
        else:
            print(f" -> OK (keeps '{first_token}')")
            # Cache positive match to avoid checking again
            new_mappings[key] = first_token

    if corrected_count > 0:
        # Merge new mappings
        for k, v in new_mappings.items():
            if "å" in v:
                mapping[k] = v
        # Save mapping
        save_mapping(mapping)
        # Apply mapping again to update dico
        dico, _, _ = apply_static_mapping(dico, mapping)

    print(f"\nLLM Run completed. Corrected {corrected_count} new words.")
    return dico, mapping


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not DICO_PATH.exists():
        print(f"❌ dico.json not found at {DICO_PATH}")
        sys.exit(1)

    dico = load_dico()
    mapping = load_mapping()

    # Step 1: Apply static mapping (flexible accent-insensitive matching)
    dico, w_corr, d_corr = apply_static_mapping(dico, mapping)

    # Step 2: Run LLM corrections for remaining suspects
    dico, mapping = run_llm_corrections(dico, mapping)

    # Save final results
    save_dico(dico)
    print("\n🏁 Finished all corrections!")


if __name__ == "__main__":
    main()
