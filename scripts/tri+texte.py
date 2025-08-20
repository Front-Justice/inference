import os
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict

# Namespace ALTO
NS = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
ET.register_namespace('', NS['alto'])

dataset_path = "../dataset/export"
output_path = "../transcriptions"

os.makedirs(output_path, exist_ok=True)

files = sorted([f for f in os.listdir(dataset_path) if f.endswith(".xml")])

current_min_id = None
min_counter = 1
min_dir = None
zone_texts = defaultdict(list)

# Ordre d’apparition des zones dans le texte final
zone_order = [
    "RunningTitleZone",
    "MainZone-judgementNumber",
    "MainZone-orderNumber",
    "MainZone-crimeDate",
    "MainZone-judgementPlace",
    "MarginTextZone-addition",
    "MainZone",
    # "MarginTextZone-note" est traité à part à la fin
]

# Mots-clés pour insérer des sauts de ligne avant certaines phrases
keywords = [
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

def add_spacing(lines, keywords):
    """Ajoute une ligne vide avant chaque ligne contenant un des mots-clés."""
    result = []
    for line in lines:
        if any(kw in line for kw in keywords):
            result.append("")  # Ajoute une ligne vide avant
        result.append(line)
    return result

def write_minute_file(path, zone_texts, zone_order, keywords):
    """Écrit un fichier .txt structuré selon les zones et ajoute des sauts de ligne contextuels."""
    with open(path, "w", encoding="utf-8") as out_txt:
        for zone in zone_order:
            if zone_texts[zone]:
                lines = add_spacing(zone_texts[zone], keywords)
                out_txt.write("\n".join(lines))
                out_txt.write("\n\n")
        if zone_texts["MarginTextZone-note"]:
            out_txt.write("=== Notes en marge ===\n")
            out_txt.write("\n".join(zone_texts["MarginTextZone-note"]))

# Parcours des fichiers
for f in files:
    full_path = os.path.join(dataset_path, f)
    tree = ET.parse(full_path)
    root = tree.getroot()

    # Récupération des balises OtherTag de type "region"
    region_map = {}
    for tag in root.findall(".//alto:OtherTag", NS):
        id_ = tag.attrib.get("ID")
        label = tag.attrib.get("LABEL")
        if id_ and label:
            region_map[id_] = label


    # Vérifie si le fichier contient une RunningTitleZone → nouveau document
    has_running_title = False
    for block in root.findall(".//alto:TextBlock", NS):
        tagref = block.attrib.get("TAGREFS")
        if tagref and region_map.get(tagref) == "RunningTitleZone":
            has_running_title = True
            break

    # Si début d’un nouveau document, enregistrer le précédent
    if has_running_title or current_min_id is None:
        if current_min_id and any(zone_texts.values()):
            txt_path = os.path.join(min_dir, f"{current_min_id}.txt")
            write_minute_file(txt_path, zone_texts, zone_order, keywords)
            zone_texts.clear()

        # Crée le nouveau dossier pour le document courant
        current_min_id = f"min_{min_counter:03d}"
        min_counter += 1
        min_dir = os.path.join(output_path, current_min_id)
        os.makedirs(min_dir, exist_ok=True)
        zone_texts.clear()
        print(f"📄 Nouveau document : {current_min_id}")

    # Copie du fichier XML source dans le dossier correspondant
    shutil.copy2(full_path, os.path.join(min_dir, f))

    # Récupération du texte ligne par ligne, classé par zone
    for block in root.findall(".//alto:TextBlock", NS):
        tagref = block.attrib.get("TAGREFS")
        zone_type = region_map.get(tagref, "unknown")

        for line in block.findall("alto:TextLine", NS):
            line_tagref = line.attrib.get("TAGREFS")
            # ⚠️ Si la ligne est marquée comme "scratched", on l’ignore
            if line_tagref and region_map.get(line_tagref) == "CustomLine:scratched":
                continue  

            strings = line.findall("alto:String", NS)
            contents = [s.attrib.get("CONTENT", "") for s in strings]
            line_text = " ".join(contents).strip()
            if line_text:
                zone_texts[zone_type].append(line_text)

# Traitement du dernier document
if current_min_id and any(zone_texts.values()):
    txt_path = os.path.join(min_dir, f"{current_min_id}.txt")
    write_minute_file(txt_path, zone_texts, zone_order, keywords)
    print(f"✅ Dernier document écrit : {current_min_id}")

# Vérification du nombre de fichiers XML par dossier
print("\n🔎 Vérification des dossiers...")
for min_folder in sorted(os.listdir(output_path)):
    folder_path = os.path.join(output_path, min_folder)
    if os.path.isdir(folder_path):
        xml_files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
        if len(xml_files) > 4:
            print(f"⚠️ Le dossier '{min_folder}' contient {len(xml_files)} fichiers XML")
