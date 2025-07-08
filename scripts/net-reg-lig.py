from lxml import etree
from pathlib import Path
import glob

def nettoyer_et_renommer_alto(fichier_xml):
    fichier_xml = Path(fichier_xml)

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(str(fichier_xml), parser)
    root = tree.getroot()

    NS = {'alto': 'http://www.loc.gov/standards/alto/ns-v4#'}

    # Étape 1 : Nettoyer les lignes vides
    lignes_supprimees = 0
    for textline in root.xpath(".//alto:TextLine", namespaces=NS):
        strings = textline.findall(".//alto:String", namespaces=NS)
        strings_non_vides = [
            s for s in strings
            if s.get("CONTENT") and s.get("CONTENT").strip() != ""
        ]
        if len(strings_non_vides) == 0:
            textline.getparent().remove(textline)
            lignes_supprimees += 1

    # Étape 2 : Supprimer les TextBlock sans TextLine
    blocs_supprimes = 0
    for textblock in root.xpath(".//alto:TextBlock", namespaces=NS):
        if len(textblock.findall(".//alto:TextLine", namespaces=NS)) == 0:
            textblock.getparent().remove(textblock)
            blocs_supprimes += 1

    # Étape 3 : Renommer les IDs des blocs et des lignes
    textblocks = root.xpath('.//alto:TextBlock', namespaces=NS)
    for i, tb in enumerate(textblocks, start=1):
        tb.set("ID", f"r_{i:02d}")

    textlines = root.xpath('.//alto:TextLine', namespaces=NS)
    for j, tl in enumerate(textlines, start=1):
        tl.set("ID", f"l_{j:03d}")

    # Écraser le fichier d’origine
    tree.write(
        str(fichier_xml),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False
    )

    print(f"✅ Fichier traité : {fichier_xml.name}")
    print(f"   → {lignes_supprimees} lignes supprimées")
    print(f"   → {blocs_supprimes} blocs supprimés")

# Traiter tous les fichiers .xml du dossier (récursivement si besoin)
for fichier in glob.glob("../dataset/export/**/*.xml", recursive=True):
    nettoyer_et_renommer_alto(fichier)

