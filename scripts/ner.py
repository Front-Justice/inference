import os
import requests
import time
import re
import json
import sys
import glob
import unicodedata


OLLAMA_MODEL = "phi4"
API_URL = "http://localhost:11434/api/chat"
HISTORY_MAX = 12
MAX_RETRIES = 3
MAX_TAILLE_BLOC = 15000  # caractères

SECTION_KEYWORDS = [
    "RÉPUBLIQUE FRANÇAISE",
    "CEJOURD",
    "A l'effet de juger",
    "La séance ayant été ouverte",
    "Interrogé de", "Interrogés de",
    "Le Président, après avoir fait lire",
    "Ouï M. le Commissaire",
    "L'accusé a été reconduit", "Les accusés ont été reconduits",
    "Les voix recueillies séparément",
    "Sur quoi, et attendu les conclusions",
    "Enjoint au Commissaire du Gouvernement",
    "EXÉCUTOIRE",
    "=== Notes en marge ==="
]

# === Fichiers ===
# Trouver tous les dossiers min_*
dossiers_minutes = sorted(glob.glob("../transcriptions/min_*"))

# Ne garder que ceux qui contiennent un fichier *_corrige.txt
minutes_a_traiter = []
for dossier in dossiers_minutes:
    nom = os.path.basename(dossier)
    nom_minute = nom  # ex: min_001
    fichier_texte = os.path.join(dossier, f"{nom_minute}_corrige.txt")
    if os.path.exists(fichier_texte):
        fichier_sortie = os.path.join(dossier, f"{nom_minute}_ner.json")
        minutes_a_traiter.append((fichier_texte, fichier_sortie))

if not minutes_a_traiter:
    print("Aucune minute trouvée à traiter.")
    sys.exit(0)


# === PROMPTS PAR SECTION ===
PROMPTS_SECTIONS = {
    "RÉPUBLIQUE FRANÇAISE": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "RÉPUBLIQUE FRANÇAISE" à "CEJOURD", trouve ces informations :

- numéro de l'armée
- numéro du jugement (⚠️ le "N° du jugement", parfois écrit "N° DU JUGEMENT", **et non** le "N° de la nomenclature générale")
- date du crime ou du délit 
- séant à (lieu où siège le Conseil de guerre)

Il y a parfois également des informations sur l'exécution de la peine (avant "Au nom du peuple français"). 
Si c'est le cas, trouve :
 - date d'exécution de la peine
 - si la peine a été exécutée, suspendue ou non exécutée
 - motif éventuel de suspension

Retourne un JSON avec ces champs. 
Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "CEJOURD": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "CEJOURD" à "A l'effet de juger", trouve ces informations :
- président du jugement
- grade du président
- juge 1 du jugement
- grade du juge 1
- juge 2 du jugement
- grade du juge 2
- juge 3 du jugement
- grade du juge 3
- juge 4 du jugement
- grade du juge 4
(il y a toujours 4 juges, tu dois les trouver, ils sont entre le président et "tous nommés par le")
- commissaire du gouvernement
- grade du commissaire du gouvernement
- greffier près ledit conseil 
- grade du greffier

Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "A l'effet de juger": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.

⚠️ Important : Il peut y avoir plusieurs accusés listés dans cette section. Tu dois donc extraire les informations pour **chacun des accusés** et retourner une liste JSON.

Pour chaque accusé, retourne les champs suivants :
- nom_de_l_accuse
- prenoms_de_l_accuse
- parents_de_l_accuse
    - prenoms_du_pere
    - nom_et_prenoms_de_la_mere
- date_de_naissance_de_l_accuse
- lieu_de_naissance_de_l_accuse
- departement_de_naissance_de_l_accuse
- profession_de_l_accuse
- lieu_de_residence_de_l_accuse_avant_son_entree_au_service
- etat_civil_de_l_accuse
- enfant_naturel_ou_legitime_de_l_accuse
- caracteristiques_physiques_de_l_accuse
    - taille_de_l_accuse
    - couleur_des_cheveux_de_l_accuse
    - caracteristique_du_front_de_l_accuse
    - couleur_des_yeux_de_l_accuse
    - caracteristique_du_nez_de_l_accuse
    - caracteristique_du_visage_de_l_accuse
    - renseignements_physionomiques_complements
    - marque_particuliere_de_l_accuse
- raison_de_son_inculpation
- condamnations_anterieures (liste ou null)

Retourne un JSON de cette forme :
{
  "A l'effet de juger": {
    "accuses": [
      { ... },
      { ... }
    ]
  }
}

⚠️ Règles :
- Si une information est absente pour un accusé, mets la valeur `null`.
- Ne donne aucune explication, aucun texte en dehors du JSON.
- Le JSON doit toujours être valide.
""",
    "La séance ayant été ouverte": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "La séance ayant été ouverte" à "Interrogé de", trouve ces informations :
- défenseur
    - nom du défenseur
    - grade du défenseur
    - s'il est d'office ou désigné par l'accusé
    
Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "Interrogé de": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Tu as déjà extrait les informations suivantes sur l’accusé à partir de la section "A l'effet de juger" :

[JSON_ACCUSÉ]

Lis maintenant la section "Interrogé de" à "Le Président, après avoir fait lire". Utilise-la pour :
- confirmer ou corriger les informations déjà extraites
- ajouter des informations manquantes si elles sont présentes

Retourne uniquement un JSON **corrigé ou enrichi**, avec les mêmes champs. Ne retourne rien d’autre que ce JSON final.
""",
    "Interrogés de": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Tu as déjà extrait les informations suivantes sur les accusés à partir de la section "A l'effet de juger" :

[JSON_ACCUSÉS]

Lis maintenant la section "Interrogés de" à "Le Président, après avoir fait lire". Utilise-la pour :
- confirmer ou corriger les informations déjà extraites pour chaque accusé
- ajouter des informations manquantes si elles sont présentes

Retourne uniquement un JSON **corrigé ou enrichi** pour tous les accusés, avec les mêmes champs. Ne retourne rien d’autre que ce JSON final.
""",
    "Ouï M. le Commissaire": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918. 
Dans la section "Ouï M. le Commissaire" à "L'accusé a été reconduit", trouve ces informations :
- réquisitoire du commissaire du gouvernement
    - déclaré coupable ou non coupable
    - article du code militaire cité
    
Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "L'accusé a été reconduit": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "L'accusé a été reconduit" à "Les voix recueillies séparément", il y a un seul accusé.

Pour chaque accusé, identifié par son nom et prénom, extrais de manière structurée :
- le numéro de la question : 1^o, 2^o, etc.
- nom_prenom : nom et prénom de l'accusé
- le crime ou délit : caractérise le (outrage, vol, desertion, etc.)
- faits_reproches : ce qui décrivit le crime ou le délit
- date_du_crime : date mentionnée pour ce crime/délit
- lieu_du_crime : lieu mentionné pour ce crime/délit
- complements : tout complément sur les circonstances ou incidents du crime/délit
- complicites : toute mention de complicité, coauteur ou accomplice

⚠️ Il peut y avoir un nombre variable de questions par accusé. Chaque accusé doit être un objet JSON séparé.

Retourne un JSON de la forme :
{
  "Les accusés ont été reconduits": {
    "inculpations": [
      {
        "numero_question": 1,
        "nom_prenom": "...",
        "crime_ou_délit": "...",
        "faits_reproches": "...",
        "date_du_crime": "...",
        "lieu_du_crime": "...",
        "complements": "...",
        "complicites": "..."
      },
      ...
    ]
  }
}

Si une information est absente, mets `null`. Pas d’explication, uniquement un JSON valide.
""",

    "Les accusés ont été reconduits": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "Les accusés ont été reconduits" à "Les voix recueillies séparément", il peut y avoir plusieurs accusés.

Pour chaque accusé, identifié par son nom et prénom, extrais de manière structurée :
- le numéro de la question : 1^o, 2^o, etc.
- nom_prenom : nom et prénom de l'accusé
- le crime ou délit : caractérise le (outrage, vol, desertion, etc.)
- faits_reproches : ce qui décrivit le crime ou le délit
- date_du_crime : date mentionnée pour ce crime/délit
- lieu_du_crime : lieu mentionné pour ce crime/délit
- complements : tout complément sur les circonstances ou incidents du crime/délit
- complicites : toute mention de complicité, coauteur ou accomplice

⚠️ Il peut y avoir un nombre variable de questions par accusé. Chaque accusé doit être un objet JSON séparé.

Retourne un JSON de la forme :
{
  "Les accusés ont été reconduits": {
    "inculpations": [
      {
        "numero_question": 1,
        "nom_prenom": "...",
        "crime_ou_délit": "...",
        "faits_reproches": "...",
        "date_du_crime": "...",
        "lieu_du_crime": "...",
        "complements": "...",
        "complicites": "..."
      },
      ...
    ]
  }
}

Si une information est absente, mets `null`. Pas d’explication, uniquement un JSON valide.
""",

    "Les voix recueillies séparément": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "Les voix recueillies séparément" à "Sur quoi, et attendu les conclusions", trouve ces informations :
- décision du Conseil de guerre
    - coupable ou non coupable
    - unanimité ou majorité des voix
    
Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "Sur quoi, et attendu les conclusions": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "Sur quoi, et attendu les conclusions" à "Enjoint au Commissaire du Gouvernement", trouve pour chaque question posée par le Président :
- nom_prenom_accuse : nom et prénom de l'accusé concerné
- résultat du vote (ex. : oui, non, coupable, non coupable)
- peine prononcée (ex. : emprisonnement, amende, acquittement)
- éventuels compléments d'information (ex. : observations)

Retourne un JSON de la forme :
{
  "Sur quoi, et attendu les conclusions": [
    {
      "nom_prenom_accuse": "...",
      "resultat": "",
      "peine_prononcee": "",
      "complements": ""
    },
    ...
  ]
}

Si une information est absente, mets `null`. Pas d’explication, uniquement un JSON valide.
""",
    "Enjoint au Commissaire du Gouvernement": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "Enjoint au Commissaire du Gouvernement" à "EXÉCUTOIRE", trouve ces informations :
- exécution de la peine
 - date de lecture présent jugement
 - lieu de la séance publique 
 
Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""",
    "EXÉCUTOIRE": """Tu es un expert en extraction d’informations à partir de documents judiciaires historiques.
Le texte qui suit est une minute de jugement militaire française de 1914-1918.
Dans la section "EXÉCUTOIRE", trouve ces informations :
- somme à payer par l'accusé

Retourne un JSON avec ces champs. Si une information est absente, indique `null`. Pas d'explication, uniquement un JSON valide.
""", 
}

# === Fonctions ===

def normaliser(texte: str) -> str:
    """Normalise le texte (NFC, supprime les doubles espaces, harmonise casse)."""
    texte = unicodedata.normalize("NFC", texte)
    return texte

def decouper_en_sections(texte, keywords):
    texte = normaliser(texte)
    pattern = r"(?i)(?=(" + "|".join(re.escape(normaliser(k)) for k in keywords) + r"))"
    indices = [m.start() for m in re.finditer(pattern, texte)]
    if not indices:
        return [("Texte complet", texte)]

    sections = []
    skip_until = -1
    longueur_totale = len(texte)
    seuil_executoire = int(longueur_totale * 0.65)

    for i, start in enumerate(indices):
        if start < skip_until:
            continue

        # Identifier le mot-clé correspondant
        titre_section = None
        for kw in keywords:
            if texte[start:].upper().startswith(normaliser(kw).upper()):
                titre_section = kw
                break
        if not titre_section:
            continue

        # Cas spécial EXÉCUTOIRE → seulement si on est dans le dernier quart
        if titre_section.upper() == "EXÉCUTOIRE" and start >= seuil_executoire:
            end = texte.find("=== Notes en marge ===", start)
            if end == -1:
                end = len(texte)
            skip_until = end
        elif titre_section.upper() == "EXÉCUTOIRE" and start < seuil_executoire:
            # On ignore cette occurrence, on continue la boucle
            continue
        else:
            end = indices[i+1] if i+1 < len(indices) else len(texte)

        section = texte[start:end].strip()
        sections.append((titre_section, section))

    return sections

def envoyer_prompt_sur_bloc(prompt, bloc):
    messages = [
        {
            "role": "system",
            "content": "Tu es un expert en extraction d’informations à partir de documents judiciaires historiques. Retourne uniquement un JSON valide, sans explication."
        },
        {
            "role": "user",
            "content": prompt + "\n\nTexte :\n" + bloc
        }
    ]

    for tentative in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            }, timeout=60)

            response.raise_for_status()
            data = response.json()

            # Format GPT-like
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            # Format Ollama-like
            elif "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                print("❌ Structure inattendue :", data.keys())
                return None

        except Exception as e:
            print(f"❌ Erreur pendant la requête (tentative {tentative+1}/{MAX_RETRIES}) : {e}")
            time.sleep(1)

    print("⛔ Abandon de ce bloc après échecs répétés.")
    return None

# === Traitement principal ===
for fichier_texte, fichier_sortie in minutes_a_traiter:
    print(f"\n📂 Traitement de la minute : {fichier_texte}")
    
    with open(fichier_texte, "r", encoding="utf-8") as f:
        texte_jugement = f.read()

    sections = decouper_en_sections(texte_jugement, SECTION_KEYWORDS)

    resultat_json = {}

    for nom_section, contenu in sections:
        print(f"📚 Traitement de la section : {nom_section}")

        prompt = PROMPTS_SECTIONS.get(nom_section)

        # Cas spécial pour "Interrogé de"
        if nom_section == "Interrogé de":
            donnees_existantes = resultat_json.get("A l'effet de juger", {})
            if not donnees_existantes:
                print("⚠️ Aucune donnée à enrichir pour 'Interrogé de', section ignorée.")
                continue
            donnees_json_str = json.dumps(donnees_existantes, ensure_ascii=False, indent=2)
            prompt = PROMPTS_SECTIONS["Interrogé de"].replace("[JSON_ACCUSÉ]", donnees_json_str)

        if prompt:
            reponse_brute = envoyer_prompt_sur_bloc(prompt, contenu)
            if reponse_brute:
                json_str = reponse_brute.strip()
                if json_str.startswith("```"):
                    json_str = "\n".join(json_str.splitlines()[1:-1])
                try:
                    resultat = json.loads(json_str)
                    if nom_section == "Interrogé de":
                        resultat_json["A l'effet de juger"] = resultat
                        print("✅ Données de l'accusé enrichies via 'Interrogé de'")
                    else:
                        resultat_json[nom_section] = resultat
                        print(f"✅ Section {nom_section} traitée avec succès.")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON invalide pour la section {nom_section} :", e)
                    resultat_json[nom_section] = {"_raw_response": json_str}
        else:
            print(f"⚠️ Pas de prompt défini pour la section : {nom_section}, elle est ignorée.")

    # === Sauvegarde du JSON final ===
    print(f"💾 Sauvegarde du JSON structuré dans {fichier_sortie}")
    with open(fichier_sortie, "w", encoding="utf-8") as f:
        json.dump(resultat_json, f, ensure_ascii=False, indent=4)

    print("✅ Traitement terminé pour cette minute.")
