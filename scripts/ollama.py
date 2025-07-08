import os
import requests
import time
import re

OLLAMA_MODEL = "phi4"
API_URL = "http://localhost:11434/api/chat"
HISTORY_MAX = 11
MAX_RETRIES = 3
MAX_TAILLE_BLOC = 15000  # caractères

SECTION_KEYWORDS = [
    "RÉPUBLIQUE FRANÇAISE",
    "CEJOURD'HUI",
    "A l'effet de juger",
    "La séance ayant été ouverte",
    "Interrogé de",
    "Le Président, après avoir fait lire",
    "Ouï M. le Commissaire",
    "L'accusé a été reconduit",
    "Les voix recueillies séparément",
    "Sur quoi, et attendu les conclusions",
    "Enjoint au Commissaire du Gouvernement",
    "EXÉCUTOIRE"
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

    "CEJOURD'HUI": """CEJOURD'HUI [date]
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

    "A l'effet de juger": """A l'effet de juger le nommé [nom], [prénoms], fils de [père] et de [mère], né le [date] à [lieu], département de [département], profession de [profession], résidant, avant son entrée au service, à [lieu].

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


    "La séance ayant été ouverte" : """La séance ayant été ouverte, le Président a fait apporter et déposer devant lui, sur le bureau, un exemplaire du Code de justice militaire, du Code d'instruction criminelle et du Code pénal ordinaire, et ordonné à la garde d'amener l'accusé, qui a été introduit, libre et sans fers, devant le Conseil, accompagné de son défenseur M. [nom], [profession]""",

    "Interrogé de": """Interrogé de ses nom, prénoms, âge, lieu de naissance, état, profession et domicile, l'accusé a répondu se nommer :
[nom complet], [âge] ans, né à [lieu de naissance], département de [département],
[état civil : célibataire / marié / veuf], [nombre d’enfants éventuel],
profession de [profession], demeurant à [ville], département de [département].""",


    "Le Président, après avoir fait lire" : """Le Président, après avoir fait lire par le greffier l'ordre de convocation, le rapport prescrit par l'article 108 du Code de justice
militaire, et les pièces dont la lecture lui a paru nécessaire, a fait connaître a l'accusé les faits à raison desquels il est
poursuivi, et lui a donné, ainsi qu'au défenseur, l'avertissement indiqué en l'article 121 dudit Code;
Après quoi, il a procédé à l'interrogatoire de l'accusé et a fait entendre publiquement et séparément les témoins à charge (1)
; lesdits témoins ayant au préalable prêté serment de parler sans haine et sans crainte, juré de dire toute la
vérité et rien que la vérité;
Et le Président ayant, en outre, rempli à leur égard les formalités prescrites par les articles 317 et 319 du Code d'instruction
criminelle;
(2)""",

    "Ouï M. le Commissaire" : """Ouï M. le Commissaire du Gouvernement en ses réquisitions tendant à ce que (3) l'accusé soit déclaré coupable
des faits relevés contre lui dans l'ordre de mise en jugement et qu'il lui soit
fait application des article 242-267 du Code de Justice militaire; 849 de la
loi du 9 aout 1849 modifié par la loi du 27 Avril 1916 - 156, 164 du Code Pénal
et l'accusé dans ses moyens de défense, tant par lui-même que par son défenseur, lesquels ont
déclaré n'avoir rien à ajouter à leurs moyens de défense, et ont eu la parole les derniers, le Président a déclaré les débats terminés,
et il a ordonné au défenseur et a l'accusé de se retirer.""",

    "L'accusé a été reconduit" : """L'accusé a été reconduit par l'escorte à la prison; le Commissaire du Gouvernement, le Greffier et les assistants dans
l'auditoire se sont retirés sur l'invitation du Président (4);
Le Conseil délibérant à huis clos, le Président a posé les questions, conformément à l'article 132 du Code de justice
militaire, ainsi qu'il suit:
1^ere Question: Le nomme Lambelin Alphonse Jeanne Ferdinand imprimeur libraire demeurant
à Epernay est-il, coupable d'avoir le 27 Novembre 1917 à Epernay- Marne favorisé la désertion
à l'intérieur en temps de guerre du soldat de 2^e lasse Grégoire du 4^e régiment de Zouaves en
lui procurant une fausse permission?
2^e question: Est-il coupable d'avoir aux mêmes date et lieu fabrique
une fausse permission ayant tenu lieu de feuille de route audit soldat Grégoire?
Question:- Est-il, coupable d'avoir le 13 décembre 1917, audit lieu
favorisé la désertion à l'intérieur en temps de guerre du soldat de 2^e classe Brèbion
4^e Question - Est-il coupable d'avoir aux mêmes date et lieu fabriqué une fausse permission ayant tenu lieu
de feuille de route audit soldat Brebion?
5^e Question - Est il coupable d'avoir audit lieu, vers la fin de Décembre 1917 favorisé la désertion
à l'intérieur en temps de guerre du soldat de 2^e lasse Brébion du 4^e reg^t de zouaves
en lui procurant une fausse permission ?
6^e question - Est-il coupable d'avoir audit lieu, vers la fis du mois de décembre 1917
fabriqué une fausse permission ayant tenu lieu de feuille de route audit soldat Brébion?
7 Question - Est-il coupable d'avoir audit lieu le 18 Décembre 1917 favorisé la désertion
à l'intérieur en temps de guerre du soldat de 3^e classe Deschamps du 4^e régiment de
Zouaves, en lui procurant une fausse permission
8^o Question - Est-il coupable d'avoir audit lieu le 18 Décembre 1917 fabriqué une
fausse permission ayant tenu lieu de feuille de route audit soldat Deschamps?
Il a été voté au scrutin secret, conformément à l'article 191 du Code de Justice militaire sur chacune de ces questions ainsi que sur les
circonstances atténuantes, et sur l'application de la loi de sursis.""",

    "Les voix recueillies séparément" : """Les voix recueillies séparément, conformément à l'article 131 du Code de justice militaire, en commençant par le grade inférieur.
le Président ayant émis son opinion le dernier, le Conseil de guerre permanent déclare.
Le Président a dépouillé chaque scrutins en présence
des juges du Conseil de guerre: de ces dépouillements successifs il résulte que le Conseil de Guerre déclare:
Sur la 1^ere question à l'unanimité: non
Sur la 2^e Question à l'unanimité: oui
sur la 3^e question à l'unanimité: non
Sur la 4^e question à l'unanimité: oui
sur la 5e question à l'unanimité: non
sur la 6^e question à l'unanimité: oui
Sur la 7^e question, à l'unanimité: non
Sur la 8^e question à l'unanimité: oui""",

    "Sur quoi, et attendu les conclusions" : """Sur quoi, et attendu les conclusions prises par le Commissaire du Gouvernement dans ses réquisitions, le Président a lu le texte
de la loi,
recueilli de nouveau les voix dans la forme prescrite par les articles 131 et 134 du Code de justice militaire pour l'appli-
cation de la peine.
et le Conseil de guerre a délibéré sur l'application de le peine conformément à l'article 134 du Code de Justice militaire
Le Conseil est rentré en séance publique, le Président a lu les motifs qui précèdent et le dispositif ci-dessous.
Le Président a en
En conséquence, le Conseil (1)
conséquence recueilli les voix en commençant par le grade inférieur et émis son opinion le dernier
Le Conseil est rentré en séance publique, le Président a lu les motifs qui précèdent et les dispositifs ci dessous
En consequence le Conseil, condamne le 1^e Lambelin susqualifié
1^o  l'unanimité à la peine de six mois de prison
2^o a l'unanimité à la peine de trois mille, francs d'amende,
Et, attendu qu'il n'a subi antérieurement aucune condamnation, considérant que le
renseignements fournis sur lui, lui sont favorables, ordonne à l'unanimité, qu'il sera sursis
à l'exécution de la présente peine de prison
Le condamne en outre aux fais envers l'Etat, et a l'unanimité fixe la durée de la
contrainte par Corps, au minimum édicte par la loi, le tout par application des articles
139 du Code de Justice militaire, 156, 164 du Code Pénal; 849 de le loi du 9 Aout 1849 modifié
par la loi du 27 Avril 1916. 9 de la loi du 22 Juillet 1867, 1^er des lois du 28 Juin 1904. et 26
mars 1891.
Ceux des articles édictant le peine ont été lus publiquement par le
Président et sont ainsi conçus.
« Article 156 Code Pénal: Quiconque fabriquera une fausse feuille de route...
« sera puni savoir:...
« D'un emprisonnement de six mois au moins et de trois ans au plus si la
« fausse feuille de route n'a eu pour objet qui su tromper la surveillance
« de l'autorité publique.
« Article 164 Code Pénal: Il sera prononcé contre les coupables une amende dont
« le minimum sera de 100^l et le maximum de 9000^e.""",

    "Enjoint au Commissaire du Gouvernement" : """Enjoint au Commissaire du Gouvernement de faire donner immédiatement en sa présence lecture du présent jugement au
condamne devant la garde rassemblée sous les armes,
de avertir que la loi accorde un délai de trois jours francs pour se pourvoir en cassation (1), ou de vingt-quatre heures
pour se pourvoir en revision (2).
FAIT, clos et jugé sans désemparer, en séance publique, à Chalons sur Marne, les jour, mois et an que dessus.
En conséquence, LE PRÉSIDENT DE LA RÉPUBLIQUE MANDE et ORDONNE à tous huissiers sur ce requis de mettre ledit jugement à
exécution; aux Procureurs généraux et aux Procureurs de la République près les tribunaux de première instance d'y tenir la
main; à tous commandants et officiers de la force publique de prêter main-forte lorsqu'ils en seront légalement requis.
En foi de quoi le présent jugement a été signé par les Membres du Conseil et par le Greffier.
+
+
+
+
+
+
L'an mil neuf cent dix huit le deux Juillet le présent jugement a été lu par nous, Greffier soussigné, au condamné
averti par le Commissaire du Gouvernement que l'article 44 de la loi du 17 avril
1906 accorde trois jours pour se pourvoir en cassation (1), ou que les articles 141 et 143 du Code de justice militaire
accordent vingt-quatre heures pour se pourvoir en revision (2), lesquels commencent à courir de l'expiration du présent jour,
Cette
lecture faite en présence de la Garde rassemblée sous les armes. Le Commissaire Rapporteur a en outre averti au condamné Lambelin
l'avertissement prescrit par l'article 3 de la loi du 26 mars 1891.
Le Commissaire du Gouvernement,
+
Le Greffier,
+
Jugement définitif le deux Juillet 1918
détention préventive du onze mai au trois
Juillet 1918
+""",
    "EXÉCUTOIRE" : """EXÉCUTOIRE.
Vu la procédure instruite contre le M^e Lambelin
et les frais d'icelle dont le détail suit:
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
9^o Frais résultant de l'obtention des extraits du casier judiciaire......................................... 0.25
10^o Prix du bulletin n^o 1 et du duplicata dudit (décret du 12 décembre 1899, art. 13).....................
11^o Coût des bulletins n^o 1 et du duplicata de ces bulletins établis par les greffiers des conseils de guerre au sujet
des condamnations prononcées par ces conseils (décret du 12 décembre 1899, art. 13).................... 0.40
12^o Frais de procédure ou coût du jugement........................................................ 12^f 00
13^o Amende......................................................................................... 3000
14^o Décimes additionnels (en France)............................................................... 730
15^o Frais fixes de procédure devant la Cour de cassation ou le Conseil de revision...........................
16^o Frais fixes de procédure devant le Conseil de guerre jugeant en 2^e instance.............................
TOTAL.................................................. 3762^f 65
Vu le dispositif du jugement définitif, l'article 139 du Code de justice militaire, le Président du- Conseil de guerre
permanent
de la IV^e Armée liquide les frais dont l'état est ci-dessus à la somme de trois mille sept cent soixante
deux francs 65 centimes du montant de laquelle il délivre le présent exécutoire, pour le recouvrement de
ladite somme être poursuivi sur les biens présents et à venir du condamné, par les percepteurs des Contributions directes.
En conséquence, LE PRÉSIDENT DE LA RÉPUBLIQUE MANDE ET ORDONNE a tous huissiers sur ce requis de mettre ledit jugement à
exécution; aux Procureurs généraux et aux Procureurs de la République près les tribunaux de première instance d'y tenir la
main; à tous commandants et officiers de la force publique de prêter main-forte lorsqu'ils en seront légalement requis.
Fait en la Chambre du Conseil de guerre susdit, à Chalons Sur Marne, le deux Juillet 1915
Le Président,
+"""
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
