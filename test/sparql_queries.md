# Requêtes SPARQL pour le Tolkien Knowledge Graph

Ces requêtes sont conçues pour tester le KG dans Apache Fuseki.
Endpoint SPARQL : `http://localhost:3030/tolkien/sparql`

---

## 1. REQUÊTES BASIQUES

### 1.1 Compter le nombre total de triplets
```sparql
SELECT (COUNT(*) AS ?total)
WHERE {
  ?s ?p ?o .
}
```

### 1.2 Lister tous les types d'entités (classes)
```sparql
SELECT ?type (COUNT(?s) AS ?count)
WHERE {
  ?s a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
LIMIT 20
```

### 1.3 Lister tous les prédicats utilisés
```sparql
SELECT ?predicate (COUNT(*) AS ?count)
WHERE {
  ?s ?predicate ?o .
}
GROUP BY ?predicate
ORDER BY DESC(?count)
LIMIT 30
```

---

## 2. REQUÊTES SUR LES PERSONNAGES

### 2.1 Lister tous les personnages
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?character ?name
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 50
```

### 2.2 Personnages avec leur race/peuple
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?people
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  ?character tolkien_prop:people ?peopleUri .
  BIND(REPLACE(STR(?peopleUri), "https://tolkiengateway.net/wiki/", "") AS ?people)
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?people ?name
LIMIT 100
```

### 2.3 Compter les personnages par race
```sparql
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>

SELECT ?race (COUNT(?character) AS ?count)
WHERE {
  ?character a tolkien_class:Character .
  ?character tolkien_prop:people ?raceUri .
  BIND(REPLACE(STR(?raceUri), "https://tolkiengateway.net/wiki/", "") AS ?race)
}
GROUP BY ?race
ORDER BY DESC(?count)
```

### 2.4 Personnages avec dates de naissance et mort
```sparql
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?birth ?death
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  OPTIONAL { ?character tolkien_prop:birth ?birth }
  OPTIONAL { ?character tolkien_prop:death ?death }
  FILTER(lang(?name) = "en" || lang(?name) = "")
  FILTER(BOUND(?birth) || BOUND(?death))
}
ORDER BY ?name
LIMIT 50
```

### 2.5 Personnages avec leur conjoint (spouse)
```sparql
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?spouse
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  ?character tolkien_prop:spouse ?spouseUri .
  BIND(REPLACE(STR(?spouseUri), "https://tolkiengateway.net/wiki/", "") AS ?spouse)
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
```

---

## 3. REQUÊTES SUR LES LIEUX

### 3.1 Lister tous les lieux
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?place ?name
WHERE {
  ?place a tolkien_class:Location .
  ?place rdfs:label ?name .
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 50
```

### 3.2 Lister tous les royaumes
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?kingdom ?name
WHERE {
  ?kingdom a tolkien_class:Kingdom .
  ?kingdom rdfs:label ?name .
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
```

### 3.3 Lieux avec leur région/emplacement
```sparql
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?location
WHERE {
  ?place a tolkien_class:Location .
  ?place rdfs:label ?name .
  ?place tolkien_prop:location ?locUri .
  BIND(REPLACE(STR(?locUri), "https://tolkiengateway.net/wiki/", "") AS ?location)
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 50
```

---

## 4. REQUÊTES MULTILINGUES (Étape 11)

### 4.1 Entités avec labels en plusieurs langues
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?lang ?label
WHERE {
  ?entity rdfs:label ?label .
  BIND(lang(?label) AS ?lang)
  FILTER(?lang != "" && ?lang != "en")
}
ORDER BY ?entity ?lang
LIMIT 100
```

### 4.2 Compter les labels par langue
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?lang (COUNT(?label) AS ?count)
WHERE {
  ?entity rdfs:label ?label .
  BIND(lang(?label) AS ?lang)
}
GROUP BY ?lang
ORDER BY DESC(?count)
```

### 4.3 Trouver les traductions d'un personnage (ex: Gandalf)
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?lang ?label
WHERE {
  ?entity rdfs:label "Gandalf"@en .
  ?entity rdfs:label ?label .
  BIND(lang(?label) AS ?lang)
}
ORDER BY ?lang
```

### 4.4 Entités avec le plus de traductions
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity (COUNT(DISTINCT ?lang) AS ?numLangs) (GROUP_CONCAT(DISTINCT ?lang; separator=", ") AS ?languages)
WHERE {
  ?entity rdfs:label ?label .
  BIND(lang(?label) AS ?lang)
  FILTER(?lang != "")
}
GROUP BY ?entity
HAVING (COUNT(DISTINCT ?lang) > 3)
ORDER BY DESC(?numLangs)
LIMIT 20
```

---

## 5. REQUÊTES SUR LES ALIGNEMENTS EXTERNES (Étape 12)

### 5.1 Lister tous les alignements owl:sameAs
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?name ?externalUri
WHERE {
  ?entity owl:sameAs ?externalUri .
  OPTIONAL { 
    ?entity rdfs:label ?name .
    FILTER(lang(?name) = "en" || lang(?name) = "")
  }
}
ORDER BY ?name
```

### 5.2 Alignements DBpedia uniquement
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?name ?dbpediaUri
WHERE {
  ?entity owl:sameAs ?dbpediaUri .
  FILTER(CONTAINS(STR(?dbpediaUri), "dbpedia.org"))
  OPTIONAL { 
    ?entity rdfs:label ?name .
    FILTER(lang(?name) = "en" || lang(?name) = "")
  }
}
ORDER BY ?name
```

### 5.3 Alignements Wikidata uniquement
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?entity ?name ?wikidataUri
WHERE {
  ?entity owl:sameAs ?wikidataUri .
  FILTER(CONTAINS(STR(?wikidataUri), "wikidata.org"))
  OPTIONAL { 
    ?entity rdfs:label ?name .
    FILTER(lang(?name) = "en" || lang(?name) = "")
  }
}
ORDER BY ?name
```

### 5.4 Compter les alignements par source externe
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?source (COUNT(*) AS ?count)
WHERE {
  ?entity owl:sameAs ?externalUri .
  BIND(
    IF(CONTAINS(STR(?externalUri), "dbpedia"), "DBpedia",
    IF(CONTAINS(STR(?externalUri), "wikidata"), "Wikidata",
    IF(CONTAINS(STR(?externalUri), "yago"), "YAGO", "Other")))
    AS ?source
  )
}
GROUP BY ?source
ORDER BY DESC(?count)
```

---

## 6. REQUÊTES SUR LES CARTES MECCG

### 6.1 Compter les cartes par type
```sparql
PREFIX meccg: <https://meccg.net/card/>
PREFIX meccg_prop: <https://meccg.net/property/>

SELECT ?cardType (COUNT(?card) AS ?count)
WHERE {
  ?card meccg_prop:cardType ?cardType .
}
GROUP BY ?cardType
ORDER BY DESC(?count)
```

### 6.2 Lister les cartes de personnages
```sparql
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?card ?name ?race
WHERE {
  ?card meccg_prop:cardType "Character" .
  ?card rdfs:label ?name .
  OPTIONAL { ?card meccg_prop:race ?race }
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 50
```

### 6.3 Cartes liées à des entités du wiki
```sparql
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?card ?cardName ?wikiEntity
WHERE {
  ?card meccg_prop:depicts ?wikiEntity .
  ?card rdfs:label ?cardName .
  FILTER(lang(?cardName) = "en" || lang(?cardName) = "")
}
ORDER BY ?cardName
LIMIT 50
```

### 6.4 Cartes par set/extension
```sparql
PREFIX meccg_prop: <https://meccg.net/property/>

SELECT ?set (COUNT(?card) AS ?count)
WHERE {
  ?card meccg_prop:set ?set .
}
GROUP BY ?set
ORDER BY DESC(?count)
```

### 6.5 Sites (lieux) dans MECCG
```sparql
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX meccg_class: <https://meccg.net/class/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?site ?name ?region
WHERE {
  ?site a meccg_class:Site .
  ?site rdfs:label ?name .
  OPTIONAL { ?site meccg_prop:region ?region }
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
LIMIT 50
```

---

## 7. REQUÊTES AVANCÉES

### 7.1 Personnages avec le plus de propriétés
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name (COUNT(?p) AS ?numProperties)
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  ?character ?p ?o .
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
GROUP BY ?character ?name
ORDER BY DESC(?numProperties)
LIMIT 20
```

### 7.2 Recherche textuelle (personnages contenant "Bag")
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?character ?name
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  FILTER(CONTAINS(LCASE(STR(?name)), "bag"))
}
ORDER BY ?name
```

### 7.3 Entités communes entre Wiki et MECCG
```sparql
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?wikiEntity ?wikiName ?card ?cardName
WHERE {
  ?card meccg_prop:depicts ?wikiEntity .
  ?wikiEntity a tolkien_class:Character .
  ?wikiEntity rdfs:label ?wikiName .
  ?card rdfs:label ?cardName .
  FILTER(lang(?wikiName) = "en" || lang(?wikiName) = "")
  FILTER(lang(?cardName) = "en" || lang(?cardName) = "")
}
ORDER BY ?wikiName
LIMIT 30
```

### 7.4 Statistiques complètes du KG
```sparql
SELECT 
  (COUNT(DISTINCT ?s) AS ?subjects)
  (COUNT(DISTINCT ?p) AS ?predicates)
  (COUNT(DISTINCT ?o) AS ?objects)
  (COUNT(*) AS ?triples)
WHERE {
  ?s ?p ?o .
}
```

### 7.5 Tous les Hobbits avec leurs informations
```sparql
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name ?birth ?death ?spouse
WHERE {
  ?character a tolkien_class:Character .
  ?character tolkien_prop:people tolkien:Hobbits .
  ?character rdfs:label ?name .
  OPTIONAL { ?character tolkien_prop:birth ?birth }
  OPTIONAL { ?character tolkien_prop:death ?death }
  OPTIONAL { ?character tolkien_prop:spouse ?spouseUri }
  BIND(REPLACE(STR(?spouseUri), "https://tolkiengateway.net/wiki/", "") AS ?spouse)
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
ORDER BY ?name
```

---

## 8. REQUÊTES CONSTRUCT (création de graphes)

### 8.1 Extraire un sous-graphe pour un personnage
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

CONSTRUCT {
  ?s ?p ?o .
}
WHERE {
  BIND(tolkien:Gandalf AS ?s)
  ?s ?p ?o .
}
```

### 8.2 Créer un graphe simplifié des personnages
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>

CONSTRUCT {
  ?character foaf:name ?name .
  ?character foaf:member ?people .
}
WHERE {
  ?character a tolkien_class:Character .
  ?character rdfs:label ?name .
  OPTIONAL { ?character tolkien_prop:people ?people }
  FILTER(lang(?name) = "en" || lang(?name) = "")
}
```

---

## 9. REQUÊTES ASK (vérification)

### 9.1 Vérifier si Gandalf existe
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>

ASK {
  tolkien:Gandalf ?p ?o .
}
```

### 9.2 Vérifier s'il y a des alignements DBpedia
```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>

ASK {
  ?s owl:sameAs ?o .
  FILTER(CONTAINS(STR(?o), "dbpedia"))
}
```

### 9.3 Vérifier s'il y a des labels en français
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

ASK {
  ?s rdfs:label ?label .
  FILTER(lang(?label) = "fr")
}
```

---

## 10. REQUÊTES DESCRIBE

### 10.1 Décrire une entité spécifique
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>

DESCRIBE tolkien:Gandalf
```

### 10.2 Décrire les 5 premiers personnages
```sparql
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>

DESCRIBE ?character
WHERE {
  ?character a tolkien_class:Character .
}
LIMIT 5
```

---

## Notes d'utilisation

1. **Dans Fuseki** : Allez sur `http://localhost:3030/#/dataset/tolkien/query`
2. **Copiez-collez** une requête et cliquez sur le bouton "Play" (▶)
3. **Modifiez** les requêtes selon vos besoins (LIMIT, FILTER, etc.)

### Préfixes utiles à retenir :
```sparql
PREFIX tolkien: <https://tolkiengateway.net/wiki/>
PREFIX tolkien_prop: <https://tolkiengateway.net/wiki/Property:>
PREFIX tolkien_class: <https://tolkiengateway.net/wiki/Class:>
PREFIX meccg: <https://meccg.net/card/>
PREFIX meccg_prop: <https://meccg.net/property/>
PREFIX meccg_class: <https://meccg.net/class/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX schema: <http://schema.org/>
```
