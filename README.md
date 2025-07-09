# PROJET FRONT JUSTICE

Chaîne de traitement des minutes dans le cadre du projet **Front Justice**.

## 🔧 Prérequis

**Important** : toutes les opérations doivent être effectuées depuis l’environnement virtuel.

```bash
source env/bin/activate
```

1. Installation de YALTAi :

```bash
pip install YALTAi
```

📎 Lien : [https://github.com/ponteineptique/yaltai](https://github.com/ponteineptique/yaltai)

---

## ✍️ Reconnaissance automatique de l’écriture

Le traitement suit une chaîne bien définie :
- Détection des zones et des lignes via YALTAi et Kraken
- Reconnaissance des caractères avec un modèle entraîné (Kraken)
- Correction manuelle via eScriptorium (noms propres, date, numéro de jugement, armée)
- Post-traitement et extraction du contenu avec Ollama

---

### 📐 Analyse de la mise en page

1. Se placer dans `htr/dataset`
2. Placer les numérisations dans le dossier `dataset`
3. Lancer la détection d’objets et de lignes :

```bash
yaltai kraken --device cuda:0 -a -I "*.tif" --suffix ".xml" segment --yolo models/weights.pt -i models/250p-escript.mlmodel
```

📎 Résultat : fichiers ALTO `.xml`, générés depuis des images `.tif` avec support GPU.

---

### 🔡 Reconnaissance des caractères

Appliquer le modèle entraîné `250p_best.mlmodel` :

```bash
kraken -d cuda:0 -a -I "*.xml" -o ".ocr.xml" -f xml ocr -m models/250p_best.mlmodel
```

🗂 Résultats stockés dans des fichiers `*.ocr.xml`.

#### ➕ Traitement des signatures

Remplacer toute ligne marquée `LABEL="CustomLine:signature"` par un simple `+` :

```bash
cd htr/scripts
python3 signature.py
```

---

## 🔍 Vérifications manuelles essentielles

Sur la **première page de chaque minute**, vérifier :
- Les noms propres
- La date
- Le numéro de jugement
- Le nom de l’armée concernée

Ces éléments critiques ne doivent pas être laissés à la seule reconnaissance automatique.

📦 Pour faciliter l’import dans eScriptorium :

```bash
zip ocr.zip *.ocr.xml
```

Après correction dans eScriptorium, exporter les transcriptions au format `ALTO` dans `dataset/export`.

---

## 🧹 Post-traitement & structuration

### 🧭 Remise en ordre des lignes

Assurer l’ordre logique des lignes en première page :

```bash
python3 ordre.py
```

### 🆔 Nettoyage des ID et des régions

- Renommage cohérent des ID pour régions et lignes
- Suppression des zones/lignes vides

```bash
python3 net-reg-lig.py
```

### 📁 Structuration finale et extraction de texte

Organise chaque minute dans un dossier dédié et extrait le texte dans un fichier `min_*.txt` :

```bash
python3 tri+texte.py
```

Ces fichiers serviront à l’analyse NER.

---

## 🤖 Correction via Ollama

Appliquer le modèle LLM Phi-4 pour corriger automatiquement les transcriptions HTR, y compris les toponymes :

```bash
python3 post-oll.py
```

---

## ✅ Prochaines étapes

1. Amélioration de la qualité de l’HTR :
   - Monter à **1 000** sur Roboflow
   - Monter à **500** pour la segmentation (pour détecter les marges)
   - Entraîner un modèle `Party` pour la reconnaissance, à l’aide du dataset (⚠️ nécessite un GPU puissant)

