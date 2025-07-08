import os
import xml.etree.ElementTree as ET

# Le namespace ALTO par défaut
NAMESPACE = "http://www.loc.gov/standards/alto/ns-v4#"

# Enregistre le namespace sans préfixe (le namespace par défaut)
ET.register_namespace('', NAMESPACE)

# Chemin vers le dossier contenant les fichiers ALTO
dataset_path = os.path.join("..", "dataset")

for filename in os.listdir(dataset_path):
    if filename.endswith(".ocr.xml"):
        full_path = os.path.join(dataset_path, filename)
        print(f"Processing {full_path}")
        
        tree = ET.parse(full_path)
        root = tree.getroot()

        count = 0

        for line in root.findall(".//{{{}}}TextLine".format(NAMESPACE)):
            if line.get("LABEL") == "CustomLine:signature":
                for string in line.findall(".//{{{}}}String".format(NAMESPACE)):
                    string.set("CONTENT", "+")
                count += 1

        tree.write(full_path, encoding="UTF-8", xml_declaration=True)
        print(f"→ {count} ligne(s) modifiée(s)\n")
