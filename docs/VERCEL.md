# Application web et collecte réelle

L’application React/Vite est dans `web/`. Elle se déploie sur Vercel et lit les données réelles dans une **base Supabase dédiée**. La collecte Python reste exécutée par GitHub Actions : pas de processus permanent ni d’écriture dans le système de fichiers de Vercel.

```text
RSS / NewsAPI / YouTube
          ↓
GitHub Actions : restaurer → pipeline Python / SQLite → CSV
          ↓
Supabase / PostgreSQL : archive persistante + dataset publié
          ↓
Fonctions Vercel → application React → consultation / CSV Power BI
```

La connexion réelle est sélectionnée par défaut. Sans stockage configuré, l’interface affiche l’étape à terminer ; elle ne remplace pas les résultats réels par des données fictives. L’aperçu démo est activé explicitement et porte un bandeau permanent.

Le projet Supabase retenu pour ce dépôt est **`okcesmqirgzupiagxeui`**, avec l’URL publique **`https://okcesmqirgzupiagxeui.supabase.co`**. Son [SQL Editor](https://supabase.com/dashboard/project/okcesmqirgzupiagxeui/sql/new) permet d’installer le schéma ci-dessous. Aucun secret n’est inclus dans cette documentation.

## 1. Créer une base indépendante

1. Ouvrir <https://supabase.com/dashboard/new> et choisir une organisation.
2. Créer un projet **ccr-veille-2027**, avec une région européenne et un mot de passe fort conservé en lieu sûr.
3. Attendre la fin du provisionnement.
4. Dans **SQL Editor**, créer une requête, copier le contenu de [`supabase/schema.sql`](../supabase/schema.sql) et cliquer **Run**.
5. Relever l’URL publique du projet, sous la forme `https://REFERENCE.supabase.co`, dans les paramètres API.
6. Relever la clé serveur **service_role** dans les clés API historiques/Legacy. Ne jamais utiliser la clé `anon` pour ce pipeline. Ne pas transmettre cette clé en chat ni la committer.

Le schéma crée uniquement `public.ccr_snapshots` et la fonction `public.publish_ccr_snapshot`. Il ne supprime aucune autre table. Le stockage est inaccessible aux rôles Supabase `anon` et `authenticated` ; seule la clé serveur peut restaurer/publier les données. Aucune clé Supabase n’est envoyée au navigateur.

Pour ce POC, PostgreSQL conserve un snapshot JSONB avec **l’archive complète** des tables SQLite (articles, vidéos, personnalités, associations, alias et métriques), et un dataset distinct pour l’interface. À la prochaine tâche GitHub, SQLite est restaurée depuis cette archive avant la collecte. Les contenus restent donc conservés même si la machine GitHub change.

La publication remplace atomiquement le snapshot. Une révision attendue empêche une tâche ayant lu un ancien état d’écraser une publication récente. Les exécutions GitHub sont aussi sérialisées. Le mode démo est refusé par la publication réelle.

Ce stockage JSONB est adapté au POC et réutilise le moteur Python existant. Il ne constitue pas encore une migration des entités vers des tables analytiques PostgreSQL normalisées. Pour une archive volumineuse ou plusieurs producteurs, prévoir cette migration et une API paginée. Le dataset web est limité volontairement à 3,5 Mo pour rester sous la limite des réponses serverless.

## 2. Configurer GitHub Actions

Dans `bouboukane33/veille-2027`, ouvrir **Settings → Secrets and variables → Actions → New repository secret**, puis ajouter :

| Secret GitHub | Requis | Utilisation |
| --- | --- | --- |
| `SUPABASE_URL` | Oui | URL du nouveau projet Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Oui | Clé serveur pour restaurer et publier le corpus |
| `NEWS_API_KEY` | Facultatif | Presse via NewsAPI |
| `YOUTUBE_API_KEY` | Facultatif | YouTube Data API v3 |

Les RSS fonctionnent sans clé s’ils sont accessibles depuis le runner GitHub. Au moins une source doit retourner des contenus réels pour la première publication. Un corpus vide avec toutes les sources indisponibles ne crée pas de faux tableau de bord.

Dans **Actions → Collecte CCR Veille → Run workflow**, sélectionner `main` et lancer. Le workflow :

1. Installe Python et les dépendances.
2. Télécharge l’archive Supabase, ou initialise le premier corpus.
3. Exécute les collectes, traitements, scores et exports.
4. Publie le résultat dans Supabase avec contrôle de révision.
5. Conserve les CSV Power BI et le journal comme artefact GitHub pendant 14 jours.

Le déclenchement quotidien est configuré à **06 h UTC**, soit **07 h à Paris en hiver et 08 h en été**. GitHub peut retarder une tâche planifiée ; le site affiche la date effective du dernier dataset publié. La planification nécessite un dépôt actif et les permissions GitHub Actions habituelles. Aucune clé de collecte n’est nécessaire sur Vercel lui-même.

Les erreurs de sources restent visibles dans le dataset et le journal. Si Supabase ne peut pas être lu, la tâche s’arrête avant collecte afin de ne pas écraser une archive inaccessible. Si une publication est incertaine, vérifier la révision distante avant une nouvelle exécution.

## 3. Déployer sur Vercel

Importer `bouboukane33/veille-2027` dans Vercel, ou configurer le projet prévu pour cette application (par exemple `bossea`). Utiliser :

| Paramètre Vercel | Valeur |
| --- | --- |
| Git Repository | `bouboukane33/veille-2027` |
| Production Branch | `main` |
| **Root Directory** | **`web`** |
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Node.js Version | 24.x |

Dans **Settings → Environment Variables**, ajouter pour les environnements de déploiement souhaités :

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Utiliser les valeurs du **nouveau projet dédié**, pas celles d’une autre application. Ne jamais préfixer ces variables par `VITE_` : ce préfixe les rendrait accessibles dans le code client. Redéployer après avoir ajouté ou modifié les variables.

`web/vercel.json` prépare les trois fonctions `/api/dataset`, `/api/status` et `/api/collect`. La navigation utilise des fragments URL (`#overview`, `#activity`, etc.), ce qui évite les erreurs de routage d’une application statique. Les réponses API désactivent le cache pour relire le dernier snapshot.

Les données peuvent être lues publiquement si le déploiement est public. Pour un usage interne CCR, configurer l’accès au déploiement selon les possibilités de votre compte Vercel, ou ajouter une authentification applicative avant la diffusion interne souhaitée. La V1 ne gère pas de comptes utilisateurs ; la clé opérateur décrite ci-dessous protège uniquement le déclenchement de collecte.

Une fois déployé, vérifier : chargement de l’accueil réel, date de référence, état des sources, filtres, fiche et téléchargement d’un CSV. Un build réussi ne valide pas à lui seul les accès Supabase ou les clés API.

### Déploiement CLI alternatif

Avec une session Vercel authentifiée :

```bash
cd web
npm ci
npm run build
npx vercel link --project bossea
npx vercel --prod
```

La liaison d’un projet existant doit correspondre à l’application prévue. Les identifiants locaux `.vercel/` sont ignorés par Git. Sans accès au compte Vercel, l’assistant peut préparer le code mais ne peut pas publier dans votre projet.

## 4. Lancer une collecte depuis le site (facultatif)

Le lancement manuel depuis GitHub Actions fonctionne sans cette option. Pour activer le bouton de l’application, ajouter dans **Vercel** :

| Variable serveur | Valeur |
| --- | --- |
| `GH_WORKFLOW_TOKEN` | Jeton GitHub limité au dépôt avec permission **Actions: Read and write** |
| `COLLECT_ADMIN_KEY` | Secret opérateur long et aléatoire, distinct des clés API |
| `GITHUB_REPOSITORY` | `bouboukane33/veille-2027` (valeur par défaut) |

Le bouton de **Sources & méthode** demande uniquement la clé opérateur. Le navigateur n’obtient jamais le jeton GitHub ou la clé Supabase. Le serveur vérifie la clé opérateur puis demande l’exécution du workflow. Une réponse acceptée signifie **collecte demandée**, pas collecte terminée. L’interface surveille la révision publiée pendant 15 minutes ; sinon elle invite à consulter GitHub Actions.

Ne pas entrer une clé NewsAPI, YouTube ou Supabase dans cette boîte. La clé opérateur reste seulement en mémoire de la page et est effacée à la fermeture. Les appels aux API et la consommation de quota ont lieu dans le runner Python, pas lors de la navigation sur le site.

## 5. Développement local

Python reste utilisable comme précédemment. Pour l’interface :

```bash
cd web
npm ci
npm run dev
```

Dans `web/.env.local` (ignoré par Git), configurer les mêmes variables serveur Supabase si l’on souhaite consulter le corpus réel. Le serveur de développement fournit les mêmes routes API que Vercel. Si le stockage manque, l’interface affiche son état de connexion et permet de choisir explicitement l’aperçu fictif.

Pour régénérer uniquement l’aperçu depuis la racine du dépôt :

```bash
python scripts/run_pipeline.py --demo
python scripts/export_web.py --demo
```

`web/public/demo.json` est un jeu fictif versionné pour que le build Vercel ne nécessite pas Python. Il n’est pas utilisé comme remplacement automatique du corpus réel. `python scripts/export_web.py` exporte un `data/processed/web_live.json` local ignoré par Git, en dehors des assets web ; ce fichier n’est pas la source de l’application de production.

Collecte/publication cloud depuis un poste autorisé, avec `.env` configuré :

```bash
python scripts/run_cloud_pipeline.py
```

Exécuter les producteurs séquentiellement. Les sauvegardes/restaurations locales doivent utiliser une base de travail dédiée à cette collecte.

## 6. Validation

```bash
# À la racine
python -m pytest -q
# Dans web/
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Les tests Python couvrent aussi l’export web et la restauration d’archive. Les tests serveur valident les réponses API, l’absence de fuite des clés, la séparation des modes et le déclenchement authentifié. La migration est exécutée dans un moteur PostgreSQL embarqué PGlite pour contrôler la publication, les révisions et les permissions. Les tests navigateur couvrent navigation, filtres, fiches, téléchargement CSV et affichage mobile.

Ces tests ne remplacent pas une collecte réelle ni une vérification du déploiement Vercel avec vos comptes. Les clés, le projet Supabase dédié et l’authentification Vercel sont les prérequis externes restants.
