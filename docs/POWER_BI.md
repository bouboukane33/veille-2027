# Connecter CCR Veille 2027 à Power BI Desktop

## 1. Choisir une seule source de données

Pour tester, utiliser `data/exports/demo/`. Pour la veille réelle, utiliser `data/exports/live/`. Ne pas fusionner ces dossiers. Afficher le mode dans le titre du rapport ; le jeu démo porte `is_demo=1` et des titres fictifs.

Dans **Accueil → Obtenir des données → Texte/CSV**, sélectionner chaque fichier requis, choisir **UTF-8 (65001)** et le séparateur **virgule**, puis **Transformer les données**. Créer un paramètre `ExportFolder` pour déplacer facilement le rapport. Éviter une combinaison automatique de tous les CSV : leurs schémas diffèrent.

Exemple de requête Power Query pour une table :

```powerquery
let
    Source = Csv.Document(
        File.Contents(ExportFolder & "\daily_metrics.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"date", type date},
        {"personality_id", type text},
        {"news_count", Int64.Type},
        {"youtube_video_count", Int64.Type},
        {"youtube_views", Int64.Type},
        {"visibility_score", type number},
        {"ccr_relevance_score", type number},
        {"visibility_change_7d", type number},
        {"is_demo", Int64.Type}
    }, "en-US")
in
    Types
```

Les décimales utilisent le point : interpréter les nombres avec une locale appropriée (par exemple `en-US`) même dans Power BI français. Conserver les identifiants comme texte ; les timestamps `published_at` et `collected_at` sont des dates/heures avec fuseau UTC, `date` est une date civile. Les compteurs vides signifient « inconnu », pas forcément zéro.

## 2. Construire les relations

| Dimension, côté 1 | Table, côté plusieurs | Colonne |
| --- | --- | --- |
| `personalities` | `daily_metrics` | `personality_id` |
| `personalities` | `personality_brief` | `personality_id` |
| `personalities` | `latest_activity` | `personality_id` |
| `personalities` | `content_personalities` | `personality_id` |
| `content` | `content_personalities` | `content_key` |
| `content` | `content_topics` | `content_key` |
| `topics` | `content_topics` | `topic` |

`personality_brief` possède une ligne par personnalité : une relation 1:1 est possible. Les autres relations sont 1:N, à filtrage simple depuis la dimension. Ne pas relier les tables d'articles et vidéos à `personalities` par leur premier `personality_id` pour analyser toutes les mentions. Ne pas importer simultanément `personality_dashboard` et `daily_metrics` comme deux faits agrégés : la vue est une alternative pratique, pas un volume supplémentaire.

Ajouter une dimension calendrier avec une date unique par jour, reliée à `daily_metrics.date` et `content.date`. Pour une analyse personnalité × thème, utiliser une mesure de transfert des identifiants (ci-dessous), plutôt qu'un filtrage bidirectionnel généralisé susceptible de créer des chemins ambigus. `latest_activity` est déjà une table de mentions prête à afficher ; elle est limitée aux 200 dernières lignes par défaut, donc ne convient pas aux KPI exhaustifs.

## 3. Mesures DAX de départ

Ces mesures supposent les noms de tables ci-dessus. Selon les paramètres régionaux, adapter les séparateurs DAX. Filtrer les dimensions au statut `suivi` et choisir une date de référence pour les scores.

```dax
Personnalités suivies =
CALCULATE(DISTINCTCOUNT(personalities[personality_id]), personalities[status] = "suivi")

Articles analysés =
CALCULATE(DISTINCTCOUNT(content[content_key]), content[content_type] = "news")

Vidéos analysées =
CALCULATE(DISTINCTCOUNT(content[content_key]), content[content_type] = "youtube")

Contenus CCR = DISTINCTCOUNT(content_topics[content_key])

Visibilité = AVERAGE(daily_metrics[visibility_score])

Pertinence CCR = AVERAGE(daily_metrics[ccr_relevance_score])

Contenus par personnalité et thème =
VAR PersonKeys = VALUES(content_personalities[content_key])
RETURN
CALCULATE(
    DISTINCTCOUNT(content_topics[content_key]),
    KEEPFILTERS(TREATAS(PersonKeys, content_topics[content_key]))
)

Contenus mentionnant la personnalité =
VAR PersonKeys = VALUES(content_personalities[content_key])
RETURN
CALCULATE(
    DISTINCTCOUNT(content[content_key]),
    KEEPFILTERS(TREATAS(PersonKeys, content[content_key]))
)
```

Pour les KPI `Articles analysés` et `Vidéos analysées`, ces versions comptent le corpus filtré par date, indépendamment du sélecteur de personnalité. Pour les rendre sensibles à ce sélecteur, ajouter aussi `TREATAS(VALUES(content_personalities[content_key]), content[content_key])`, comme dans la dernière mesure. Le nombre de contenus uniques n'est pas la somme des mentions des personnalités.

Les scores se visualisent comme des valeurs ou moyennes, **jamais comme des sommes** entre jours ou personnalités. Pour le classement du jour, filtrer `daily_metrics.date` sur la date de référence la plus récente du manifeste ; ne pas additionner 30 scores. `overview.csv` fournit aussi les KPI uniques du corpus et le leader de la dernière date.

## 4. Préparer les cinq pages

| Page | Données et visuels |
| --- | --- |
| Vue d'ensemble | `overview`, `daily_metrics` : KPI, classement du jour, courbe historique, volumes de mentions, pertinence CCR. Afficher l'état des sources. |
| Personnalités | `personality_brief` : nom, visibilité, variation en points J-7, articles/vidéos récents, pertinence, dernier contenu CCR. |
| Thématiques CCR | Matrice `personalities.name` × `topics.topic`, mesure « Contenus par personnalité et thème ». Graphiques climat, Cat Nat, assurance, sécheresse, inondation, collectivités et prévention. |
| Actualités | `latest_activity` : date, nom, titre, source, thèmes et URL. Définir `url` comme catégorie **URL Web**. |
| Fiche rencontre | Sélecteur `personalities.name`, `personality_brief`, et table `latest_activity` filtrée : derniers contenus, sujets et liens à consulter. |

`top_5_topics`, `latest_articles`, `latest_videos`, `latest_ccr_topics` et les mots-clés sont du JSON dans les cellules CSV. Power Query peut les convertir avec `Json.Document`, puis développer les listes/enregistrements dans des requêtes de présentation séparées. Utiliser `latest_activity` directement si une table de liens suffit. Les listes de fiche comportent au plus cinq liens par type sur les 7 derniers jours ; le dernier contenu CCR est recherché sur 30 jours par défaut.

## 5. Actualiser et contrôler

1. Exécuter `python scripts/run_pipeline.py --demo` ou la commande réelle.
2. Lire `manifest.json` et `collection_status.csv` : mode, référence, volume et sources disponibles.
3. Dans Power BI Desktop, cliquer **Actualiser**.
4. Vérifier le mode, les types, les relations et la disponibilité des sources avant d'interpréter les classements.

Pour Power BI Service, les fichiers locaux nécessitent généralement une passerelle de données ou une copie contrôlée vers une source accessible au service. Le POC ne met pas en place de publication ni de planification Power BI.

Les données RSS/API représentent des mentions observées, pas des déclarations attribuées avec certitude. Les compteurs YouTube sont cumulés à la collecte et rattachés au jour de publication. Les chiffres de démonstration sont entièrement fictifs.
