import streamlit as st
import pandas as pd
import datetime
from database import Database
from utils import set_page_config
import io

set_page_config()

# Vérifier si l'utilisateur est connecté
if not st.session_state.get('logged_in', False):
    st.warning("Veuillez vous connecter pour accéder à cette page")
    st.stop()

st.title("📝 Saisie des Données")

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()

# Get categories for the select box
categories_df = st.session_state.db.get_categories()
if categories_df.empty:
    st.warning("⚠️ Veuillez d'abord créer des catégories dans la section 'Gestion des Catégories'")
    st.stop()

# Liste des projets disponibles depuis la base de données
projects_df = st.session_state.db.get_projects()
PROJETS = projects_df['name'].tolist() if not projects_df.empty else []

# Fonction pour traiter le fichier Excel
def process_excel_file(df, categories_df):
    try:
        # Afficher les colonnes trouvées dans le fichier
        st.write("Colonnes trouvées dans le fichier:", list(df.columns))

        # Normaliser les noms de colonnes (enlever les accents, espaces, majuscules)
        df.columns = df.columns.str.lower().str.strip()
        df.columns = df.columns.str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')

        # Vérifier les colonnes requises
        required_columns = ['date', 'montant', 'libelle', 'type', 'projet', 'categorie', 'payer']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error("Structure attendue du fichier Excel:")
            st.code("""
            | date       | montant | libelle        | type    | projet   | categorie | payer  | date_paiement |
            |------------|---------|----------------|---------|----------|-----------|--------|---------------|
            | 31/01/2025| 100.00  | Description... | charge  | TAWSSIL  | Loyer     | oui    | 31/01/2025   |
            """)
            return False, f"Colonnes manquantes: {', '.join(missing_columns)}\nColonnes trouvées: {', '.join(df.columns)}"

        # Vérifier les types de données
        df['date'] = pd.to_datetime(df['date'])
        df['montant'] = pd.to_numeric(df['montant'])
        if 'date_paiement' in df.columns:
            df['date_paiement'] = pd.to_datetime(df['date_paiement'])

        # Vérifier les valeurs valides pour le type et le projet
        if not df['type'].isin(['charge', 'recette']).all():
            invalid_types = df[~df['type'].isin(['charge', 'recette'])]['type'].unique()
            return False, f"Types invalides trouvés: {invalid_types}. Utilisez 'charge' ou 'recette'."

        if not df['projet'].isin(PROJETS).all():
            invalid_projects = df[~df['projet'].isin(PROJETS)]['projet'].unique()
            return False, f"Projets invalides trouvés: {invalid_projects}. Utilisez: {', '.join(PROJETS)}"

        # Convertir les noms de catégories en IDs
        categories_dict = dict(zip(categories_df['name'].str.lower(), categories_df['id']))
        df['categorie'] = df['categorie'].str.lower()
        invalid_categories = df[~df['categorie'].isin(categories_dict.keys())]['categorie'].unique()
        if len(invalid_categories) > 0:
            return False, f"Catégories invalides trouvées: {invalid_categories}.\nCatégories disponibles: {', '.join(categories_df['name'])}."

        # Add payer validation
        df['payer'] = df['payer'].str.lower()
        if not df['payer'].isin(['oui', 'non']).all():
            invalid_payer = df[~df['payer'].isin(['oui', 'non'])]['payer'].unique()
            return False, f"Valeurs invalides pour 'payer' trouvées: {invalid_payer}. Utilisez 'oui' ou 'non'."

        # Convert 'oui'/'non' to boolean
        df['payer'] = df['payer'].map({'oui': True, 'non': False})

        # Validate date_paiement if present
        if 'date_paiement' in df.columns:
            # Pour les lignes où payer = True, date_paiement est obligatoire
            missing_payment_dates = df[df['payer'] & df['date_paiement'].isna()]
            if not missing_payment_dates.empty:
                return False, "Date de paiement manquante pour certaines transactions marquées comme payées"

        # Formater les données pour l'affichage
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
        if 'date_paiement' in display_df.columns:
            display_df['date_paiement'] = display_df['date_paiement'].dt.strftime('%d/%m/%Y')

        # Initialiser l'état de confirmation si nécessaire
        if 'import_confirmed' not in st.session_state:
            st.session_state.import_confirmed = False

        # Afficher l'aperçu seulement si pas encore confirmé
        if not st.session_state.import_confirmed:
            st.subheader("Aperçu des données à importer")
            st.dataframe(display_df, use_container_width=True)

            # Demander confirmation
            if st.button("Confirmer l'import des données"):
                # Insérer les données
                success_count = 0
                for _, row in df.iterrows():
                    try:
                        # Déterminer la date de paiement
                        payment_date = None
                        if row['payer']:
                            payment_date = row['date_paiement'].date() if 'date_paiement' in df.columns and pd.notna(row['date_paiement']) else row['date'].date()

                        query = """
                        INSERT INTO transactions (date, montant, libelle, category_id, type, project, payer, payment_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cur = st.session_state.db.conn.cursor()
                        cur.execute(query, (
                            row['date'].date(),
                            float(row['montant']),
                            row['libelle'],
                            categories_dict[row['categorie']],
                            row['type'],
                            row['projet'],
                            row['payer'],
                            payment_date
                        ))
                        st.session_state.db.conn.commit()
                        success_count += 1
                    except Exception as e:
                        st.warning(f"Erreur pour la ligne {_ + 2}: {str(e)}")
                        continue

                st.session_state.import_confirmed = True
                return True, f"{success_count} transactions importées avec succès sur {len(df)} au total."
        else:
            # Réinitialiser l'état après l'affichage du message de succès
            st.session_state.import_confirmed = False

        return False, "En attente de confirmation..."

    except Exception as e:
        return False, f"Erreur lors du traitement du fichier: {str(e)}"

# Section d'import Excel
st.subheader("📤 Importer depuis Excel")
with st.expander("Cliquez pour importer un fichier Excel"):
    st.markdown("""
    ### Instructions
    1. Préparez un fichier Excel avec les colonnes suivantes:
        - date (format: DD/MM/YYYY)
        - montant (nombres)
        - libelle (texte)
        - type ('charge' ou 'recette')
        - projet (TAWSSIL, TRANSPORT, CASHPLUS, HABIB, CP TAWSSIL)
        - categorie (doit correspondre aux catégories existantes)
        - payer ('oui' ou 'non')
        - date_paiement (format: DD/MM/YYYY, optionnel - utilisé si payer = 'oui')
    2. Sélectionnez votre fichier ci-dessous
    """)

    # Exemple de fichier
    st.markdown("### Exemple de structure du fichier Excel:")
    example_df = pd.DataFrame({
        'date': ['31/01/2025'],
        'montant': [100.00],
        'libelle': ['Description de la transaction'],
        'type': ['charge'],
        'projet': ['TAWSSIL'],
        'categorie': [categories_df['name'].iloc[0] if not categories_df.empty else 'Catégorie'],
        'payer': ['oui'],
        'date_paiement': ['31/01/2025']
    })
    st.dataframe(example_df)

    uploaded_file = st.file_uploader("Choisir un fichier Excel", type=['xlsx'])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            success, message = process_excel_file(df, categories_df)
            if success:
                st.success(message)
                st.rerun()
            elif message != "En attente de confirmation...":
                st.error(message)
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier: {str(e)}")

# Initialize session state variables if they don't exist
if 'form_montant' not in st.session_state:
    st.session_state.form_montant = 0.0
if 'form_libelle' not in st.session_state:
    st.session_state.form_libelle = ''

def reset_form():
    st.session_state.form_montant = 0.0
    st.session_state.form_libelle = ''

# Form for data entry
st.subheader("✍️ Saisie manuelle")
with st.form("transaction_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input(
            "Date",
            value=datetime.date.today(),
            max_value=datetime.date.today()
        )
        montant = st.number_input("Montant (DH)", 
                                min_value=0.0, 
                                step=0.01,
                                key="input_montant",
                                value=st.session_state.form_montant)

    with col2:
        type_ = st.selectbox("Type", ["charge", "recette"])
        category = st.selectbox(
            "Catégorie",
            options=categories_df['id'].tolist(),
            format_func=lambda x: categories_df[categories_df['id'] == x]['name'].iloc[0]
        )

    with col3:
        projet = st.selectbox("Projet", options=PROJETS)
        libelle = st.text_input("Libellé", 
                              key="input_libelle",
                              value=st.session_state.form_libelle)
        payer = st.selectbox("Payé", ["oui", "non"])

    submitted = st.form_submit_button("Enregistrer")

    if submitted:
        if not libelle:
            st.error("Le libellé est obligatoire.")
        elif montant <= 0:
            st.error("Le montant doit être supérieur à 0.")
        else:
            try:
                # Si le statut est "payé", utiliser la date saisie comme date de paiement
                payment_date = date if payer == "oui" else None

                # Update database query to include payment date
                query = """
                INSERT INTO transactions (date, montant, libelle, category_id, type, project, payer, payment_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur = st.session_state.db.conn.cursor()
                cur.execute(query, (
                    date,
                    montant,
                    libelle,
                    int(category),
                    type_,
                    projet,
                    payer == "oui",
                    payment_date
                ))
                st.session_state.db.conn.commit()

                # Reset form values
                reset_form()

                st.success("Transaction enregistrée avec succès!")
                st.rerun()

            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement: {str(e)}")

# Display recent transactions
st.subheader("Transactions Récentes")
df = st.session_state.db.get_transactions()

if not df.empty:
    # Add search bar
    search_term = st.text_input("🔍 Rechercher une transaction", help="Rechercher par libellé, type, ou projet")

    # Filter dataframe based on search term
    if search_term:
        mask = (
            df['libelle'].str.contains(search_term, case=False, na=False) |
            df['type'].str.contains(search_term, case=False, na=False) |
            df['project'].str.contains(search_term, case=False, na=False)
        )
        df = df[mask]

    # Initialize pagination state if not exists
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0

    # Calculate total pages
    transactions_per_page = 6
    total_pages = (len(df) + transactions_per_page - 1) // transactions_per_page

    # Get current page transactions
    start_idx = st.session_state.current_page * transactions_per_page
    end_idx = start_idx + transactions_per_page
    page_transactions = df.iloc[start_idx:end_idx]

    # Display pagination info
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        st.write(f"Page {st.session_state.current_page + 1} sur {total_pages}")

    # Pour chaque transaction de la page courante
    for idx, row in page_transactions.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
        with col1:
            st.write(f"**{row['libelle']}** ({row['category_name']})")
            st.write(f"{row['montant']} DH - {row['type']}")
        with col2:
            # Afficher la date et l'heure de création
            created_at = pd.to_datetime(row['created_at'])
            st.write(f"{created_at.strftime('%d/%m/%Y %H:%M')}")
        with col3:
            st.write(row.get('project', 'N/A'))
        with col4:
            st.write("✅" if row['payer'] else "❌")
        with col5:
            col5_1, col5_2 = st.columns(2)
            with col5_1:
                if st.button("✏️", key=f"edit_{row['id']}", help="Modifier le statut de paiement"):
                    # Store the transaction ID in session state
                    st.session_state.editing_transaction = row['id']
                    st.session_state.show_edit_modal = True

            with col5_2:
                # Afficher le bouton de suppression uniquement pour les admins
                if st.session_state.get('user_role') == 'admin':
                    if st.button("🗑️", key=f"del_trans_{row['id']}", help="Supprimer la transaction"):
                        try:
                            st.session_state.db.delete_transaction(int(row['id']))
                            st.success(f"Transaction '{row['libelle']}' supprimée avec succès!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

        # Add a divider between transactions
        st.divider()

    # Edit modal
    if st.session_state.get('show_edit_modal', False):
        with st.form(key='edit_transaction_form'):
            st.subheader("Modifier le statut de paiement")
            nouveau_statut = st.selectbox("Statut de paiement", ["oui", "non"])
            date_paiement = st.date_input(
                "Date de paiement",
                value=datetime.date.today(),
                max_value=datetime.date.today()
            )

            submit_col1, submit_col2 = st.columns(2)
            with submit_col1:
                if st.form_submit_button("Annuler"):
                    st.session_state.show_edit_modal = False
                    st.session_state.editing_transaction = None
                    st.rerun()

            with submit_col2:
                if st.form_submit_button("Enregistrer"):
                    try:
                        # Update transaction payment status and date
                        db = Database()
                        query = """
                        UPDATE transactions 
                        SET payer = %s, payment_date = %s 
                        WHERE id = %s
                        """
                        cur = db.conn.cursor()
                        cur.execute(query, (nouveau_statut == "oui", date_paiement, st.session_state.editing_transaction))
                        db.conn.commit()

                        st.success("Statut de paiement mis à jour avec succès!")
                        st.session_state.show_edit_modal = False
                        st.session_state.editing_transaction = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la mise à jour: {str(e)}")

    # Navigation buttons
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        if st.session_state.current_page > 0:
            if st.button("← Précédent"):
                st.session_state.current_page -= 1
                st.rerun()

    with col3:
        if st.session_state.current_page < total_pages - 1:
            if st.button("Suivant →"):
                st.session_state.current_page += 1
                st.rerun()
else:
    st.info("Aucune transaction enregistrée")