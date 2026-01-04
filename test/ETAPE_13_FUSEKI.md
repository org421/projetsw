# Étape 13 : Charger le KG dans Apache Fuseki

## 1. Installation de Fuseki

### Option A : Téléchargement direct (recommandé)

```bash
# 1. Télécharger Fuseki (version 4.10.0 ou plus récente)
wget https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-4.10.0.zip

# 2. Extraire
unzip apache-jena-fuseki-4.10.0.zip
cd apache-jena-fuseki-4.10.0

# 3. Lancer le serveur
./fuseki-server --update --mem /tolkien
```

### Option B : Avec Docker

```bash
# Lancer Fuseki avec Docker
docker run -d --name fuseki \
  -p 3030:3030 \
  -e ADMIN_PASSWORD=admin123 \
  secoresearch/fuseki

# Ou avec persistence des données
docker run -d --name fuseki \
  -p 3030:3030 \
  -v $(pwd)/fuseki-data:/fuseki \
  -e ADMIN_PASSWORD=admin123 \
  secoresearch/fuseki
```

### Option C : Sur Windows (sans Docker)

1. Téléchargez : https://jena.apache.org/download/
2. Extrayez le ZIP
3. Ouvrez un terminal dans le dossier extrait
4. Exécutez :
```cmd
fuseki-server.bat --update --mem /tolkien
```

---

## 2. Accéder à l'interface Fuseki

1. Ouvrez votre navigateur
2. Allez sur : **http://localhost:3030**
3. Vous verrez l'interface d'administration Fuseki

---

## 3. Créer le dataset (si pas fait au lancement)

### Via l'interface web :

1. Cliquez sur **"manage datasets"**
2. Cliquez sur **"add new dataset"**
3. Configurez :
   - **Dataset name** : `tolkien`
   - **Dataset type** : `Persistent (TDB2)` ou `In-memory`
4. Cliquez sur **"create dataset"**

### Via la ligne de commande :

```bash
# Dataset en mémoire (perdu au redémarrage)
./fuseki-server --update --mem /tolkien

# Dataset persistant (sauvegardé sur disque)
./fuseki-server --update --loc=./tolkien-data /tolkien
```

---

## 4. Charger le fichier RDF

### Méthode 1 : Via l'interface web (recommandé)

1. Allez sur **http://localhost:3030**
2. Cliquez sur votre dataset **"tolkien"**
3. Cliquez sur **"upload files"**
4. Sélectionnez **`tolkien_kg_complete.ttl`**
5. Cliquez sur **"upload"**
6. Attendez le message de confirmation

### Méthode 2 : Via curl (ligne de commande)

```bash
# Charger le fichier Turtle
curl -X POST \
  -H "Content-Type: text/turtle" \
  --data-binary @tolkien_kg_complete.ttl \
  http://localhost:3030/tolkien/data

# Ou avec le fichier N-Triples
curl -X POST \
  -H "Content-Type: application/n-triples" \
  --data-binary @tolkien_kg_complete.nt \
  http://localhost:3030/tolkien/data
```

### Méthode 3 : Via l'outil tdbloader (pour gros fichiers)

```bash
# Pour un dataset TDB2 persistant
./tdb2.tdbloader --loc=./tolkien-data tolkien_kg_complete.ttl
```

---

## 5. Vérifier le chargement

### Via l'interface web :

1. Allez sur **http://localhost:3030/#/dataset/tolkien/query**
2. Exécutez cette requête :

```sparql
SELECT (COUNT(*) AS ?total)
WHERE {
  ?s ?p ?o .
}
```

3. Vous devriez voir : **~46 308 triplets**

### Via curl :

```bash
curl -X POST \
  -H "Accept: application/json" \
  --data-urlencode "query=SELECT (COUNT(*) AS ?total) WHERE { ?s ?p ?o . }" \
  http://localhost:3030/tolkien/sparql
```

---

## 6. Tester des requêtes SPARQL

Allez sur **http://localhost:3030/#/dataset/tolkien/query** et testez :

### Requête 1 : Statistiques de base
```sparql
SELECT ?type (COUNT(?s) AS ?count)
WHERE {
  ?s a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
LIMIT 15
```

### Requête 2 : Liste des personnages
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 20
```

### Requête 3 : Labels multilingues
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?lang (COUNT(*) AS ?count)
WHERE {
  ?s rdfs:label ?label .
  BIND(lang(?label) AS ?lang)
}
GROUP BY ?lang
ORDER BY DESC(?count)
```

### Requête 4 : Alignements externes
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?source (COUNT(*) AS ?count)
WHERE {
  ?s owl:sameAs ?ext .
  BIND(
    IF(CONTAINS(STR(?ext), "dbpedia"), "DBpedia",
    IF(CONTAINS(STR(?ext), "wikidata"), "Wikidata",
    IF(CONTAINS(STR(?ext), "yago"), "YAGO", "Other")))
    AS ?source
  )
}
GROUP BY ?source
```

---

## 7. Endpoints SPARQL disponibles

Une fois Fuseki lancé, vous avez accès à :

| Endpoint | URL | Description |
|----------|-----|-------------|
| **Query** | http://localhost:3030/tolkien/sparql | Requêtes SELECT, ASK, CONSTRUCT |
| **Update** | http://localhost:3030/tolkien/update | Requêtes INSERT, DELETE |
| **Data** | http://localhost:3030/tolkien/data | Upload/Download de données |
| **Graph Store** | http://localhost:3030/tolkien/data?graph=default | Accès au graphe par défaut |

---

## 8. Configuration avancée (optionnel)

### Fichier de configuration Fuseki (`config.ttl`)

```turtle
@prefix :      <#> .
@prefix fuseki: <http://jena.apache.org/fuseki#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix tdb2:  <http://jena.apache.org/2016/tdb#> .
@prefix ja:    <http://jena.hpl.hp.com/2005/11/Assembler#> .

:service a fuseki:Service ;
    fuseki:name "tolkien" ;
    fuseki:endpoint [ 
        fuseki:operation fuseki:query ;
        fuseki:name "sparql"
    ] ;
    fuseki:endpoint [
        fuseki:operation fuseki:update ;
        fuseki:name "update"
    ] ;
    fuseki:endpoint [
        fuseki:operation fuseki:gsp-rw ;
        fuseki:name "data"
    ] ;
    fuseki:dataset :dataset .

:dataset a tdb2:DatasetTDB2 ;
    tdb2:location "./tolkien-data" .
```

Lancer avec config :
```bash
./fuseki-server --config=config.ttl
```

---

## 9. Résolution des problèmes

### Erreur : "Port 3030 already in use"
```bash
# Trouver le processus
lsof -i :3030
# ou sur Windows
netstat -ano | findstr 3030

# Tuer le processus ou utiliser un autre port
./fuseki-server --port=3031 --update --mem /tolkien
```

### Erreur : "Out of memory"
```bash
# Augmenter la mémoire Java
export JVM_ARGS="-Xmx4G"
./fuseki-server --update --mem /tolkien
```

### Erreur de parsing du fichier
```bash
# Valider le fichier Turtle
riot --validate tolkien_kg_complete.ttl
```

---

## 10. Résumé des commandes

```bash
# 1. Lancer Fuseki
./fuseki-server --update --mem /tolkien

# 2. Charger les données (dans un autre terminal)
curl -X POST \
  -H "Content-Type: text/turtle" \
  --data-binary @tolkien_kg_complete.ttl \
  http://localhost:3030/tolkien/data

# 3. Tester
curl -X POST \
  --data-urlencode "query=SELECT (COUNT(*) AS ?total) WHERE { ?s ?p ?o . }" \
  http://localhost:3030/tolkien/sparql

# 4. Interface web
# Ouvrir http://localhost:3030 dans le navigateur
```

---

## ✅ Checklist Étape 13

- [ ] Fuseki installé et lancé
- [ ] Dataset "tolkien" créé
- [ ] Fichier tolkien_kg_complete.ttl chargé
- [ ] ~46 308 triplets visibles
- [ ] Requêtes SPARQL fonctionnelles
- [ ] Interface web accessible sur http://localhost:3030

---

## 🚀 Prochaine étape

Une fois Fuseki configuré, passez à l'**Étape 14** :
- Créer une interface web Linked Data
- Exposer les données via une API REST
- Créer des pages HTML pour chaque entité
