import streamlit as st
import pandas as pd
from database import Database
from datetime import datetime
from utils import set_page_config
from auth.auth_decorator import require_auth
import io

set_page_config()

def load_immobilisations():
    db = Database()
    query = """
    SELECT i.*, 
           COALESCE(SUM(ti.montant), 0) as montant_investi,
           STRING_AGG(DISTINCT p.name, ', ') as investisseurs
    FROM immobilisations i
    LEFT JOIN transactions_investissement ti ON i.id = ti.immobilisation_id
    LEFT JOIN partners p ON ti.associe_id = p.id
    GROUP BY i.id, i.nom, i.description, i.prix_total, i.date_acquisition, i.created_at
    ORDER BY i.created_at DESC
    """
    return pd.read_sql_query(query, db.conn)

def load_transactions_investissement():
    db = Database()
    query = """
    SELECT ti.*, i.nom as immobilisation_nom, p.name as associe_nom
    FROM transactions_investissement ti
    JOIN immobilisations i ON ti.immobilisation_id = i.id
    JOIN partners p ON ti.associe_id = p.id
    ORDER BY ti.created_at DESC
    """
    return pd.read_sql_query(query, db.conn)

def calculate_investissements_par_associe():
    db = Database()
    query = """
    SELECT 
        p.id,
        p.name,
        COALESCE(SUM(ti.montant), 0) as total_investi
    FROM partners p
    LEFT JOIN transactions_investissement ti ON p.id = ti.associe_id
    GROUP BY p.id, p.name
    ORDER BY p.name
    """
    return pd.read_sql_query(query, db.conn)

def save_immobilisation(nom, description, prix_total, date_acquisition):
    db = Database()
    query = """
    INSERT INTO immobilisations (nom, description, prix_total, date_acquisition)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """
    cur = db.conn.cursor()
    cur.execute(query, (nom, description, prix_total, date_acquisition))
    immobilisation_id = cur.fetchone()[0]
    db.conn.commit()
    return immobilisation_id

def save_transaction_investissement(associe_id, immobilisation_id, montant, description):
    db = Database()
    query = """
    INSERT INTO transactions_investissement (associe_id, immobilisation_id, montant, description)
    VALUES (%s, %s, %s, %s)
    """
    cur = db.conn.cursor()
    cur.execute(query, (associe_id, immobilisation_id, montant, description))
    db.conn.commit()

def delete_transaction(transaction_id):
    db = Database()
    query = "DELETE FROM transactions_investissement WHERE id = %s"
    cur = db.conn.cursor()
    cur.execute(query, (transaction_id,))
    db.conn.commit()

def load_partners():
    db = Database()
    query = "SELECT * FROM partners ORDER BY name"
    return pd.read_sql_query(query, db.conn)

@require_auth
def main():
    st.title("💼 Investissements des Associés")

    # Charger les données
    partners_df = load_partners()
    investissements_df = calculate_investissements_par_associe()
    immobilisations_df = load_immobilisations()
    transactions_df = load_transactions_investissement()

    # Calculer et afficher le total des investissements
    total_investissements = investissements_df['total_investi'].sum()
    st.header("💰 Total des Investissements")
    st.metric(
        "Total des investissements des associés",
        f"{total_investissements:,.2f} DH",
        help="Somme totale des investissements de tous les associés"
    )

    # Séparateur
    st.markdown("---")

    # Afficher le bilan des investissements
    st.header("📊 Bilan des Investissements")
    
    # Calculer le total des investissements
    investissement_moyen = total_investissements / len(partners_df) if len(partners_df) > 0 else 0

    # Afficher les investissements par associé
    col1, col2 = st.columns(2)
    for idx, row in investissements_df.iterrows():
        with col1 if idx % 2 == 0 else col2:
            difference = row['total_investi'] - investissement_moyen
            st.subheader(row['name'])
            st.write(f"Total investi: {row['total_investi']:,.2f} DH")
            if difference < 0:
                st.warning(f"Doit investir: {abs(difference):,.2f} DH pour équilibrer")
            elif difference > 0:
                st.success(f"A investi en plus: {difference:,.2f} DH")

    # Formulaire d'ajout d'immobilisation
    st.header("📝 Ajouter un Investissement")
    with st.form("immobilisation_form"):
        nom = st.text_input("Nom de l'investissement")
        description = st.text_area("Description")
        prix_total = st.number_input("Prix Total (DH)", min_value=0.0, step=1000.0)
        date_acquisition = st.date_input(
            "Date d'acquisition",
            value=datetime.now().date(),
            format="DD/MM/YYYY"
        )

        col1, col2 = st.columns(2)
        with col1:
            associe1 = st.selectbox(
                "Premier Investisseur",
                options=partners_df['id'].tolist(),
                format_func=lambda x: partners_df[partners_df['id'] == x]['name'].iloc[0]
            )
            montant1 = st.number_input("Montant Investi (DH)", min_value=0.0, step=1000.0, key="montant1")

        with col2:
            associe2 = st.selectbox(
                "Deuxième Investisseur",
                options=partners_df['id'].tolist(),
                format_func=lambda x: partners_df[partners_df['id'] == x]['name'].iloc[0]
            )
            montant2 = st.number_input("Montant Investi (DH)", min_value=0.0, step=1000.0, key="montant2")

        submitted = st.form_submit_button("Enregistrer l'Investissement")

        if submitted:
            if not nom:
                st.error("Le nom de l'immobilisation est requis")
            elif prix_total <= 0:
                st.error("Le prix total doit être supérieur à 0")
            elif montant1 + montant2 != prix_total:
                st.error("La somme des montants investis doit être égale au prix total")
            else:
                immobilisation_id = save_immobilisation(nom, description, prix_total, date_acquisition)
                if montant1 > 0:
                    save_transaction_investissement(associe1, immobilisation_id, montant1, f"Investissement initial - {nom}")
                if montant2 > 0:
                    save_transaction_investissement(associe2, immobilisation_id, montant2, f"Investissement initial - {nom}")
                st.success("Investissement enregistré avec succès!")
                st.rerun()

    # Tableau des immobilisations
    st.header("📋 Liste des Investissements")
    if not immobilisations_df.empty:
        # Export buttons
        col1, col2 = st.columns([1, 8])
        with col1:
            # Export to CSV
            csv_data = immobilisations_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv_data,
                file_name="immobilisations.csv",
                mime="text/csv"
            )
        with col2:
            # Export to PDF
            buffer = io.BytesIO()
            immobilisations_df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            st.download_button(
                label="📥 Excel",
                data=buffer,
                file_name="immobilisations.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Pagination for immobilisations
        items_per_page = 5
        if 'immob_page' not in st.session_state:
            st.session_state.immob_page = 0

        total_pages = len(immobilisations_df) // items_per_page + (1 if len(immobilisations_df) % items_per_page > 0 else 0)
        start_idx = st.session_state.immob_page * items_per_page
        end_idx = start_idx + items_per_page

        # Display current page items
        page_immobs = immobilisations_df.iloc[start_idx:end_idx]

        for _, immob in page_immobs.iterrows():
            with st.expander(f"{immob['nom']} - {immob['prix_total']:,.2f} DH"):
                st.write(f"Description: {immob['description']}")
                st.write(f"Date d'acquisition: {pd.to_datetime(immob['date_acquisition']).strftime('%d/%m/%Y')}")
                st.write(f"Date de création: {pd.to_datetime(immob['created_at']).strftime('%d/%m/%Y')}")
                st.write(f"Montant investi: {immob['montant_investi']:,.2f} DH")
                st.write(f"Investisseurs: {immob['investisseurs']}")

        # Pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Précédent", key="prev_immob", disabled=st.session_state.immob_page == 0):
                st.session_state.immob_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.immob_page + 1} sur {total_pages}")
        with col3:
            if st.button("Suivant ▶️", key="next_immob", disabled=st.session_state.immob_page >= total_pages - 1):
                st.session_state.immob_page += 1
                st.rerun()
    else:
        st.info("Aucune immobilisation enregistrée")

    # Historique des transactions
    st.header("📔 Historique des Transactions")
    if not transactions_df.empty:
        # Export buttons for transactions
        col1, col2 = st.columns([1, 8])
        with col1:
            # Export to CSV
            csv_data = transactions_df.to_csv(index=False)
            st.download_button(
                label="📥 CSV",
                data=csv_data,
                file_name="transactions.csv",
                mime="text/csv",
                key="trans_csv"
            )
        with col2:
            # Export to Excel
            buffer = io.BytesIO()
            transactions_df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            st.download_button(
                label="📥 Excel",
                data=buffer,
                file_name="transactions.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="trans_excel"
            )

        transactions_df['date_transaction'] = pd.to_datetime(transactions_df['date_transaction']).dt.strftime('%d/%m/%Y')

        # Pagination for transactions
        items_per_page = 5
        if 'trans_page' not in st.session_state:
            st.session_state.trans_page = 0

        total_pages = len(transactions_df) // items_per_page + (1 if len(transactions_df) % items_per_page > 0 else 0)
        start_idx = st.session_state.trans_page * items_per_page
        end_idx = start_idx + items_per_page

        # Display current page transactions
        page_transactions = transactions_df.iloc[start_idx:end_idx]

        for idx, trans in page_transactions.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 3, 1])
                with col1:
                    st.write(trans['date_transaction'])
                with col2:
                    st.write(trans['associe_nom'])
                with col3:
                    st.write(f"{trans['montant']:,.2f} DH")
                with col4:
                    st.write(f"{trans['immobilisation_nom']} - {trans['description']}")
                with col5:
                    if st.button("🗑️", key=f"delete_{trans['id']}", help="Supprimer cette transaction"):
                        if st.session_state.get(f"confirm_delete_{trans['id']}", False):
                            delete_transaction(trans['id'])
                            st.success("Transaction supprimée avec succès!")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{trans['id']}"] = True
                            st.warning("Cliquez à nouveau pour confirmer la suppression")
                st.divider()

        # Pagination controls for transactions
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Précédent", key="prev_trans", disabled=st.session_state.trans_page == 0):
                st.session_state.trans_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.trans_page + 1} sur {total_pages}")
        with col3:
            if st.button("Suivant ▶️", key="next_trans", disabled=st.session_state.trans_page >= total_pages - 1):
                st.session_state.trans_page += 1
                st.rerun()
    else:
        st.info("Aucune transaction enregistrée")

if __name__ == "__main__":
    main()