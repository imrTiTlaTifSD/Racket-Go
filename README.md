# Racket-Go

Une vitrine de raquettes de padel, pensée pour les visiteurs qui arrivent depuis TikTok sur leur téléphone. Le modèle « Sport épuré » présente les photos, prix, états et stocks, avec des liens vers WhatsApp, Facebook, Leboncoin et Vinted.

La page publique permet de consulter le catalogue et de contacter le vendeur. L'espace privé permet de modifier les produits, leurs photos et leurs stocks, ainsi que les liens de contact. Il n'y a pas de panier ni de paiement en ligne : les ventes se concluent via vos canaux habituels et les stocks se mettent à jour manuellement.

## Démarrer en local

Prérequis : **Python 3.12 ou 3.13** et [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/imrTiTlaTifSD/Racket-Go.git
cd Racket-Go
uv sync --frozen
uv run streamlit run app.py
```

Le site est accessible sur <http://localhost:8501>. `uv sync --frozen` utilise les versions du fichier `uv.lock` et installe également les outils de développement du groupe `dev`.

## Activer l'espace privé

Aucun mot de passe administrateur n'est fourni par défaut. Pour activer l'administration, générez un hash de votre propre mot de passe :

```bash
uv run python security.py
```

La saisie est masquée ; choisissez un mot de passe d'au moins **12 caractères**. Conservez le hash affiché dans la configuration locale. Il ne faut pas mettre votre mot de passe dans le code ni dans Git.

### Option locale avec les secrets Streamlit

Copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml`, puis remplacez le champ `RACKET_GO_ADMIN_PASSWORD_HASH` par le hash généré. Le fichier contenant vos secrets est ignoré par Git. Redémarrez Streamlit après une modification de ces secrets.

### Option par variables d'environnement

Les mêmes paramètres peuvent être fournis au processus :

- `RACKET_GO_ADMIN_PASSWORD_HASH` : hash généré par `security.py`, recommandé.
- `RACKET_GO_ADMIN_PASSWORD` : mot de passe en clair si votre hébergeur impose cette méthode ; renseignez une seule des deux options.
- `RACKET_GO_DATA_DIR` : dossier de stockage, `./data` par défaut.

Le fichier `.env` est utilisé par Docker Compose. Pour le lancement direct avec Streamlit, utilisez les secrets Streamlit ou injectez les variables via votre gestionnaire d'environnement ; Streamlit ne charge pas automatiquement `.env`.

Ouvrez ensuite <http://localhost:8501/?admin=1> et connectez-vous avec votre mot de passe. Ne partagez pas les fichiers de secrets, même si vous changez le mot de passe ensuite.

## Ajouter vos vraies raquettes et vos contacts

La première initialisation propose **quatre raquettes de démonstration**. Leurs noms, prix et stocks sont fictifs et signalés comme tels : ils servent uniquement à montrer la présentation.

Dans l'espace privé :

1. Renseignez vos liens de contact et votre numéro WhatsApp avec son indicatif international.
2. Ajoutez chaque vraie raquette : marque, modèle, état, description, prix, quantité disponible et photo.
3. Retirez les produits de démonstration avant de partager le site.
4. Mettez à jour le stock après chaque vente et vérifiez vos liens depuis un téléphone.

Les liens de contact apparaissent lorsqu'ils sont renseignés. Vous pouvez partager l'adresse publique du site dans votre bio TikTok.

## Données et sauvegardes

Le catalogue et les paramètres sont conservés dans une base **SQLite** ; les photos ajoutées sont stockées dans le même dossier de données. Ces données restent locales au serveur et ne sont jamais destinées à Git.

Utilisez un dossier persistant pour `RACKET_GO_DATA_DIR`. Sauvegardez régulièrement **tout ce dossier**, idéalement pendant que l'application est arrêtée, pour conserver la base et les photos ensemble. Pour restaurer, arrêtez l'application, remettez le dossier sauvegardé en place, puis relancez-la.

## Déployer avec Docker

Prérequis : Docker avec Docker Compose.

```bash
cp .env.example .env
```

Renseignez dans `.env` le hash généré via `uv run python security.py`. Entourez sa valeur d'**apostrophes simples** pour que Docker Compose conserve les caractères `$` du hash, par exemple `RACKET_GO_ADMIN_PASSWORD_HASH='votre_hash_complet'`. Puis lancez :

```bash
docker compose up --build -d
docker compose logs -f
```

Le site écoute sur le port **8501**. Le volume Docker `racket_go_data` conserve les produits et photos lorsque le conteneur est recréé. `docker compose down` conserve ce volume ; **`docker compose down -v` le supprime et efface vos données**.

Pour un site public, placez le service derrière le proxy HTTPS de votre hébergeur et configurez votre domaine. Protégez les secrets de déploiement et sauvegardez le volume. L'image fonctionne avec un utilisateur sans privilèges et vérifie le point de santé Streamlit.

Si votre environnement utilise un proxy HTTPS nécessitant une autorité de certification supplémentaire, fournissez le **bundle CA approuvé par votre environnement** au build. La vérification TLS reste active et le bundle n'est pas conservé dans l'image :

```bash
docker build --secret id=build_ca_bundle,src=/chemin/vers/ca-bundle.crt -t racket-go:local .
docker compose up -d --no-build
```

### Streamlit Community Cloud

L'application peut aussi être lancée sur [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) en choisissant ce dépôt, `app.py` et Python 3.12. Le fichier `requirements.txt` fournit les dépendances pour cette plateforme. Ajoutez `RACKET_GO_ADMIN_PASSWORD_HASH` dans les secrets de l'application, sans l'ajouter au dépôt.

**Le stockage local de Community Cloud n'est pas garanti durable** : un redémarrage ou un redéploiement peut perdre la base et les photos. Pour gérer votre vrai stock avec cette version, privilégiez Docker avec un volume persistant et des sauvegardes. Un stockage externe serait nécessaire pour garantir cette persistance sur Community Cloud.

## Développement et vérification

```bash
uv sync --frozen
uv run pytest
```

Le dépôt contient les dépendances verrouillées dans `uv.lock`. Pour exporter les dépendances de production après une mise à jour volontaire :

```bash
uv export --frozen --no-dev --no-emit-project --output-file requirements.txt
```

Le projet se développe directement dans son checkout ; chaque tâche cloud est déjà isolée et n'a pas besoin d'un worktree supplémentaire.

Ne commitez jamais `.env`, `.streamlit/secrets.toml`, le dossier `data/`, une base SQLite ou des photos privées. Vérifiez `git status` avant chaque commit. Les fichiers d'exemple ne doivent contenir aucune vraie valeur secrète.
