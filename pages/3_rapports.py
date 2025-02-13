import streamlit as st
import pandas as pd
from database import Database
from utils import set_page_config
from datetime import datetime, timedelta
from auth.auth_decorator import require_auth

set_page_config()

@require_auth
def main():
    st.title("📊 Rapports")

    # Initialize database connection
    if 'db' not in st.session_state:
        st.session_state.db = Database()

    # Get categories for filter
    categories_df = st.session_state.db.get_categories()

    # Get projects from database
    projects_df = st.session_state.db.get_projects()
    PROJETS = ["Tous"] + projects_df['name'].tolist() if not projects_df.empty else ["Tous"]

    # Section des filtres
    st.subheader("🔍 Filtres")

    # Container pour tous les filtres
    with st.container():
        # Premier groupe de filtres (Catégorie, Projet, Statut)
        st.markdown("##### Filtres généraux")
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

        with filter_col1:
            selected_category = st.selectbox(
                "Catégorie",
                ["Toutes"] + categories_df['id'].tolist(),
                format_func=lambda x: "Toutes" if x == "Toutes" else categories_df[categories_df['id'] == x]['name'].iloc[0]
            )

        with filter_col2:
            selected_project = st.selectbox(
                "Projet",
                PROJETS
            )

        with filter_col3:
            payment_status = st.selectbox(
                "Statut de paiement",
                ["Tous", "Payé", "Non payé"]
            )

        with filter_col4:
            inclusion_status = st.selectbox(
                "Statut d'inclusion",
                ["Tous", "Inclus", "Exclus"],
                help="Filtrer les projets selon leur statut d'inclusion dans les calculs"
            )

        # Séparateur visuel
        st.markdown("---")

        # Deuxième groupe de filtres (Dates)
        st.markdown("##### Filtres de dates")

        # Dates de transaction
        st.markdown("**📅 Période de transaction**")
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            date_debut = st.date_input(
                "Du",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        with date_col2:
            date_fin = st.date_input(
                "Au",
                value=datetime.now(),
                max_value=datetime.now()
            )

        # Dates de paiement
        st.markdown("**💰 Période de paiement**")
        payment_date_col1, payment_date_col2 = st.columns(2)
        with payment_date_col1:
            payment_date_debut = st.date_input(
                "Du (paiement)",
                value=None,
                max_value=datetime.now()
            )
        with payment_date_col2:
            payment_date_fin = st.date_input(
                "Au (paiement)",
                value=None,
                max_value=datetime.now()
            )

    # Séparateur avant les résultats
    st.markdown("---")

    # Get and display data
    if selected_category == "Toutes":
        df = st.session_state.db.get_transactions()
    else:
        df = st.session_state.db.get_filtered_transactions(selected_category)

    if not df.empty:
        # Convert date columns to datetime for filtering
        df['date'] = pd.to_datetime(df['date'])
        if 'payment_date' in df.columns:
            df['payment_date'] = pd.to_datetime(df['payment_date'])

        # Apply date filter for transaction date
        mask = (df['date'].dt.date >= date_debut) & (df['date'].dt.date <= date_fin)

        # Apply payment status filter
        if payment_status != "Tous":
            mask &= df['payer'] == (payment_status == "Payé")

        # Apply payment date filter if dates are selected
        if payment_date_debut and payment_date_fin:
            mask &= (
                (df['payment_date'].notna()) & 
                (df['payment_date'].dt.date >= payment_date_debut) & 
                (df['payment_date'].dt.date <= payment_date_fin)
            )

        # Apply inclusion status filter
        if inclusion_status != "Tous":
            mask &= df['inclus_calcul'] == (inclusion_status == "Inclus")

        df = df[mask]

        # Apply project filter if not "Tous"
        if selected_project != "Tous":
            df = df[df['project'] == selected_project]

        # Prepare data for display
        df['date'] = df['date'].dt.strftime('%d/%m/%Y')
        if 'payment_date' in df.columns:
            df['payment_date'] = df['payment_date'].dt.strftime('%d/%m/%Y')

        # Suppression explicite des colonnes is_paid et paid si elles existent
        columns_to_drop = ['id', 'created_at', 'category_id', 'is_paid', 'paid']
        display_df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')

        display_df = display_df.rename(columns={
            'date': 'Date',
            'payment_date': 'Date de paiement',
            'montant': 'Montant',
            'libelle': 'Libellé',
            'category_name': 'Catégorie',
            'type': 'Type',
            'project': 'Projet',
            'payer': 'Payé',
            'inclus_calcul': 'Inclus dans les calculs'
        })

        # Convert boolean payer to Oui/Non
        display_df['Payé'] = display_df['Payé'].map({True: 'Oui', False: 'Non'})
        display_df['Inclus dans les calculs'] = display_df['Inclus dans les calculs'].map({True: 'Oui', False: 'Non'})

        # Summary statistics
        st.subheader("📈 Résumé")
        total_charges = df[df['type'] == 'charge']['montant'].sum()
        total_recettes = df[df['type'] == 'recette']['montant'].sum()
        balance = total_recettes - total_charges

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Charges", f"{total_charges:.2f} DH")
        col2.metric("Total Recettes", f"{total_recettes:.2f} DH")
        col3.metric(
            "Balance",
            f"{balance:.2f} DH",
            delta=f"{balance:.2f} DH",
            delta_color="normal" if balance > 0 else "inverse"
        )

        # Résultats détaillés
        st.subheader("📋 Résultats détaillés")

        # Initialize pagination state if not exists
        if 'rapport_page' not in st.session_state:
            st.session_state.rapport_page = 0

        # Calculate total pages (15 transactions per page)
        transactions_per_page = 15
        total_pages = (len(display_df) + transactions_per_page - 1) // transactions_per_page

        # Get current page transactions
        start_idx = st.session_state.rapport_page * transactions_per_page
        end_idx = start_idx + transactions_per_page
        page_df = display_df.iloc[start_idx:end_idx]

        # Export options
        export_col1, export_col2 = st.columns([1, 8])
        with export_col1:
            # Export button
            st.download_button(
                "📥 Exporter",
                get_csv(display_df),
                "transactions.csv",
                "text/csv",
                key='download-csv'
            )

        # Display pagination info
        st.write(f"Page {st.session_state.rapport_page + 1} sur {total_pages}")

        # Display data
        st.dataframe(page_df, use_container_width=True)

        # Navigation buttons
        col1, col2, col3 = st.columns([2, 3, 2])
        with col1:
            if st.session_state.rapport_page > 0:
                if st.button("← Page précédente"):
                    st.session_state.rapport_page -= 1
                    st.rerun()

        with col3:
            if st.session_state.rapport_page < total_pages - 1:
                if st.button("Page suivante →"):
                    st.session_state.rapport_page += 1
                    st.rerun()

    else:
        st.info("Aucune transaction trouvée pour les critères sélectionnés")

def get_csv(display_df):
    # Ensure proper ordering of columns
    columns_order = ['Date', 'Libellé', 'Montant', 'Type', 'Catégorie', 'Projet', 'Payé', 'Date de paiement', 'Inclus dans les calculs']
    export_df = display_df[columns_order]
    return export_df.to_csv(
        index=False,
        sep=';',
        encoding='utf-8-sig',
        decimal=',',
        float_format='%.2f'
    )

if __name__ == "__main__":
    main()