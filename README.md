# Application de Gestion Financière

Une application web avancée de gestion financière conçue pour le suivi et l'analyse détaillée des dépenses personnelles et professionnelles.

## Technologies utilisées
- Streamlit pour l'interface utilisateur
- Python 3.11
- PostgreSQL pour la base de données
- Pandas pour le traitement des données
- Plotly pour la visualisation

## Démarrage rapide

1. Décompressez le fichier `app.zip`
2. Ouvrez `index.html` dans votre navigateur pour voir la présentation et la documentation de l'application
3. Suivez les instructions d'installation détaillées dans la page d'index

## Installation détaillée

1. Installez Python 3.11 ou supérieur
2. Installez les dépendances :
```bash
pip install streamlit pandas plotly psycopg2-binary
```

3. Configurez une base de données PostgreSQL et mettez à jour les variables d'environnement :
- DATABASE_URL
- PGUSER
- PGPASSWORD
- PGDATABASE
- PGHOST
- PGPORT

## Démarrage de l'application

```bash
streamlit run login.py
```

## Identifiants de test
- Admin: username: `admin`, password: `admin123`
- Utilisateur: username: `user`, password: `user123`

## Structure des fichiers
- `index.html` : Documentation et présentation de l'application
- `login.py` : Page de connexion et système d'authentification
- `database.py` : Gestion de la base de données
- `utils.py` : Fonctions utilitaires
- `pages/` : Contient les différentes pages de l'application
  - `1_accueil.py` : Page d'accueil
  - `2_categories.py` : Gestion des catégories
  - `3_saisie.py` : Saisie des transactions
  - `4_rapports.py` : Rapports et analyses
  - `5_tableau_bord.py` : Tableau de bord