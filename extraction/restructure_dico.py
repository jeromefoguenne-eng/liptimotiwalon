#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
from pathlib import Path

# Marqueurs grammaticaux
GRAMMAR_MAP = {
    "m.": "masculin",
    "f.": "féminin",
    "adj.": "adjectif",
    "adv.": "adverbe",
    "prép.": "préposition",
    "conj.": "conjonction",
    "interj.": "interjection",
    "loc.": "locution",
    "n.pr.": "nom propre",
    "pron.": "pronom",
    "num.": "numéral",
    "art.": "article",
    "part.": "participe",
    "suff.": "suffixe",
    "préf.": "préfixe",
    "v. tr.": "verbe transitif",
    "v. intr.": "verbe intransitif",
    "v. réfl.": "verbe réfléchi",
    "v. imp.": "verbe impersonnel",
    "v.": "verbe"
}

GRAMMAR_RE = re.compile(
    r'\b(v\.\s*tr\.|v\.\s*intr\.|v\.\s*réfl\.|v\.\s*imp\.|v\.|m\.|f\.|adj\.|adv\.|prép\.|conj\.|interj\.|loc\.|n\.pr\.|pron\.|num\.|art\.|part\.|suff\.|préf\.)(?![a-zA-Zàâéèêëîïôùûüœæç])',
    re.IGNORECASE
)

# Domaines spécialisés typiques de Jean Haust
DOMAINE_MARKERS = [
    "fig.", "arch.", "t. de houill.", "t. de bat.", "t. enf.", "t. rural", "néol.", 
    "techn.", "arg.", "pop.", "t. de serr.", "t. d'arm.", "t. de chaudr.", "prov."
]

def restructure_entry(e: dict) -> dict:
    word = e.get("word", "").strip()
    definition_text = e.get("definition", "").strip()
    tome = e.get("tome", 2)
    page = e.get("page", 0)
    slice_name = e.get("slice", "")
    entry_type = e.get("type", "wallon-francais")
    
    # 1. Extraire la catégorie grammaticale et le genre
    grammar = e.get("grammar", "").strip()
    genre = ""
    
    # Si le mot ou la définition contient une indication de genre/catégorie
    if not grammar:
        gm = GRAMMAR_RE.search(word)
        if gm:
            grammar = gm.group(0).rstrip('.')
        else:
            gm = GRAMMAR_RE.search(definition_text[:60])
            if gm:
                grammar = gm.group(0).rstrip('.')
                
    # Normalisation du genre
    if grammar.lower() in ("m", "m.", "masculin"):
        genre = "masculin"
        grammar = "nom"
    elif grammar.lower() in ("f", "f.", "féminin"):
        genre = "féminin"
        grammar = "nom"
    elif grammar in GRAMMAR_MAP:
        grammar = GRAMMAR_MAP[grammar]
        if "masculin" in grammar:
            genre = "masculin"
            grammar = "nom"
        elif "féminin" in grammar:
            genre = "féminin"
            grammar = "nom"

    # 2 & 3. Extraire la prononciation et l'origine (étymologie)
    prononciation = ""
    origine = ""
    
    # Recherche et extraction des crochets (y compris non fermés) dans la définition
    brackets = []
    start_idx = definition_text.find('[')
    while start_idx != -1:
        end_idx = definition_text.find(']', start_idx)
        if end_idx != -1:
            content = definition_text[start_idx+1:end_idx].strip()
            definition_text = definition_text[:start_idx] + " " + definition_text[end_idx+1:]
        else:
            content = definition_text[start_idx+1:].strip()
            definition_text = definition_text[:start_idx].strip()
        
        if content:
            brackets.append(content)
        start_idx = definition_text.find('[')
        
    # Extraire également les crochets du mot-vedette
    word_brackets = []
    w_start_idx = word.find('[')
    while w_start_idx != -1:
        w_end_idx = word.find(']', w_start_idx)
        if w_end_idx != -1:
            w_content = word[w_start_idx+1:w_end_idx].strip()
            word = word[:w_start_idx] + " " + word[w_end_idx+1:]
        else:
            w_content = word[w_start_idx+1:].strip()
            word = word[:w_start_idx].strip()
        if w_content:
            word_brackets.append(w_content)
        w_start_idx = word.find('[')
        
    # Classer tous les crochets extraits
    for b in (word_brackets + brackets):
        if b.startswith('-') or len(b) <= 6:
            if not prononciation:
                prononciation = b
            else:
                prononciation += "; " + b
        else:
            if not origine:
                origine = b
            else:
                origine += "; " + b

    # Nettoyage des espaces doubles créés par le retrait des crochets
    definition_text = re.sub(r'\s+', ' ', definition_text).strip()
    word = re.sub(r'\s+', ' ', word).strip()

    # 4. Extraire les domaines
    domaines = []
    for dom in DOMAINE_MARKERS:
        if dom in definition_text[:120] or dom in word:
            domaines.append(dom.rstrip('.'))

    # 5. Extraire les renvois (Voy. xxx, Voy. aussi xxx, Cf. xxx)
    renvois = []
    renvoi_matches = re.finditer(r'\b(?:Voy\.|voir|Voir|Cf\.)\s+([a-zàâéèêëîïôùûüçœæåÅ\'\-,\s]{1,100})', definition_text, re.I)
    for rm in renvoi_matches:
        # Extraire les mots séparés par des virgules
        targets = [t.strip().rstrip(',;.:') for t in rm.group(1).split(',')]
        for t in targets:
            if t and len(t) < 40 and not any(k in t.lower() for k in ("les", "le", "la", "tome", "page", "art", "subst")):
                renvois.append(t)
    
    # Nettoyer les doublons dans renvois
    renvois = list(dict.fromkeys(renvois))

    # 6. Extraire les synonymes (syn. xxx, Syn. xxx)
    synonymes = []
    syn_matches = re.finditer(r'\b(?:syn\.|Syn\.)\s+([a-zàâéèêëîïôùûüçœæåÅ\'\-,\s]{1,60})', definition_text, re.I)
    for sm in syn_matches:
        targets = [t.strip().rstrip(',;.:') for t in sm.group(1).split(',')]
        for t in targets:
            if t and len(t) < 30:
                synonymes.append(t)
    synonymes = list(dict.fromkeys(synonymes))

    # 7. Définitions et Exemples / Expressions
    definitions = []
    exemples = []
    expressions = []
    variantes = []
    notes = ""
    
    # Séparer le texte principal par le séparateur sub-entry "|"
    parts_by_pipe = definition_text.split('|')
    main_text = parts_by_pipe[0].strip()
    
    # Gérer les sub-entries / variantes de la forme | xxx
    if len(parts_by_pipe) > 1:
        for extra in parts_by_pipe[1:]:
            extra = extra.strip()
            if extra:
                # Si le bloc contient syn., c'est une variante ou expression
                variantes.append(extra)

    if entry_type == "wallon-francais":
        # Tome 2: Wallon -> Français
        # Le format est typiquement: "définition(s) : exemple1 ; exemple2"
        # Ou "définition(s) ; exemple1" s'il n'y a pas de colon
        colon_index = main_text.indexOf(':') if hasattr(main_text, 'indexOf') else main_text.find(':')
        
        if colon_index != -1:
            def_part = main_text[:colon_index].strip()
            examples_part = main_text[colon_index+1:].strip()
        else:
            # S'il n'y a pas de colon, on prend la première partie avant le premier point/virgule
            # comme la définition si elle semble française
            semicolon_index = main_text.find(';')
            if semicolon_index != -1:
                def_part = main_text[:semicolon_index].strip()
                examples_part = main_text[semicolon_index+1:].strip()
            else:
                def_part = main_text
                examples_part = ""
                
        # Nettoyage des définitions
        # On sépare par des virgules ou des points-virgules les synonymes de traduction
        raw_defs = [d.strip() for d in re.split(r'[,;]', def_part) if d.strip()]
        for rd in raw_defs:
            # Supprimer les marqueurs grammaticaux résiduels
            rd_clean = GRAMMAR_RE.sub('', rd).strip().lstrip(',;.: ')
            if rd_clean and not any(k in rd_clean.lower() for k in ("voy.", "cf.", "syn.")):
                definitions.append(rd_clean)
                
        # Parsing des exemples
        if examples_part:
            raw_examples = [ex.strip() for ex in examples_part.split(';') if ex.strip()]
            for re_ex in raw_examples:
                # Nettoyer les renvois
                if any(k in re_ex.lower() for k in ("voy.", "cf.")):
                    continue
                # Séparer Wallon du Français par la première virgule
                comma_idx = re_ex.find(',')
                if comma_idx != -1:
                    wal = re_ex[:comma_idx].strip()
                    fra = re_ex[comma_idx+1:].strip()
                    # Remplacer les tirets représentant le mot par ~
                    wal = wal.replace('—', '~').replace('–', '~')
                    exemples.append({"wallon": wal, "francais": fra})
                else:
                    wal = re_ex.replace('—', '~').replace('–', '~')
                    exemples.append({"wallon": wal, "francais": ""})
                    
    else:
        # Tome 3: Français -> Wallon
        # Le format est: "traduction_wallonne ; exemple1 ; exemple2"
        # La traduction wallonne est le premier élément
        parts = [p.strip() for p in main_text.split(';') if p.strip()]
        if parts:
            def_part = parts[0]
            # Nettoyer
            def_part = GRAMMAR_RE.sub('', def_part).strip().lstrip(',;.: ')
            definitions.append(def_part)
            
            for re_ex in parts[1:]:
                if any(k in re_ex.lower() for k in ("voy.", "cf.")):
                    continue
                # Souvent de la forme "exemple en français, traduction en wallon" ou inversement
                comma_idx = re_ex.find(',')
                if comma_idx != -1:
                    wal = re_ex[comma_idx+1:].strip()
                    fra = re_ex[:comma_idx].strip()
                    exemples.append({"wallon": wal, "francais": fra})
                else:
                    exemples.append({"wallon": re_ex, "francais": ""})

    # Si aucune définition n'a été extraite, utiliser la définition d'origine comme fallback
    if not definitions:
        definitions.append(main_text)

    # Nettoyer le mot-vedette des indications grammaticales
    mot_clean = GRAMMAR_RE.sub('', word).strip().rstrip(',;.: ')

    return {
        "mot": mot_clean,
        "categorie": grammar,
        "genre": genre,
        "prononciation": prononciation,
        "origine": origine,
        "domaines": domaines,
        "definitions": definitions,
        "exemples": exemples,
        "expressions": expressions,
        "synonymes": synonymes,
        "variantes": variantes,
        "renvois": renvois,
        "notes": notes,
        "page": str(page),
        "tome": tome,
        "slice": slice_name,
        "type": entry_type
    }

def restructure_database(input_file: Path, output_file: Path):
    print(f"Chargement de {input_file} ...")
    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Restructuration de {len(data)} entrées...")
    restructured = [restructure_entry(e) for e in data]
    
    print(f"Sauvegarde dans {output_file} ...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(restructured, f, ensure_ascii=False, indent=2)
        
    # Format JS
    js_file = output_file.with_suffix(".js")
    print(f"Sauvegarde format JS dans {js_file} ...")
    with open(js_file, "w", encoding="utf-8") as f:
        f.write("window.dictionaryData = ")
        json.dump(restructured, f, ensure_ascii=False)
        f.write(";\n")
    print("Terminé !")

if __name__ == "__main__":
    import sys
    infile = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../dico.json")
    outfile = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("../dico.json")
    restructure_database(infile, outfile)
