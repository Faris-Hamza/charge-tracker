import streamlit as st
import pandas as pd
import io # Added for Excel export
from database import Database
from datetime import datetime
from utils import set_page_config
from auth.auth_decorator import require_auth
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import landscape

set_page_config()

def load_partners():
    db = Database()
    query = "SELECT * FROM partners ORDER BY name"
    return pd.read_sql_query(query, db.conn)

def load_partner_payments():
    db = Database()
    query = """
    SELECT pp.id, pp.payment_date, pp.partner_id, pp.amount, pp.description, p.name as partner_name 
    FROM partner_payments pp 
    JOIN partners p ON pp.partner_id = p.id 
    ORDER BY pp.payment_date DESC
    """
    return pd.read_sql_query(query, db.conn)

def calculate_global_balance():
    db = Database()
    query = """
    SELECT 
        COALESCE(SUM(CASE 
            WHEN t.type = 'recette' AND t.payer = true THEN t.montant 
            ELSE 0 
        END), 0) as total_recettes_payees,
        COALESCE(SUM(CASE 
            WHEN t.type = 'recette' AND t.payer = false THEN t.montant 
            ELSE 0 
        END), 0) as total_recettes_impayees,
        COALESCE(SUM(CASE 
            WHEN t.type = 'charge' THEN t.montant 
            ELSE 0 
        END), 0) as total_depenses
    FROM transactions t
    LEFT JOIN projects p ON t.project = p.name
    WHERE p.inclus_calcul = TRUE OR t.project IS NULL
    """
    df = pd.read_sql_query(query, db.conn)
    return df

def calculate_partner_investments():
    db = Database()
    query = """
    SELECT 
        p.id,
        p.name,
        p.share_percentage,
        COALESCE(SUM(ti.montant), 0) as total_investi
    FROM partners p
    LEFT JOIN transactions_investissement ti ON p.id = ti.associe_id
    GROUP BY p.id, p.name, p.share_percentage
    ORDER BY p.name
    """
    return pd.read_sql_query(query, db.conn)

def save_payment(partner_id, amount, description):
    db = Database()
    query = """
    INSERT INTO partner_payments (partner_id, amount, description)
    VALUES (%s, %s, %s)
    """
    cur = db.conn.cursor()
    cur.execute(query, (partner_id, amount, description))
    db.conn.commit()

def delete_payment(payment_id):
    db = Database()
    query = "DELETE FROM partner_payments WHERE id = %s"
    cur = db.conn.cursor()
    cur.execute(query, (payment_id,))
    db.conn.commit()

@require_auth
def main():
    st.title("💰 Situation Financière des Associés")

    # Charger les données
    partners_df = load_partners()
    payments_df = load_partner_payments()
    balance_df = calculate_global_balance()
    investments_df = calculate_partner_investments()

    # Afficher le bilan global
    st.header("📊 Bilan Global des Projets")
    total_recettes_payees = balance_df['total_recettes_payees'].iloc[0]
    total_recettes_impayees = balance_df['total_recettes_impayees'].iloc[0]
    total_recettes_global = total_recettes_payees + total_recettes_impayees
    total_depenses = balance_df['total_depenses'].iloc[0]
    total_balance = total_recettes_payees - total_depenses
    balance_global = total_recettes_global - total_depenses

    # Première ligne : Totaux globaux (incluant les recettes impayées)
    st.markdown("##### 💹 Totaux Globaux")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Recettes Global",
            f"{total_recettes_global:,.2f} DH",
            delta=None
        )
    with col2:
        st.metric(
            "Total Charges Global",
            f"{total_depenses:,.2f} DH",
            delta=None
        )
    with col3:
        st.metric(
            "Balance Globale",
            f"{balance_global:,.2f} DH",
            delta=f"{balance_global:,.2f} DH",
            delta_color="normal" if balance_global > 0 else "inverse"
        )

    # Séparateur
    st.markdown("---")

    # Deuxième ligne : Totaux effectifs (uniquement les recettes payées)
    st.markdown("##### 💰 Totaux Effectifs")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Recettes Payées",
            f"{total_recettes_payees:,.2f} DH",
            delta=None
        )
    with col2:
        st.metric(
            "Total Charges",
            f"{total_depenses:,.2f} DH",
            delta=None
        )
    with col3:
        st.metric(
            "Balance Nette",
            f"{total_balance:,.2f} DH",
            delta=f"{total_balance:,.2f} DH",
            delta_color="normal" if total_balance > 0 else "inverse"
        )

    # Séparateur
    st.markdown("---")

    # Tableau détaillé de répartition
    st.header("📈 Tableau de Répartition Détaillé")

    # Créer un DataFrame pour le tableau de répartition
    repartition_data = []

    for _, partner in partners_df.iterrows():
        # Calculer les parts des bénéfices
        share_percentage = partner['share_percentage'] / 100
        benefices_payes = (total_recettes_payees - total_depenses) * share_percentage
        benefices_a_recevoir = total_recettes_impayees * share_percentage
        total_benefices = benefices_payes + benefices_a_recevoir  # Nouveau calcul: somme des bénéfices

        # Obtenir les investissements et paiements
        partner_investments = investments_df[investments_df['id'] == partner['id']]['total_investi'].iloc[0]
        partner_payments = payments_df[payments_df['partner_id'] == partner['id']]['amount'].sum() if not payments_df.empty else 0
        remaining_payment = benefices_payes - partner_payments
        remaining_treasury = benefices_payes + partner_investments - partner_payments  # Modification ici: utilisation de benefices_payes au lieu de total_benefices

        repartition_data.append({
            'Associé': partner['name'],
            'Part des bénéfices (payés)': f"{benefices_payes:,.2f} DH",
            'Part des bénéfices (à recevoir)': f"{benefices_a_recevoir:,.2f} DH",
            'Total des bénéfices': f"{total_benefices:,.2f} DH",
            'Total investissements': f"{partner_investments:,.2f} DH",
            'Montant payé': f"{partner_payments:,.2f} DH",
            'Reste à payer': f"{remaining_payment:,.2f} DH",
            'Reste à payer (Trésorerie)': f"{remaining_treasury:,.2f} DH"
        })

    # Créer le DataFrame
    repartition_df = pd.DataFrame(repartition_data)

    # Boutons d'export
    col1, col2 = st.columns([1, 8])
    with col1:
        # Export to CSV
        csv_data = repartition_df.to_csv(index=False)
        st.download_button(
            label="📥 CSV",
            data=csv_data,
            file_name="repartition.csv",
            mime="text/csv"
        )
    with col2:
        # Export to Excel
        buffer = io.BytesIO()
        repartition_df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        st.download_button(
            label="📥 Excel",
            data=buffer,
            file_name="repartition.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Afficher le tableau de répartition
    st.dataframe(repartition_df, use_container_width=True)

    # Graphique de répartition des montants payés
    st.header("🥧 Répartition des Montants Payés")

    # Préparer les données pour le graphique
    total_benefices = total_recettes_payees - total_depenses
    total_payments = payments_df['amount'].sum() if not payments_df.empty else 0
    montant_restant = total_benefices - total_payments

    # Créer la liste des données pour le graphique
    partners_payments = []
    for _, partner in partners_df.iterrows():
        payment = payments_df[payments_df['partner_id'] == partner['id']]['amount'].sum() if not payments_df.empty else 0
        partners_payments.append({
            'name': partner['name'],
            'payment': payment
        })

    # Données pour le graphique
    labels = [p['name'] for p in partners_payments] + ['Reste à distribuer']
    values = [p['payment'] for p in partners_payments] + [montant_restant]

    # Créer le graphique avec plotly
    import plotly.graph_objects as go

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        textinfo='label+percent',
        textposition='inside',
        hovertemplate="<b>%{label}</b><br>" +
                      "Montant: %{value:,.2f} DH<br>" +
                      "<extra></extra>"
    )])

    fig.update_layout(
        title=f"Total des bénéfices: {total_benefices:,.2f} DH | Montant distribué: {total_payments:,.2f} DH",
        showlegend=True,
        width=800,
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    # Afficher le graphique
    st.plotly_chart(fig, use_container_width=True)

    # Nouvelle section: Ancienne méthode de calcul
    st.header("📊 Ancienne Méthode de Calcul")

    # Préparer les données pour le tableau
    abderrahim_investment = investments_df[investments_df['name'] == 'EL AZZAOUY ABDERRAHIM']['total_investi'].iloc[0] if not investments_df.empty else 0
    mohamed_investment = investments_df[investments_df['name'].str.contains('MOHAMED LAHBIB', na=False)]['total_investi'].iloc[0] if not investments_df.empty else 0
    total_investment = abderrahim_investment + mohamed_investment

    # Balance des opérations (0 pour Abderrahim, total balance pour Mohamed Lahbib)
    balance_operations = total_balance  # Using the total_balance calculated earlier

    # Calculer les différences
    abderrahim_diff = 0 - abderrahim_investment  # Car balance est 0 pour Abderrahim
    mohamed_diff = balance_operations - mohamed_investment
    total_diff = balance_operations - total_investment

    # Montants payés
    abderrahim_paid = payments_df[payments_df['partner_name'] == 'EL AZZAOUY ABDERRAHIM']['amount'].sum() if not payments_df.empty else 0
    mohamed_paid = payments_df[payments_df['partner_name'].str.contains('MOHAMED LAHBIB', na=False)]['amount'].sum() if not payments_df.empty else 0
    total_paid = abderrahim_paid + mohamed_paid

    # Décaissements (inverse du montant payé de l'autre associé)
    abderrahim_decaissement = -mohamed_paid  # L'inverse du montant payé par Mohamed
    mohamed_decaissement = -abderrahim_paid  # L'inverse du montant payé par Abderrahim
    total_decaissement = -(abderrahim_paid + mohamed_paid)  # Total des décaissements

    # Encaissements
    abderrahim_encaissement = abderrahim_diff + abderrahim_paid + abderrahim_decaissement
    mohamed_encaissement = mohamed_diff + mohamed_paid + mohamed_decaissement
    total_encaissement = total_diff + total_paid + total_decaissement

    # Répartition trésorerie
    repartition = (balance_operations - total_investment) / 2

    # Reste
    abderrahim_reste = repartition - abderrahim_encaissement
    mohamed_reste = repartition - mohamed_encaissement
    total_reste = (repartition * 2) - total_encaissement

    # Créer le DataFrame pour le tableau
    old_method_data = {
        'Associé': ['EL AZZAOUY ABDERRAHIM', 'EL AZZOUY MOHAMED LAHBIB ET STE', 'TOTAL'],
        'Investissement': [abderrahim_investment, mohamed_investment, total_investment],
        'Balance des Opérations': [0, balance_operations, balance_operations],  # Mise à 0 pour Abderrahim
        'Différence': [abderrahim_diff, mohamed_diff, total_diff],
        'Montant Payé': [abderrahim_paid, mohamed_paid, total_paid],
        'Décaissement': [abderrahim_decaissement, mohamed_decaissement, total_decaissement],  # Nouvelle colonne
        'Encaissement': [abderrahim_encaissement, mohamed_encaissement, total_encaissement],
        'Répartition Trésorerie': [repartition, repartition, repartition * 2],
        'Reste': [abderrahim_reste, mohamed_reste, total_reste]
    }

    old_method_df = pd.DataFrame(old_method_data)

    # Formatage des colonnes numériques
    numeric_cols = old_method_df.columns.difference(['Associé'])
    old_method_df[numeric_cols] = old_method_df[numeric_cols].map(lambda x: f"{x:,.2f} DH")

    # Afficher le tableau
    st.dataframe(old_method_df, use_container_width=True)

    # Export buttons for old method table
    col1, col2 = st.columns(2)

    # Excel export
    with col1:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            old_method_df.to_excel(writer, sheet_name='Ancienne Méthode', index=False)
        excel_data = excel_buffer.getvalue()
        st.download_button(
            label="📥 Télécharger en Excel",
            data=excel_data,
            file_name="ancienne_methode_calcul.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # PDF export
    with col2:
        def create_old_method_pdf(df):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(letter),
                rightMargin=20,
                leftMargin=20,
                topMargin=20,
                bottomMargin=20
            )
            elements = []

            # Calculer les largeurs des colonnes
            col_widths = [150]  # Largeur pour la colonne Associé
            data_widths = [80] * (len(df.columns) - 1)  # Largeur uniforme pour les autres colonnes
            col_widths.extend(data_widths)

            # Convertir DataFrame en liste pour le tableau PDF
            data = [df.columns.tolist()]
            data.extend(df.values.tolist())

            # Créer le tableau
            t = Table(data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ]))
            elements.append(t)
            doc.build(elements)
            return buffer.getvalue()

        pdf_data = create_old_method_pdf(old_method_df)
        st.download_button(
            label="📥 Télécharger en PDF",
            data=pdf_data,
            file_name="ancienne_methode_calcul.pdf",
            mime="application/pdf",
        )

    # Section existante de répartition par associé
    st.header("💼 Répartition par Associé")
    col1, col2 = st.columns(2)
    for idx, partner in partners_df.iterrows():
        with col1 if idx % 2 == 0 else col2:
            partner_share = total_balance * (partner['share_percentage'] / 100)
            partner_payments = payments_df[payments_df['partner_id'] == partner['id']]['amount'].sum() if not payments_df.empty else 0
            remaining = partner_share - partner_payments

            st.subheader(partner['name'])
            st.write(f"Part des bénéfices (🔄): {partner_share:,.2f} DH")
            st.write(f"Montant payé (✅): {partner_payments:,.2f} DH")
            st.write(f"Reste à payer (💰): {remaining:,.2f} DH")

    # Formulaire de saisie des paiements
    st.header("📝 Enregistrer un Nouveau Paiement")
    with st.form("payment_form"):
        partner_id = st.selectbox(
            "Associé",
            options=partners_df['id'].tolist(),
            format_func=lambda x: partners_df[partners_df['id'] == x]['name'].iloc[0]
        )
        amount = st.number_input("Montant (DH)", min_value=0.0, step=1000.0)
        description = st.text_area("Description", placeholder="Détails du paiement...")
        submitted = st.form_submit_button("Enregistrer le Paiement")

        if submitted:
            if amount <= 0:
                st.error("Le montant doit être supérieur à 0")
            else:
                save_payment(partner_id, amount, description)
                st.success("Paiement enregistré avec succès!")
                st.rerun()

    # Historique des paiements
    st.header("📔 Historique des Paiements")
    if not payments_df.empty:
        payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date']).dt.strftime('%d/%m/%Y')

        # Pagination
        items_per_page = 5
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 0

        total_pages = len(payments_df) // items_per_page + (1 if len(payments_df) % items_per_page > 0 else 0)
        start_idx = st.session_state.current_page * items_per_page
        end_idx = start_idx + items_per_page

        # Afficher les entrées de la page courante
        page_payments = payments_df.iloc[start_idx:end_idx]

        for idx, payment in page_payments.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 3, 1])
                with col1:
                    st.write(payment['payment_date'])
                with col2:
                    st.write(payment['partner_name'])
                with col3:
                    st.write(f"{payment['amount']:,.2f} DH")
                with col4:
                    st.write(payment['description'])
                with col5:
                    if st.button("🗑️", key=f"delete_{payment['id']}", help="Supprimer ce paiement"):
                        if st.session_state.get(f"confirm_delete_{payment['id']}", False):
                            delete_payment(payment['id'])
                            st.success("Paiement supprimé avec succès!")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_{payment['id']}"] = True
                            st.warning("Cliquez à nouveau pour confirmer la suppression")
                st.divider()

        # Boutons de pagination
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Précédent", disabled=st.session_state.current_page == 0):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.current_page + 1} sur {total_pages}")
        with col3:
            if st.button("Suivant ▶️", disabled=st.session_state.current_page >= total_pages - 1):
                st.session_state.current_page += 1
                st.rerun()
    else:
        st.info("Aucun paiement enregistré pour le moment")

if __name__ == "__main__":
    main()