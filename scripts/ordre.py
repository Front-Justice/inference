import os
import xml.etree.ElementTree as ET

# Ordre de lecture souhaité
zone_order = [
    "RunningTitleZone",
    "MainZone-judgementNumber",
    "MainZone-orderNumber",
    "MainZone-crimeDate",
    "MainZone-judgementPlace",
    "MarginTextZone-addition",
    "MainZone",
    "MarginTextZone-note",
    "QuireMarksZone-signature"
]

# Namespace ALTO
NS = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}
ET.register_namespace('', NS['alto'])

dataset_path = "../dataset/export"  # À adapter si besoin

for filename in os.listdir(dataset_path):
    if filename.endswith(".xml"):
        full_path = os.path.join(dataset_path, filename)
        print(f"Traitement de {filename}")

        try:
            tree = ET.parse(full_path)
            root = tree.getroot()

            # Récupération des types de zones via Tags (corrigé ici)
            region_type_map = {}
            for tag in root.findall(".//alto:OtherTag", NS):
                region_type_map[tag.attrib["ID"]] = tag.attrib["LABEL"]

            # Vérification que RunningTitleZone est présent dans les LABELs
            if "RunningTitleZone" not in region_type_map.values():
                print(f"⚠️  {filename} ignoré (pas de RunningTitleZone)")
                continue

            # Accès à tous les <TextBlock> dans leur parent <PrintSpace>
            for page in root.findall(".//alto:PrintSpace", NS):
                blocks = page.findall("alto:TextBlock", NS)

                # Regrouper par zone label
                grouped_blocks = {label: [] for label in zone_order}
                other_blocks = []

                for block in blocks:
                    tagref = block.attrib.get("TAGREFS")
                    if tagref:
                        label = region_type_map.get(tagref)
                        if label in grouped_blocks:
                            grouped_blocks[label].append(block)
                        else:
                            other_blocks.append(block)
                    else:
                        other_blocks.append(block)

                # Supprimer les anciens blocs
                for block in blocks:
                    page.remove(block)

                # Réinsérer dans le bon ordre
                for label in zone_order:
                    for block in grouped_blocks[label]:
                        page.append(block)

                # Réinsérer les blocs non classés à la fin
                for block in other_blocks:
                    page.append(block)

            # Écriture du fichier réordonné
            tree.write(full_path, encoding="UTF-8", xml_declaration=True)
            print(f"✅ Réordonné : {filename}\n")

        except Exception as e:
            print(f"❌ Erreur avec {filename} : {e}")
