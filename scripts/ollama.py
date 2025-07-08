import os
import requests
import time
import re

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
    "Interrogé de",
    "Le Président, après avoir fait lire",
    "Ouï M. le Commissaire",
    "L'accusé a été reconduit",
    "Les voix recueillies séparément",
    "Sur quoi, et attendu les conclusions",
    "Enjoint au Commissaire du Gouvernement",
    "EXÉCUTOIRE",
    "=== Notes en marge ==="
]

EXEMPLES_PAR_SECTION = EXEMPLES_PAR_SECTION = {
    "RÉPUBLIQUE FRANÇAISE": """Exemple : RÉPUBLIQUE FRANÇAISE.
N^o DU JUGEMENT:[numéro]
(Art. 140 du Code de justice militaire.)
MINUTE DE JUGEMENT.

JUGEMENT rendu par le CONSEIL DE GUERRE permanent du Quartier Général de la IV^e Armée séant à [lieu].

N^o 967 DE LA NOMENCLATURE GÉNÉRALE.
FORMULE N^o 16.
N^o [numéro] D'ORDRE.

Date du crime ou du délit.
[date]

AU NOM DU PEUPLE FRANÇAIS,
Le Conseil de guerre permanent du Quartier Général de la IV^e Armée a rendu le jugement dont la teneur suit:""",

    "CEJOURD'HUI": """Exemple : CEJOURD'HUI [date]
Le Conseil de guerre permanent du Quartier Général de la IV^e Armée composé, conformément àux l'articles 35 et 10 du Code de justice militaire, de MM.
[nom], [grade]
Président;

[nom], [grade].
[nom], [grade].
[nom], [grade].
[nom], [grade].
Juges.

tous nommés par le (1) Général Commandant la IV^e armée
M. [nom], [grade];
M. [nom], [grade].

Lesquels ne se trouvent dans aucun des cas d'incompatibilité prévus par les articles 22, 23 et 24 du Code précité;
Le Conseil, convoqué par l'ordre du commandant, conformément à l'article 111 du Code de justice militaire, s'est réuni dans le lieu ordinaire de ses séances, en audience publique""",

    "A l'effet de juger": """Exemple : A l'effet de juger le nommé [nom], [prénoms], fils de [père] et de [mère], né le [date] à [lieu], département de [département], profession de [profession], résidant, avant son entrée au service, à [lieu].

Taille d’un mètre [taille], cheveux [cheveux], front [front], yeux [yeux], nez [nez], visage [visage].

Renseignements physionomiques complémentaires : [description]
Marques particulières : [description]

Inculpé d’avoir :
1° [chef d’inculpation 1]
2° [chef d’inculpation 2]
[...]

Condamnations antérieures :
- [date] : [juridiction]. [nature]. [peine ou décision]
- [date] : [juridiction]. [nature]. [peine ou décision]""",


    "La séance ayant été ouverte" : """Exemple : La séance ayant été ouverte, le Président a fait apporter et déposer devant lui, sur le bureau, un exemplaire du Code de justice militaire, du Code d'instruction criminelle et du Code pénal ordinaire, et ordonné à la garde d'amener l'accusé, qui a été introduit, libre et sans fers, devant le Conseil, accompagné de son défenseur M. [nom], [profession]""",

    "Interrogé de": """Exemple : Interrogé de ses nom, prénoms, âge, lieu de naissance, état, profession et domicile, l'accusé a répondu se nommer :
[nom complet], [âge] ans, né à [lieu de naissance], département de [département],
[état civil : célibataire / marié / veuf], [nombre d’enfants éventuel],
profession de [profession], demeurant à [ville], département de [département].""",


    "Le Président, après avoir fait lire" : """Exemple : Le Président, après avoir fait lire par le greffier l'ordre de convocation, le rapport prescrit par l'article 108 du Code de justice militaire, et les pièces dont la lecture lui a paru nécessaire, a fait connaître a l'accusé les faits à raison desquels il est poursuivi, et lui a donné, ainsi qu'au défenseur, l'avertissement indiqué en l'article 121 dudit Code;
Après quoi, il a procédé à l'interrogatoire de l'accusé et a fait entendre publiquement et séparément les témoins à charge (1) ; lesdits témoins ayant au préalable prêté serment de parler sans haine et sans crainte, juré de dire toute la vérité et rien que la vérité;
Et le Président ayant, en outre, rempli à leur égard les formalités prescrites par les articles 317 et 319 du Code d'instruction criminelle; (2)""",

    "Ouï M. le Commissaire" : """Exemple : Ouï M. le Commissaire du Gouvernement en ses réquisitions tendant à ce que (3)
[accusé / susnommé] soit déclaré [coupable / innocent] des faits relevés contre lui dans l'ordre de mise en jugement et qu'il lui soit fait application des [articles du code]
et l'accusé dans ses moyens de défense, tant par lui-même que par son défenseur, lesquels ont déclaré n'avoir rien à ajouter à leurs moyens de défense, et ont eu la parole les derniers, le Président a déclaré les débats terminés, et il a ordonné au défenseur et a l'accusé de se retirer.""",

    "L'accusé a été reconduit": """Exemple : L'accusé a été reconduit par l'escorte à la prison.
Le Commissaire du Gouvernement, le Greffier et les assistants dans l'auditoire se sont retirés sur l'invitation du Président.
(4) Le Conseil, délibérant à huis clos, s'est retiré dans la chambre des délibérations.
Le Président a posé les questions, conformément à l'article 132 du Code de justice militaire, ainsi qu'il suit :

1^re question — [question]
2^e question — [question]

Il a été voté au scrutin secret, conformément à l'article 191 du Code de justice militaire, sur chacune de ces questions, ainsi que sur les circonstances atténuantes et sur l'application éventuelle de la loi de sursis.""",

    "Les voix recueillies séparément" : """Exemple : Les voix recueillies séparément, conformément à l'article 131 du Code de justice militaire, en commençant par le grade inférieur, le Président ayant émis son opinion le dernier, le Conseil de guerre permanent déclare.
[question] : [réponse]""",

    "Sur quoi, et attendu les conclusions" : """Exemple : Sur quoi, et attendu les conclusions prises par le Commissaire du Gouvernement dans ses réquisitions, le Président a lu le texte de la loi, recueilli de nouveau les voix dans la forme prescrite par les articles 131 et 134 du Code de justice militaire pour l'application de la peine.
Le Conseil est rentré en séance publique, le Président a lu les motifs qui précèdent et le dispositif ci-dessous.
En conséquence, le Conseil (1) [sentence prononcée]""",

    "Enjoint au Commissaire du Gouvernement" : """Exemple : Enjoint au Commissaire du Gouvernement de faire donner immédiatement en sa présence lecture du présent jugement au [condamné / acquitté / susnommé] devant la garde rassemblée sous les armes,
de avertir que la loi accorde un délai de trois jours francs pour se pourvoir en cassation (1), ou de vingt-quatre heures pour se pourvoir en revision (2).

FAIT, clos et jugé sans désemparer, en séance publique, à [lieu], les jour, mois et an que dessus.

En conséquence, LE PRÉSIDENT DE LA RÉPUBLIQUE MANDE et ORDONNE à tous huissiers sur ce requis de mettre ledit jugement à exécution; aux Procureurs généraux et aux Procureurs de la République près les tribunaux de première instance d'y tenir la main; à tous commandants et officiers de la force publique de prêter main-forte lorsqu'ils en seront légalement requis.

En foi de quoi le présent jugement a été signé par les Membres du Conseil et par le Greffier.
[Signature = +]

L'an mil neuf cent [date] le présent jugement a été lu par nous, Greffier soussigné, au [condamné / acquitté / susnommé ] [nom complet]
averti par le Commissaire du Gouvernement que l'article 44 de la loi du 17 avril 1906 accorde trois jours pour se pourvoir en cassation (1), ou que les articles 141 et 143 du Code de justice militaire accordent vingt-quatre heures pour se pourvoir en revision (2), lesquels commencent à courir de l'expiration du présent jour,
Cette lecture faite en présence de la Garde rassemblée sous les armes.

Le Commissaire du Gouvernement,
[Signature = +]
Le Greffier,
[Signature = +]

[Note marginale]""",

    "EXÉCUTOIRE" : """Exemple : EXÉCUTOIRE.
Vu la procédure instruite contre le [nom] et les frais d'icelle dont le détail suit:
1^o Coût du transport des pièces et objets pouvant servie à conviction ou à décharge................. ......
2^o Honoraires des officiers de santé, médecins, chirurgiens civils, sages-femmes, experts, interprètes, traducteurs et
autres, appelés en justice.................................................................
3^o Indemnités accordées aux témoins civils et militaires..............................................
4^o Frais de garde de scellés et ceux de mise en fourrière.............................................
5^o Indemnités de route, de transport et de séjour, accordées aux membres des tribunaux militaires pour les dépla-
cements auxquels l'instruction des procédures peut donner lieu, ainsi que toutes autres dépenses nécessitées
de ce chef..............................................................................
6^o Port des lettres et paquets pour l'instruction, sauf le port des lettres résultant de l'application de la loi du
15 juin 1899............................................................................
7^o Frais l'impression des arrêts, jugements et ordonnances de justice, quand il y a lieu..................
8^o Prime de capture des contumax, des déserteurs et des insoumis......................................
9^o Frais résultant de l'obtention des extraits du casier judiciaire......................................... [montant]
10^o Prix du bulletin n^o 1 et du duplicata dudit (décret du 12 décembre 1899, art. 13)..................... [montant]
11^o Coût des bulletins n^o 1 et du duplicata de ces bulletins établis par les greffiers des conseils de guerre au sujet
des condamnations prononcées par ces conseils (décret du 12 décembre 1899, art. 13).................... [montant]
12^o Frais de procédure ou coût du jugement........................................................ [montant]
13^o Amende......................................................................................... [montant]
14^o Décimes additionnels (en France)............................................................... [montant]
15^o Frais fixes de procédure devant la Cour de cassation ou le Conseil de revision...........................
16^o Frais fixes de procédure devant le Conseil de guerre jugeant en 2^e instance.............................
TOTAL.................................................. [montant]

Vu le dispositif du jugement définitif, l'article 139 du Code de justice militaire, le Président du- Conseil de guerre permanent de la [nom de l'armée] liquide les frais dont l'état est ci-dessus à la somme de [montant] du montant de laquelle il délivre le présent exécutoire, pour le recouvrement de ladite somme être poursuivi sur les biens présents et à venir du condamné, par les percepteurs des Contributions directes.

En conséquence, LE PRÉSIDENT DE LA RÉPUBLIQUE MANDE ET ORDONNE a tous huissiers sur ce requis de mettre ledit jugement à
exécution; aux Procureurs généraux et aux Procureurs de la République près les tribunaux de première instance d'y tenir la
main; à tous commandants et officiers de la force publique de prêter main-forte lorsqu'ils en seront légalement requis.

Fait en la Chambre du Conseil de guerre susdit, à [lieu], le [date]

Le Président,
[Signature = +]""", 

    "=== Notes en marge ===": """Exemple : (1) Le gouverneur civil ou militaire. - Le général commandant le corps d'armée (France). Le général commandant la division militaire, la division ou
la brigade d'occupation, etc... - ou le ministre de la guerre, selon les cas prévus par l'article 8 du Code de justice militaire.
(2) Si le huis clos a été ordonné, le dire en visant l'article 113 du Code de justice militaire; il ne peut être ordonné que pour les débats, et tous les jugements
doivent être prononcés publiquement.
(3) Indiquer le crime ou le délit sur lequel l'accusé a été traduit devant de Conseil de guerre (art. 140).
(1) Et à décharge (s'il y en a).
(2) Indiquer si des témoins ont été entendus sans prestation de serment, et pour quel motif ; dire que les pièces de conviction, s'il y en a, ont été représentées.
Indiquer, en outre, ses incidents qui ont pu ce produire, en ayant soin de préciser à quel moment du débat ils ont en lieu, ses conclusions des parties, les
réquisitions du ministère public, les moyens de deiense présentés par l'accusé, et enfin le jugement motivé du Conseil. Dans le cas où le blanc laisse ici ne suf
firait pas pour insérer toutes ces mentions, on devra indiquer l'incident et le moment du débat il s'est produit, en ajoutant qu'il y a été statué par jugement
séparé, lequel est joint et annexé au présent, et alors le jugement séparé doit indiquer la publicité de l'audience, se terminer par la même formule et être signé
de la même manière que le jugement principal, en mentionnant qu'il y sera annexé comme en taisant partie. En cas de suspension d'audience et de remise au
lendemain, la mention qui constate cette remise est signée par le Président et le Greffier seulement.
(3) Indiquer si les réquisitions tendent à la déclaration de culpabilité et, dans ce cas, les articles de loi dont l'application est demandée.
(4) S'il y a une chambre des délibérations, on mettra que le Tribunal s'est retiré dans la chambre des délibérations.
(1) Avoir soin de spécifier, s'il y a lieu, après l'indication de la peine infligée, la décision motivée du Conseil relative à la non-imputation pour tout ou
partie de la détention préventive sur la durée de la peine prononcée.
(1) En France, en Algérie et en Tunisie.
(2) Aux colonies et aux armées."""
}

def envoyer_bloc_chat(bloc, history):
    messages = [{
        "role": "system",
        "content": (
            "Tu es un correcteur silencieux. Corrige uniquement les fautes de transcription (fautes d’orthographe, coquilles, mots mal lus ou déformés), sans jamais ajouter de commentaire, d’explication, ni de remarque. "
            "Préserve absolument la formulation originale, y compris les tournures anciennes et la syntaxe. "
            "Rends uniquement le texte corrigé, sans balise, sans titre, sans entête, sans mention de correction. "
            "Le texte est issu d’une minute de jugement de la Première Guerre mondiale."
        )
    }]
    messages += history[-HISTORY_MAX:]
    messages.append({"role": "user", "content": f"Texte à corriger :\n{bloc.strip()}"})

    for tentative in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            }, timeout=60)

            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
        except Exception as e:
            print(f"❌ Erreur pendant la requête (tentative {tentative+1}/{MAX_RETRIES}) : {e}")
            time.sleep(1)

    print("⛔ Abandon de ce bloc après échecs répétés.")
    return bloc

def decouper_en_sections(texte, keywords):
    pattern = r"(?=(" + "|".join(re.escape(k) for k in keywords) + r"))"
    indices = [m.start() for m in re.finditer(pattern, texte)]
    if not indices:
        return [("Texte complet", texte)]

    sections = []
    for i, start in enumerate(indices):
        end = indices[i+1] if i+1 < len(indices) else len(texte)
        section = texte[start:end].strip()
        for kw in keywords:
            if section.startswith(kw):
                sections.append((kw, section))
                break
    return sections

def corriger_fichier_texte(chemin_txt):
    with open(chemin_txt, "r", encoding="utf-8") as f:
        raw_text = f.read()

    sections = decouper_en_sections(raw_text, SECTION_KEYWORDS)
    history = []
    sections_corrigees = []

    for i, (titre_section, contenu_section) in enumerate(sections):
        print(f"🔁 {os.path.basename(chemin_txt)} - Section '{titre_section}' ({i+1}/{len(sections)})")
        
        # Découpe automatique si bloc trop long
        if len(contenu_section) > MAX_TAILLE_BLOC:
            sous_blocs = [contenu_section[i:i+MAX_TAILLE_BLOC] for i in range(0, len(contenu_section), MAX_TAILLE_BLOC)]
            corrections = []
            for sous_bloc in sous_blocs:
                correction = envoyer_bloc_chat(sous_bloc, history)
                history.append({"role": "user", "content": f"Texte à corriger :\n{sous_bloc.strip()}"})
                history.append({"role": "assistant", "content": correction})
                corrections.append(correction)
            section_corrigee = "\n".join(corrections)
        else:
            correction = envoyer_bloc_chat(contenu_section, history)
            history.append({"role": "user", "content": f"Texte à corriger :\n{contenu_section.strip()}"})
            history.append({"role": "assistant", "content": correction})
            section_corrigee = correction

        sections_corrigees.append(section_corrigee)

    chemin_sortie = chemin_txt.replace(".txt", "_corrige.txt")
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write("\n\n".join(sections_corrigees))

    print(f"✅ Fichier corrigé : {chemin_sortie}\n")

def traiter_dossier_racine(dataset_root):
    for dossier in sorted(os.listdir(dataset_root)):
        dossier_complet = os.path.join(dataset_root, dossier)
        if os.path.isdir(dossier_complet):
            fichiers_txt = [f for f in os.listdir(dossier_complet) if f.endswith(".txt") and not f.endswith("_corrige.txt")]
            for fichier in fichiers_txt:
                chemin_txt = os.path.join(dossier_complet, fichier)
                corriger_fichier_texte(chemin_txt)

if __name__ == "__main__":
    dossier_racine = "../transcriptions"
    traiter_dossier_racine(dossier_racine)
