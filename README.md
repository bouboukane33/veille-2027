# CCR Veille 2027

POC Python de veille médiatique et institutionnelle sur des personnalités politiques françaises. Il collecte des **métadonnées publiques** de presse/RSS et de YouTube, détecte des mentions et des thèmes CCR, conserve les résultats dans SQLite et génère des CSV pour Power BI.

**Le score de visibilité décrit la couverture observée. Ce n'est ni un sondage, ni un score de popularité électorale, ni une mesure d'intention de vote.** La liste initiale est une liste de suivi configurable, sans affirmation de candidature à l'élection de 2027.

## Application web sur Vercel

Une interface React/Vite dans `web/` fournit la vue d'ensemble, les personnalités, la matrice thématique, les actualités, les fiches rencontre et les exports CSV. Elle affiche les données réelles publiées dans une base **Supabase dédiée** ; GitHub Actions exécute le pipeline Python quotidiennement. Le stockage persiste entre les machines et déploiements.

Voir **[docs/VERCEL.md](docs/VERCEL.md)** pour créer la nouvelle base, installer le schéma, ajouter les secrets GitHub/Vercel et déployer avec **Root Directory = `web`**. Les accès aux comptes doivent être configurés ; le dépôt ne contient aucune clé. La connexion réelle est sélectionnée par défaut. Un aperçu fictif séparé permet de tester l'interface sans simuler une collecte réussie.

```bash
cd web
npm ci
npm run dev
```

Le reste de ce README décrit le pipeline Python, également utilisable indépendamment du site.

## Démarrage sous Windows

Pré requis : Python **3.11 ou plus récent** et un terminal ouvert dans le dépôt `veille-2027`.

### Invite de commandes Windows (cmd)

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .env.example .env
python scripts/init_db.py
python scripts/run_pipeline.py --demo
python -m pytest -q
```

### PowerShell, sans changer la politique d'exécution

L'activation du virtualenv est facultative : utiliser son interpréteur directement.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe scripts\run_pipeline.py --demo
.\.venv\Scripts\python.exe -m pytest -q
```

Créer `.env` uniquement s'il n'existe pas déjà. Si votre installation ne fournit pas `py`, utiliser `python` à la place, après `python --version`.

### Linux / macOS / cloud

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Seulement si .env n'existe pas :
cp .env.example .env
python scripts/init_db.py
python scripts/run_pipeline.py --demo
python -m pytest -q
```

Le dépôt et ses chemins sont résolus par le code ; les scripts fonctionnent aussi lorsqu'ils sont lancés par leur chemin absolu depuis un autre répertoire. Le pipeline Python ne nécessite pas de service permanent ; l'application web est une interface supplémentaire.

## Démonstration immédiate, sans clé

```bash
python scripts/run_pipeline.py --demo
# Date reproductible pour une démonstration :
python scripts/run_pipeline.py --demo --as-of 2026-09-30
```

Avec la configuration initiale : **10 personnalités, 100 articles fictifs, 40 vidéos fictives et 30 jours d'indicateurs**, avec des niveaux de visibilité et des thèmes variés. Le générateur s'adapte à la liste JSON.

- Base démo : `database/ccr_veille_demo.db`.
- CSV démo : `data/exports/demo/`.
- Métadonnées brutes : `data/raw/demo_latest.json`.
- Compte rendu : `data/processed/demo_report.json`.
- Journal : `logs/pipeline_demo.log`.

Les titres et sources portent `DEMO / FICTIF`, les lignes de données portent `is_demo=1` et les URL utilisent `example.invalid`, domaine réservé qui ne constitue pas une source réelle. Les textes sont inventés et n'attribuent aucune déclaration réelle aux personnalités. Le manifeste indique aussi le mode.

Une relance au même jour donne les mêmes CSV sans doublons ; une autre date décale le calendrier du jeu démo sans ajouter 140 contenus. Les modes démo et réel utilisent des bases et répertoires distincts. Ne jamais combiner leurs CSV dans Power BI. Une modification importante de la liste peut laisser des contenus fictifs archivés ; pour recréer une démo vierge, supprimer **uniquement** `database/ccr_veille_demo.db` puis relancer.

## Collecte réelle

```bash
python scripts/run_pipeline.py
```

Résultats : `database/ccr_veille.db`, `data/exports/live/`, `data/raw/live_latest.json`, `data/processed/live_report.json` et `logs/pipeline.log`.

Configurer les clés facultatives dans un fichier `.env` local, jamais dans Git :

```dotenv
NEWS_API_KEY=
YOUTUBE_API_KEY=
```

Les variables déjà définies dans le processus prennent priorité sur `.env`. Ne pas communiquer les clés en chat ou les inclure dans des exports. Le programme n'affiche pas leur valeur. Les secrets gérés par un proxy cloud doivent être associés aux destinations HTTPS indiquées ci-dessous.

| Source | Configuration | Données et limites |
| --- | --- | --- |
| RSS publics | `rss_feeds` dans `settings.json` | Titres, résumés, liens et dates ; fonctionne sans clé. Les flux initiaux sont Franceinfo politique et Le Monde politique. |
| NewsAPI | `NEWS_API_KEY` | Endpoint `everything`, recherche par nom, français, ordre chronologique ; maximum configurable par personnalité. Le plan souscrit peut limiter l'historique, retarder les articles et restreindre l'utilisation. |
| YouTube Data API v3 | `YOUTUBE_API_KEY` | `search.list` puis `videos.list` ; titre, description, chaîne et compteurs agrégés. Aucun appel aux commentaires, abonnés ou profils utilisateurs. |

Les articles complets et vidéos ne sont pas téléchargés. Aucun scraping de pages n'est effectué. Respecter les licences, conditions des API/RSS, droits de réutilisation et règles internes CCR avant une collecte régulière.

Une clé absente, une source inaccessible, une entrée sans date valide ou une API en panne est signalée ; les autres collecteurs poursuivent leur travail. `collection_status.csv` et `manifest.json` distinguent `ok`, `disabled`, `not_configured`, `skipped_missing_key`, `quota_limited`, `partial` et `failed`. Un pipeline terminé avec une couverture incomplète **ne valide pas la collecte de ces sources**. Les scores nuls en l'absence de données ne démontrent pas une absence de couverture médiatique.

Les erreurs locales de configuration, stockage ou export arrêtent le processus avec un code de sortie non nul. Les échecs de sources sont tolérés et visibles dans les journaux/exports, avec un code de sortie nul si le traitement local termine.

### Accès réseau cloud

Les destinations HTTPS nécessaires à la configuration initiale sont :

```text
www.francetvinfo.fr
www.lemonde.fr
newsapi.org
www.googleapis.com
```

Un nouveau flux RSS peut exiger l'ajout de son domaine aux paramètres réseau de l'environnement. Un `403` du proxy lors de l'ouverture du tunnel indique un blocage d'accès ; modifier un CSV ou désactiver TLS ne le résout pas. Les paramètres enregistrés dans le brouillon cloud doivent être appliqués avant de retester les sources. L'installation des dépendances utilise les domaines autorisés par le préréglage des gestionnaires de paquets.

### Quota YouTube

`max_youtube_videos_per_personality` est limité à 50 (10 par défaut), sans pagination. `youtube_max_search_requests` est le nombre maximal de recherches par exécution (10 par défaut). Les personnalités sont traitées dans l'ordre JSON. Une erreur HTTP 401/403 arrête les recherches YouTube restantes.

Avec les coûts usuels de l'API, une recherche coûte 100 unités et un appel `videos.list` coûte 1 unité : budget maximal attendu **1 010 unités** pour 10 recherches suivies de 10 appels de détails. Les retries peuvent augmenter ce coût ; le projet fait au plus un retry par requête par défaut. Vérifier les quotas et la tarification actuels dans la console Google avant de planifier une exécution.

## Configuration, sans changement de code

`config/personalities.json` : ajouter une entrée avec un `id` unique et stable, un `name`, `status: "suivi"` et les alias complets dans `keywords`. Le statut `inactif` exclut la personnalité des collectes et indicateurs. Les personnalités retirées du JSON restent archivées comme inactives en base afin de conserver l'intégrité des anciens contenus.

`config/topics.json` : thèmes et expressions CCR. Le classificateur ignore casse, accents, ponctuation et traits d'union ; il recherche des expressions avec des frontières de mots. Un même contenu peut relever de plusieurs thèmes. `content_topics.score=1` signifie « mot-clé présent », **pas une probabilité ni un soutien à un thème**. Les mots-clés trouvés sont exportés pour vérification. L'interface `TopicClassifier` permet un remplacement ultérieur par NLP/LLM.

`config/settings.json` : fenêtre de collecte/pertinence, plafonds, activation des sources, flux, timeout, retries, seuils, poids et durée des fiches. Les champs supplémentaires ont des valeurs par défaut si l'on utilise seulement la configuration minimale demandée. Les poids doivent totaliser 1. Les paramètres sont validés avant la collecte.

Une mention détectée dans un titre ou un résumé ne prouve pas que la personnalité a prononcé ces mots ni qu'elle partage le propos. Les fiches affichent des **contenus mentionnant** une personnalité ; vérifier le lien source avant toute interprétation institutionnelle. Le POC n'analyse ni transcription vidéo, ni sentiment, ni position politique.

## Nettoyage, déduplication et stockage

Les dates sont en UTC ISO 8601 ; les dates sans fuseau explicite sont interprétées en UTC. Une date absente ou invalide est exclue, sans la remplacer par la date de collecte. Les dates civiles des indicateurs sont aussi UTC.

La déduplication presse utilise l'URL canonique (sans fragment ni paramètres de suivi connus), puis la similarité `SequenceMatcher` de titres normalisés : seuil 0,94 et dates distantes d'au plus 2 jours par défaut. Les titres courts ne sont rapprochés que s'ils sont identiques ; des nombres différents empêchent le rapprochement approximatif. Les variantes d'URL sont conservées dans `article_url_aliases`. Cette heuristique peut fusionner à tort des articles ressemblants ou manquer des doublons ; les URL originales restent disponibles dans la base pour audit.

Les vidéos sont uniques par `video_id`. Les compteurs sont actualisés lorsque la même vidéo est retrouvée ; une statistique absente reste vide en CSV et ne remplace pas une valeur déjà connue. Pour les métriques, les valeurs inconnues contribuent zéro ; `youtube_stats_known_count` permet de voir la couverture des vues.

Tables principales : `personalities`, `news_articles`, `youtube_videos`, `content_topics`, `daily_metrics`. Tables complémentaires : `content_personalities`, `article_url_aliases`, `metadata`. Le schéma est dans `src/database/schema.sql`.

Un article ou une vidéo est conservé une seule fois. `personality_id` dans les tables de contenus indique la première association ; **utiliser `content_personalities` pour les analyses de toutes les personnalités**. Le même article compte une mention pour chacune des personnalités détectées. La somme des volumes par personnalité peut donc dépasser le nombre de contenus uniques. `content_key` dans les CSV (`news:<id>` ou `youtube:<id>`) évite les collisions entre types.

`vw_personality_dashboard` fournit l'historique des indicateurs des personnalités suivies avec `ccr_topic_count`, scores et tendance. `ccr_topic_count` / `topic_ccr_count` désigne le nombre de **contenus** comportant au moins un thème CCR ce jour, et non le nombre de thèmes.

## Formules des scores

### Visibilité quotidienne, de 0 à 100

Pour chaque jour de publication, les quatre composantes sont divisées par leur maximum parmi les personnalités suivies ce même jour. Si le maximum est nul, la composante contribue zéro. Les ratios sont bornés entre 0 et 1.

```text
visibilité = 100 × (
    0,35 × articles / maximum_articles
  + 0,30 × vues / maximum_vues
  + 0,15 × (likes + commentaires) / maximum_engagement
  + 0,20 × (articles + vidéos) / maximum_publications
)
```

L'engagement désigne uniquement les **compteurs agrégés**, sans contenu ni auteur de commentaire. La fréquence est ici le volume quotidien de publications. Les poids sont paramétrables dans `visibility_weights`. Une source absente ne redistribue pas ses poids ; sans vidéos, le plafond théorique de la visibilité est 55. La normalisation dépend du panel et de la disponibilité des sources, ce qui limite les comparaisons temporelles.

**Les vues, likes et commentaires YouTube sont des compteurs cumulés observés à la collecte**, rattachés ici au jour de publication de la vidéo. Ils ne représentent pas les vues reçues ce jour ni une mesure historique d'audience. Lors d'une recollecte, les indicateurs du passé peuvent être recalculés avec les nouveaux compteurs. La V1 ne conserve pas de série de snapshots d'audience.

### Pertinence CCR, de 0 à 100

Pour chaque date, utiliser uniquement les contenus présentant au moins un thème CCR et publiés dans les `lookback_days` derniers jours (30 par défaut).

```text
volume = min(nombre de contenus CCR / relevance_volume_target, 1)
diversité = nombre de thèmes CCR distincts / nombre de thèmes configurés
récence = moyenne(2 ^ (-âge_en_jours / relevance_half_life_days))
pertinence = 100 × (0,50 × volume + 0,30 × diversité + 0,20 × récence)
```

Par défaut : cible de 10 contenus, demi-vie de 7 jours et poids `relevance_weights`. Sans contenu CCR, le score est zéro. Ce score ne tient compte ni de l'appartenance politique ni des statistiques YouTube. Un mot-clé dans un article parlant d'une personne peut suffire ; la vérification humaine demeure nécessaire.

### Historique et tendances

`daily_metrics` exporte au moins 30 jours calendaires, incluant les jours sans contenu. Les fenêtres de calcul antérieures sont chargées pour calculer les moyennes dès le premier jour exporté ; les journées sans contenu connu valent zéro, même si la source ne permet pas d'historique complet.

- `visibility_yesterday` : score J-1.
- `visibility_delta` : score du jour moins J-1, en points.
- `visibility_avg_7d`, `visibility_avg_30d` : moyenne incluant le jour courant et les jours sans contenu.
- `visibility_change_7d` : score du jour moins le score J-7, en points.
- `trend` : `UP` si delta J-1 > 2 points, `DOWN` si delta < -2, sinon `STABLE`, seuil configurable.

Les comparaisons sont descriptives sur le corpus collecté. Le changement d'une configuration, de la couverture API ou du panel peut modifier les scores historiques recalculés.

## Exports Power BI

Le pipeline génère **13 CSV** dans `data/exports/demo/` ou `data/exports/live/`, avec en-têtes même si une table est vide, séparateur virgule, UTF-8 et dates ISO 8601 :

| CSV | Usage |
| --- | --- |
| `personalities.csv` | Dimension des personnalités et statuts |
| `news_articles.csv` | Articles uniques et métadonnées |
| `youtube_videos.csv` | Vidéos uniques et derniers compteurs collectés |
| `content_topics.csv` | Liaison contenu × thème, expressions trouvées |
| `daily_metrics.csv` | Indicateurs, scores et tendances quotidiennes |
| `latest_activity.csv` | Derniers contenus × personnalités, maximum 200 lignes configurable |
| `personality_brief.csv` | Fiche rencontre, une ligne par personnalité suivie |
| `content.csv` | Tous les contenus uniques et leurs `content_key` |
| `content_personalities.csv` | Liaison contenu × personnalité |
| `topics.csv` | Dimension thématique |
| `personality_dashboard.csv` | Export de la vue SQLite |
| `overview.csv` | KPI globaux du corpus, leader du jour |
| `collection_status.csv` | Couverture et état des sources pour la dernière collecte |

`manifest.json` décrit le mode, la date de référence, le nombre de lignes et l'état des sources. Les fichiers sont écrits temporairement puis remplacés, le manifeste en dernier. Lancer les pipelines **séquentiellement**, sans exécutions simultanées ; fermer un CSV ouvert avec verrouillage (par exemple Excel sous Windows) avant l'export. Les CSV et bases générés sont ignorés par Git et se régénèrent avec la commande démo.

La fiche fournit la visibilité du jour, la variation J-7, la pertinence CCR, les volumes récents sur `brief_days` (7 par défaut), les 5 thèmes les plus fréquents et jusqu'à 5 articles/vidéos récents. Les listes sont des cellules JSON. Le dernier contenu CCR est recherché dans la fenêtre `lookback_days` ; il peut être plus ancien que les 7 jours de la fiche.

Voir **[docs/POWER_BI.md](docs/POWER_BI.md)** pour l'import, les relations, les mesures DAX et les cinq pages proposées. Aucun PBIX n'est généré.

## Exécuter les étapes séparément

```bash
python scripts/init_db.py                 # Créer le schéma, synchroniser le JSON
python scripts/collect_data.py            # APIs/RSS → dernier lot brut JSON
python scripts/process_data.py            # JSON → SQLite, classification, scores, CSV
python scripts/export_powerbi.py          # Réexporter sans requête réseau ni recalcul
```

Tous acceptent `--demo`. `collect_data.py` accepte aussi `--as-of YYYY-MM-DD`. `process_data.py` conserve la date du lot, et `export_powerbi.py` utilise la dernière date d'indicateurs en base. `data/raw/*latest.json` contient le dernier lot, pas une archive exhaustive ; la base conserve les contenus collectés. Les logs sont appendus ; prévoir une politique de conservation interne pour un usage prolongé.

## Tests et validation

```bash
python -m pytest -q
python scripts/run_pipeline.py --demo --as-of 2026-09-30
```

Les tests couvrent normalisation, frontières de mots, déduplication persistante, multi-mentions, mise à jour vidéo, séparation démo/réel, scores, tendances, CSV et intégrité SQLite, ajout d'une personnalité par JSON, relances reproductibles et contrats API/RSS simulés. Les tests de collecteurs n'appellent pas Internet et ne consomment pas de quota. Une réussite des tests simulés n'atteste pas l'accès à une API réelle ; celui-ci dépend des clés, quotas, plans et règles réseau.

## Architecture et évolution

```text
API/RSS → collectors → Content → cleaner/deduplicator → SQLite
                              → TopicClassifier → metrics/scoring
                                                → CSV → Power BI
```

`src/pipeline.py` orchestre les fonctions indépendamment des CLI. `src/database/repository.py` regroupe le SQL ; remplacer ce composant permet une migration vers PostgreSQL. Dataiku ou un ordonnanceur peut appeler les fonctions ou scripts, sans dépendre de Power BI. Le schéma SQLite contient deux relations polymorphes (`content_topics` et `content_personalities`) dont l'intégrité vers les contenus est gérée par le dépôt ; une migration devra créer les contraintes adaptées.

L'application web, le stockage de snapshots PostgreSQL/Supabase et l'orchestration quotidienne GitHub Actions sont maintenant implémentés ; ils nécessitent un raccordement aux comptes pour fonctionner en production. Évolutions envisagées : tables PostgreSQL analytiques normalisées, Dataiku, API métier, résumés IA, embeddings, sémantique, recherche plein texte et alertes. Le POC n'identifie pas automatiquement des « interventions importantes » : utiliser les dates, thèmes et liens pour une sélection humaine.

## Protection des données et limites

- Seules des métadonnées publiques relatives aux personnalités politiques suivies sont analysées.
- Aucun profil individuel d'électeur n'est créé.
- Aucun abonné, commentateur ou utilisateur de réseau social n'est profilé.
- Aucune opinion politique individuelle de citoyen n'est inférée.
- Aucun ciblage électoral ni prédiction de vote n'est effectué.
- Le score de visibilité n'est pas un sondage et ne mesure pas l'intention de vote.
- Chaque résultat doit rester traçable vers son URL source et les mots-clés détectés.

La couverture dépend des sources, de leurs limites et de leurs métadonnées. Une recherche par nom peut inclure des homonymes, citations indirectes ou critiques. Les thèmes par mots-clés peuvent contenir des faux positifs (par exemple « assurance » hors contexte assurantiel). Vérifier les sources et l'attribution des prises de parole avant une rencontre ou une diffusion. Utiliser la démo uniquement pour tester le fonctionnement, jamais comme preuve d'une activité politique réelle.
