import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import hashlib
import json

class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self._create_tables()

    def connect(self):
        """Établit une nouvelle connexion à la base de données."""
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            try:
                if self.conn is None or self.conn.closed:
                    self.conn = psycopg2.connect(
                        dbname=os.environ['PGDATABASE'],
                        user=os.environ['PGUSER'],
                        password=os.environ['PGPASSWORD'],
                        host=os.environ['PGHOST'],
                        port=os.environ['PGPORT']
                    )
                    self.conn.autocommit = True
                    print("Connexion à la base de données établie avec succès")
                    return
                else:
                    return
            except Exception as e:
                attempt += 1
                if attempt == max_attempts:
                    print(f"Erreur de connexion à la base de données après {max_attempts} tentatives: {str(e)}")
                    raise
                print(f"Tentative de connexion {attempt}/{max_attempts} échouée, nouvelle tentative dans 5 secondes...")
                import time
                time.sleep(5)

    def ensure_connection(self):
        """Assure que la connexion est active."""
        try:
            if self.conn is None or self.conn.closed:
                self.connect()
            # Vérifie si la connexion est active
            with self.conn.cursor() as cur:
                cur.execute('SELECT 1')
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"Erreur de connexion détectée: {str(e)}")
            self.connect()

    def _create_tables(self):
        """Crée les tables si elles n'existent pas."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Create projects table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        inclus_calcul BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Table 'projects' créée ou déjà existante")

                # Reste du code existant pour users, categories
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        role TEXT CHECK (role IN ('admin', 'user')) NOT NULL,
                        full_name TEXT,
                        email TEXT UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Drop existing foreign key if exists
                cur.execute("""
                    DO $$ 
                    BEGIN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'transactions_project_fkey'
                            AND table_name = 'transactions'
                        ) THEN
                            ALTER TABLE transactions DROP CONSTRAINT transactions_project_fkey;
                        END IF;
                    END $$;
                """)
                
                # Create transactions table with foreign key to categories
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        date DATE NOT NULL,
                        montant NUMERIC(15, 2) NOT NULL,
                        libelle TEXT NOT NULL,
                        category_id INTEGER REFERENCES categories(id) ON UPDATE NO ACTION ON DELETE NO ACTION,
                        type TEXT CHECK (type IN ('charge', 'recette')) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        project TEXT,
                        is_paid BOOLEAN DEFAULT FALSE,
                        paid BOOLEAN DEFAULT TRUE,
                        payer BOOLEAN DEFAULT FALSE,
                        payment_date DATE
                    )
                """)

                # Insert missing projects from transactions
                cur.execute("""
                    INSERT INTO projects (name)
                    SELECT DISTINCT t.project 
                    FROM transactions t 
                    LEFT JOIN projects p ON t.project = p.name 
                    WHERE t.project IS NOT NULL 
                    AND p.name IS NULL
                    ON CONFLICT (name) DO NOTHING;
                """)

                # Create todo_tasks table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS todo_tasks (
                        id SERIAL PRIMARY KEY,
                        project_name TEXT NOT NULL,
                        due_date DATE NOT NULL,
                        description TEXT,
                        steps JSONB DEFAULT '[]'::jsonb,
                        requirements TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Tables créées ou mises à jour avec succès")

                # Create partners table -------------  added by hamza -------------
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS partners (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        share_percentage NUMERIC(5, 2) NOT NULL
                    )
                """)
                print("Table 'partners' créée ou déjà existante")
                
                
                # Create partner_payments table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS partner_payments (
                        id SERIAL PRIMARY KEY,
                        partner_id INTEGER REFERENCES partners(id) ON UPDATE NO ACTION ON DELETE NO ACTION,
                        amount NUMERIC(15, 2) NOT NULL,
                        payment_date DATE DEFAULT CURRENT_DATE,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Table 'partner_payments' créée ou déjà existante")
                
                # Create immobilisations table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS immobilisations (
                        id SERIAL PRIMARY KEY,
                        nom VARCHAR(255) NOT NULL,
                        description TEXT,
                        prix_total NUMERIC(15, 2) NOT NULL,
                        date_acquisition DATE DEFAULT CURRENT_DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Table 'immobilisations' créée ou déjà existante")
                
                
                # Create transactions_investissement table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transactions_investissement (
                        id SERIAL PRIMARY KEY,
                        associe_id INTEGER REFERENCES partners(id) ON UPDATE NO ACTION ON DELETE NO ACTION,
                        immobilisation_id INTEGER REFERENCES immobilisations(id) ON UPDATE NO ACTION ON DELETE NO ACTION,
                        montant NUMERIC(15, 2) NOT NULL,
                        date_transaction DATE DEFAULT CURRENT_DATE,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Table 'transactions_investissement' créée ou déjà existante")
                
                # ---------- End section added by hamza ------- #

        except Exception as e:
            print(f"Erreur lors de la création des tables: {str(e)}")
            raise


    def get_all_users(self):
        """Récupère tous les utilisateurs."""
        self.ensure_connection()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, username, role, full_name, email, created_at, last_login
                    FROM users
                    ORDER BY username
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            return []

    def create_user(self, username, password, role, full_name=None, email=None):
        """Crée un nouvel utilisateur."""
        self.ensure_connection()
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password, role, full_name, email)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (username, hashed_password, role, full_name, email))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"Erreur lors de la création de l'utilisateur: {str(e)}")
            raise

    def update_user(self, user_id, full_name=None, email=None, new_password=None):
        """Met à jour les informations d'un utilisateur."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                if new_password:
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    cur.execute("""
                        UPDATE users 
                        SET full_name = %s, email = %s, password = %s
                        WHERE id = %s
                    """, (full_name, email, hashed_password, user_id))
                else:
                    cur.execute("""
                        UPDATE users 
                        SET full_name = %s, email = %s
                        WHERE id = %s
                    """, (full_name, email, user_id))
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}")
            raise

    def delete_user(self, user_id):
        """Supprime un utilisateur."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        except Exception as e:
            print(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
            raise

    def add_category(self, name, description=None):
        """Ajoute une nouvelle catégorie."""
        if not name:
            raise ValueError("Le nom de la catégorie est obligatoire")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO categories (name, description)
                    VALUES (%s, %s)
                    RETURNING id
                """, (name, description))
                category_id = cur.fetchone()[0]
                print(f"Catégorie '{name}' créée avec succès (ID: {category_id})")
                return category_id
        except psycopg2.Error as e:
            print(f"Erreur lors de l'ajout de la catégorie: {str(e)}")
            raise

    def get_categories(self):
        """Récupère toutes les catégories."""
        self.ensure_connection()
        query = "SELECT * FROM categories ORDER BY name"
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération des catégories: {str(e)}")
            return pd.DataFrame(columns=['id', 'name', 'description', 'created_at'])

    def add_transaction(self, date, montant, libelle, category_id, type_, projet=None, payer=False):
        """Ajoute une nouvelle transaction."""
        if not isinstance(category_id, int):
            raise ValueError("L'ID de catégorie doit être un entier")
        if not libelle:
            raise ValueError("Le libellé est obligatoire")
        if montant <= 0:
            raise ValueError("Le montant doit être supérieur à 0")
        if type_ not in ('charge', 'recette'):
            raise ValueError("Le type doit être 'charge' ou 'recette'")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Vérifie d'abord si la catégorie existe
                cur.execute("SELECT id FROM categories WHERE id = %s", (category_id,))
                if not cur.fetchone():
                    raise ValueError(f"La catégorie avec l'ID {category_id} n'existe pas")

                # Ajoute la transaction
                cur.execute("""
                    INSERT INTO transactions (date, montant, libelle, category_id, type, project, payer)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (date, montant, libelle, category_id, type_, projet, payer))
                transaction_id = cur.fetchone()[0]
                print(f"Transaction créée avec succès (ID: {transaction_id})")
                return transaction_id
        except Exception as e:
            print(f"Erreur lors de l'ajout de la transaction: {str(e)}")
            raise

    def get_transactions(self):
        """Récupère toutes les transactions avec leurs catégories."""
        self.ensure_connection()
        query = """
            SELECT t.*, c.name as category_name, p.inclus_calcul 
            FROM transactions t 
            LEFT JOIN categories c ON t.category_id = c.id 
            LEFT JOIN projects p ON t.project = p.name
            ORDER BY t.created_at DESC, t.date DESC, t.id DESC
        """
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération des transactions: {str(e)}")
            return pd.DataFrame(columns=['id', 'date', 'montant', 'libelle', 'category_name', 'type', 'project', 'payer', 'inclus_calcul'])

    def get_filtered_transactions(self, category_id=None, inclus_calcul_only=False):
        """Récupère les transactions filtrées par catégorie et statut d'inclusion."""
        self.ensure_connection()
        query = """
            SELECT t.*, c.name as category_name, p.inclus_calcul
            FROM transactions t 
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN projects p ON t.project = p.name
        """
        conditions = []
        params = []

        if category_id:
            conditions.append("t.category_id = %s")
            params.append(category_id)

        if inclus_calcul_only:
            conditions.append("p.inclus_calcul = TRUE OR t.project IS NULL")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY t.date DESC"

        try:
            return pd.read_sql(query, self.conn, params=params)
        except Exception as e:
            print(f"Erreur lors de la récupération des transactions filtrées: {str(e)}")
            return pd.DataFrame(columns=['date', 'montant', 'libelle', 'category_name', 'type', 'project', 'payer', 'inclus_calcul'])

    def get_summary_by_period(self, period='month', inclus_calcul_only=False):
        """Récupère un résumé des transactions par période."""
        self.ensure_connection()
        period_format = {
            'day': 'YYYY-MM-DD',
            'month': 'YYYY-MM',
            'year': 'YYYY'
        }
        query = f"""
            SELECT 
                TO_CHAR(t.date, '{period_format[period]}') as period,
                c.name as category_name,
                t.type,
                t.payer,
                SUM(CASE WHEN t.type = 'charge' THEN t.montant ELSE 0 END) as charges,
                SUM(CASE WHEN t.type = 'recette' THEN t.montant ELSE 0 END) as recettes
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN projects p ON t.project = p.name
            WHERE 1=1
            {" AND (p.inclus_calcul = TRUE OR t.project IS NULL)" if inclus_calcul_only else ""}
            GROUP BY period, c.name, t.type, t.payer 
            ORDER BY period, c.name
        """
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération du résumé: {str(e)}")
            return pd.DataFrame(columns=['period', 'category_name', 'type', 'payer', 'charges', 'recettes'])

    def delete_transaction(self, transaction_id):
        """Supprime une transaction."""
        if not isinstance(transaction_id, int):
            raise ValueError("L'ID de transaction doit être un entier")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM transactions WHERE id = %s RETURNING id", (transaction_id,))
                if cur.fetchone() is None:
                    raise ValueError(f"La transaction avec l'ID {transaction_id} n'existe pas")
                print(f"Transaction supprimée avec succès (ID: {transaction_id})")
        except Exception as e:
            print(f"Erreur lors de la suppression de la transaction: {str(e)}")
            raise

    def delete_category(self, category_id):
        """Supprime une catégorie si elle n'est pas utilisée."""
        if not isinstance(category_id, int):
            raise ValueError("L'ID de catégorie doit être un entier")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Vérifie si la catégorie est utilisée
                cur.execute("SELECT COUNT(*) FROM transactions WHERE category_id = %s", (category_id,))
                if cur.fetchone()[0] > 0:
                    raise ValueError("Cette catégorie ne peut pas être supprimée car elle est utilisée par des transactions")

                # Supprime la catégorie
                cur.execute("DELETE FROM categories WHERE id = %s RETURNING id", (category_id,))
                if cur.fetchone() is None:
                    raise ValueError(f"La catégorie avec l'ID {category_id} n'existe pas")
                print(f"Catégorie supprimée avec succès (ID: {category_id})")
        except Exception as e:
            print(f"Erreur lors de la suppression de la catégorie: {str(e)}")
            raise

    def verify_login(self, username, password):
        """Vérifie les identifiants de connexion."""
        self.ensure_connection()
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, username, role, full_name, email
                    FROM users
                    WHERE username = %s AND password = %s
                """, (username, hashed_password))
                user = cur.fetchone()
                if user:
                    # Mettre à jour la date de dernière connexion
                    cur.execute("""
                        UPDATE users
                        SET last_login = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (user['id'],))
                return user
        except Exception as e:
            print(f"Erreur lors de la vérification du login: {str(e)}")
            return None

    def add_project(self, name, description=None, inclus_calcul=True):
        """Ajoute un nouveau projet."""
        if not name:
            raise ValueError("Le nom du projet est obligatoire")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO projects (name, description, inclus_calcul)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (name, description, inclus_calcul))
                project_id = cur.fetchone()[0]
                print(f"Projet '{name}' créé avec succès (ID: {project_id})")
                return project_id
        except Exception as e:
            print(f"Erreur lors de l'ajout du projet: {str(e)}")
            raise

    def get_projects(self):
        """Récupère tous les projets."""
        self.ensure_connection()
        query = "SELECT * FROM projects ORDER BY name"
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération des projets: {str(e)}")
            return pd.DataFrame(columns=['id', 'name', 'description', 'created_at', 'inclus_calcul'])

    def delete_project(self, project_id):
        """Supprime un projet."""
        if not isinstance(project_id, int):
            raise ValueError("L'ID du projet doit être un entier")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Vérifie si le projet est utilisé dans des transactions
                cur.execute("SELECT COUNT(*) FROM transactions WHERE project = (SELECT name FROM projects WHERE id = %s)", (project_id,))
                if cur.fetchone()[0] > 0:
                    raise ValueError("Ce projet ne peut pas être supprimé car il est utilisé par des transactions")

                # Supprime le projet
                cur.execute("DELETE FROM projects WHERE id = %s RETURNING id", (project_id,))
                if cur.fetchone() is None:
                    raise ValueError(f"Le projet avec l'ID {project_id} n'existe pas")
                print(f"Projet supprimé avec succès (ID: {project_id})")
        except Exception as e:
            print(f"Erreur lors de la suppression du projet: {str(e)}")
            raise
    def get_project_summary(self, period='month', inclus_calcul_only=False):
        """Récupère un résumé des transactions par projet."""
        self.ensure_connection()
        period_format = {
            'day': 'YYYY-MM-DD',
            'month': 'YYYY-MM',
            'year': 'YYYY'
        }
        query = f"""
            SELECT 
                TO_CHAR(t.date, '{period_format[period]}') as period,
                t.project,
                SUM(CASE WHEN t.type = 'charge' THEN t.montant ELSE 0 END) as charges,
                SUM(CASE WHEN t.type = 'recette' THEN t.montant ELSE 0 END) as recettes,
                SUM(CASE WHEN t.type = 'recette' THEN t.montant ELSE -t.montant END) as balance
            FROM transactions t
            LEFT JOIN projects p ON t.project = p.name
            WHERE t.project IS NOT NULL
            {" AND p.inclus_calcul = TRUE" if inclus_calcul_only else ""}
            GROUP BY period, t.project
            ORDER BY period DESC, t.project
        """
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération du résumé par projet: {str(e)}")
            return pd.DataFrame(columns=['period', 'project', 'charges', 'recettes', 'balance'])

    def get_category_summary(self, period='month', inclus_calcul_only=False):
        """Récupère un résumé des transactions par catégorie."""
        self.ensure_connection()
        period_format = {
            'day': 'YYYY-MM-DD',
            'month': 'YYYY-MM',
            'year': 'YYYY'
        }
        query = f"""
            SELECT 
                TO_CHAR(t.date, '{period_format[period]}') as period,
                c.name as category_name,
                SUM(CASE WHEN t.type = 'charge' THEN t.montant ELSE 0 END) as charges,
                SUM(CASE WHEN t.type = 'recette' THEN t.montant ELSE 0 END) as recettes,
                SUM(CASE WHEN t.type = 'recette' THEN t.montant ELSE -t.montant END) as balance
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN projects p ON t.project = p.name
            WHERE 1=1
            {" AND (p.inclus_calcul = TRUE OR t.project IS NULL)" if inclus_calcul_only else ""}
            GROUP BY period, c.name
            ORDER BY period DESC, c.name
        """
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération du résumé par catégorie: {str(e)}")
            return pd.DataFrame(columns=['period', 'category_name', 'charges', 'recettes', 'balance'])

    def create_todo_table(self):
        """Crée la table todo_tasks si elle n'existe pas."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS todo_tasks (
                        id SERIAL PRIMARY KEY,
                        project_name TEXT NOT NULL,
                        due_date DATE NOT NULL,
                        description TEXT,
                        steps JSONB DEFAULT '[]'::jsonb,
                        requirements TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print("Table 'todo_tasks' créée ou déjà existante")
        except Exception as e:
            print(f"Erreur lors de la création de la table todo_tasks: {str(e)}")
            raise

    def add_todo_task(self, project_name, due_date, description=None, steps=None, requirements=None):
        """Ajoute une nouvelle tâche todo."""
        if not project_name:
            raise ValueError("Le nom du projet est obligatoire")
        if not due_date:
            raise ValueError("La date d'échéance est obligatoire")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO todo_tasks (project_name, due_date, description, steps, requirements)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                """, (project_name, due_date, description, steps or '[]', requirements))
                task_id = cur.fetchone()[0]
                print(f"Tâche '{project_name}' créée avec succès (ID: {task_id})")
                return task_id
        except Exception as e:
            print(f"Erreur lors de l'ajout de la tâche: {str(e)}")
            raise

    def get_todo_tasks(self):
        """Récupère toutes les tâches todo."""
        self.ensure_connection()
        query = """
            SELECT id, project_name, due_date, description, steps, requirements, created_at
            FROM todo_tasks
            ORDER BY due_date ASC
        """
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            print(f"Erreur lors de la récupération des tâches: {str(e)}")
            return pd.DataFrame(columns=['id', 'project_name', 'due_date', 'description', 'steps', 'requirements', 'created_at'])

    def update_todo_task(self, task_id, steps=None):
        """Met à jour les étapes d'une tâche todo."""
        if not isinstance(task_id, int):
            raise ValueError("L'ID de la tâche doit être un entier")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                updates = []
                params = []

                if steps is not None:
                    updates.append("steps = %s::jsonb")
                    params.append(steps)

                if updates:
                    query = f"""
                        UPDATE todo_tasks 
                        SET {', '.join(updates)}
                        WHERE id = %s
                        RETURNING id
                    """
                    params.append(task_id)
                    cur.execute(query, params)
                    if cur.fetchone() is None:
                        raise ValueError(f"La tâche avec l'ID {task_id} n'existe pas")
                    print(f"Tâche mise à jour avec succès (ID: {task_id})")
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la tâche: {str(e)}")
            raise

    def delete_todo_task(self, task_id):
        """Supprime une tâche todo."""
        if not isinstance(task_id, int):
            raise ValueError("L'ID de la tâche doit être un entier")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM todo_tasks WHERE id = %s RETURNING id", (task_id,))
                if cur.fetchone() is None:
                    raise ValueError(f"La tâche avec l'ID {task_id} n'existe pas")
                print(f"Tâche supprimée avec succès (ID: {task_id})")
        except Exception as e:
            print(f"Erreur lors de la suppression de la tâche: {str(e)}")
            raise

    def mark_all_transactions_as_paid(self):
        """Marque toutes les transactions comme payées."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE transactions SET payer = TRUE")
            print("Toutes les transactions ont été marquées comme payées")
        except Exception as e:
            print(f"Erreur lors de la mise à jour des transactions: {str(e)}")
            raise

    def delete_payment(self, payment_id):
        db = Database()
        query = "DELETE FROM partner_payments WHERE id = %s"
        cur = db.conn.cursor()
        cur.execute(query, (payment_id,))
        db.conn.commit()


    def get_next_invoice_sequence(self):
        """Récupère et incrémente la séquence des factures."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Créer la table de séquence si elle n'existe pas
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS invoice_sequence (
                        id INTEGER PRIMARY KEY,
                        current_value INTEGER DEFAULT 0
                    )
                """)

                # Insérer la première valeur si la table est vide
                cur.execute("""
                    INSERT INTO invoice_sequence (id, current_value)
                    SELECT 1, 0
                    WHERE NOT EXISTS (SELECT 1 FROM invoice_sequence)
                """)

                # Incrémenter et récupérer la nouvelle valeur
                cur.execute("""
                    UPDATE invoice_sequence 
                    SET current_value = current_value + 1 
                    WHERE id = 1 
                    RETURNING current_value
                """)
                return cur.fetchone()[0]
        except Exception as e:
            print(f"Erreur lors de la récupération de la séquence: {str(e)}")
            return 1

    def get_next_invoice_number(self, date):
        sequence = self.get_next_invoice_sequence()
        date_str = date.strftime("%d%m%y")
        return f"297002{date_str}{sequence:04d}"


    def add_invoice(self, invoice_number, date, client_info, lines, totals_info, pdf_data):
        """Ajoute une nouvelle facture à l'historique."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Créer la table si elle n'existe pas
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS invoices (
                        id SERIAL PRIMARY KEY,
                        invoice_number TEXT NOT NULL,
                        date DATE NOT NULL,
                        client_info JSONB NOT NULL,
                        lines JSONB NOT NULL,
                        totals_info JSONB NOT NULL,
                        pdf_data BYTEA NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Insérer la nouvelle facture
                cur.execute("""
                    INSERT INTO invoices (invoice_number, date, client_info, lines, totals_info, pdf_data)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (invoice_number, date, json.dumps(client_info), json.dumps(lines), 
                      json.dumps(totals_info), pdf_data))
                invoice_id = cur.fetchone()[0]
                print(f"Facture ajoutée avec succès (ID: {invoice_id})")
                return invoice_id
        except Exception as e:
            print(f"Erreur lors de l'ajout de la facture: {str(e)}")
            raise

    def get_invoices(self):
        """Récupère toutes les factures."""
        self.ensure_connection()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, invoice_number, date, client_info, lines, totals_info, created_at
                    FROM invoices
                    ORDER BY created_at DESC
                """)
                return cur.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des factures: {str(e)}")
            return []

    def get_invoice_pdf(self, invoice_id):
        """Récupère le PDF d'une facture."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT pdf_data FROM invoices WHERE id = %s", (invoice_id,))
                result = cur.fetchone()
                if result and result[0]:
                    # Convert memoryview to bytes
                    return bytes(result[0])
                return None
        except Exception as e:
            print(f"Erreur lors de la récupération du PDF: {str(e)}")
            return None

    def delete_invoice(self, invoice_id):
        """Supprime une facture."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM invoices WHERE id = %s RETURNING id", (invoice_id,))
                if cur.fetchone() is None:
                    raise ValueError(f"La facture avec l'ID {invoice_id} n'existe pas")
                print(f"Facture supprimée avec succès (ID: {invoice_id})")
        except Exception as e:
            print(f"Erreur lors de la suppression de la facture: {str(e)}")
            raise

    def update_project_inclusion(self, project_id, inclus_calcul):
        """Met à jour le statut d'inclusion d'un projet."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE projects
                    SET inclus_calcul = %s
                    WHERE id = %s
                """, (inclus_calcul, project_id))
                print(f"Statut d'inclusion du projet (ID: {project_id}) mis à jour avec succès")
        except Exception as e:
            print(f"Erreur lors de la mise à jour du statut d'inclusion: {str(e)}")
            raise

    def update_project_name(self, project_id, new_name):
        """Met à jour le nom d'un projet et ses références."""
        if not isinstance(project_id, int):
            raise ValueError("L'ID du projet doit être un entier")
        if not new_name:
            raise ValueError("Le nouveau nom du projet est obligatoire")

        self.ensure_connection()
        try:
            with self.conn.cursor() as cur:
                # Désactive temporairement l'autocommit pour gérer la transaction
                old_autocommit = self.conn.autocommit
                self.conn.autocommit = False

                try:
                    # Vérifie si le nouveau nom n'existe pas déjà
                    cur.execute("SELECT id FROM projects WHERE name = %s AND id != %s", (new_name, project_id))
                    if cur.fetchone():
                        raise ValueError(f"Un projet avec le nom '{new_name}' existe déjà")

                    # Récupère l'ancien nom du projet
                    cur.execute("SELECT name FROM projects WHERE id = %s", (project_id,))
                    result= cur.fetchone()
                    if not result:
                        raise ValueError(f"Le projet avec l'ID {project_id} n'existe pas")
                    old_name = result[0]

                    #Met à jour les références dans la table transactions
                    cur.execute("""
                        UPDATE transactions 
                        SET project = %s 
                        WHERE project = %s
                    """, (new_name, old_name))

                    # Met à jour le nom du projet
                    cur.execute("""
                        UPDATE projects 
                        SET name = %s 
                        WHERE id = %s
                    """, (new_name, project_id))

                    # Commit la transaction
                    self.conn.commit()
                    print(f"Nom du projet mis à jour avec succès (ID: {project_id})")
                except Exception as e:
                    # En cas d'erreur, rollback la transaction
                    self.conn.rollback()
                    raise e
                finally:
                    # Restaure l'état d'autocommit
                    self.conn.autocommit = old_autocommit
        except Exception as e:
            print(f"Erreur lors de la mise à jour du nom du projet: {str(e)}")
            raise
