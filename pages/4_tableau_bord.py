import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from database import Database
from utils import set_page_config, create_time_series
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import io
from auth.auth_decorator import require_auth

set_page_config()

@require_auth
def main():
    st.title("📈 Tableau de Bord")

    # Initialize database connection
    if 'db' not in st.session_state:
        st.session_state.db = Database()

    # Period selector
    period = st.selectbox(
        "Période d'analyse",
        ["day", "month", "year"],
        format_func=lambda x: {
            "day": "Journalière",
            "month": "Mensuelle",
            "year": "Annuelle"
        }[x]
    )

    # Option pour filtrer les calculs
    inclure_tous_projets = st.checkbox(
        "Inclure tous les projets",
        value=False,
        help="Si décoché, seuls les projets marqués comme 'inclus dans les calculs' seront pris en compte"
    )

    # Modifier la récupération des données pour prendre en compte le filtre
    df_summary = st.session_state.db.get_summary_by_period(period, not inclure_tous_projets)
    df_project_summary = st.session_state.db.get_project_summary(period, not inclure_tous_projets)
    df_category_summary = st.session_state.db.get_category_summary(period, not inclure_tous_projets)

    if not df_summary.empty:
        # Global summary metrics
        st.subheader("📊 Résumé Global")

        # Calculer les totaux généraux
        total_charges = df_summary[df_summary['type'] == 'charge']['charges'].sum() if not df_summary.empty else 0
        total_recettes = df_summary[df_summary['type'] == 'recette']['recettes'].sum() if not df_summary.empty else 0
        balance = total_recettes - total_charges

        # Afficher les totaux généraux
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Total Charges",
            f"{total_charges:,.2f} DH"
        )
        col2.metric(
            "Total Recettes",
            f"{total_recettes:,.2f} DH"
        )
        col3.metric(
            "Balance Globale",
            f"{balance:,.2f} DH",
            delta=f"{balance:,.2f} DH",
            delta_color="normal" if balance > 0 else "inverse"
        )

        # Séparateur
        st.markdown("---")

        # Détail des charges
        st.markdown("##### 💸 Détail des Charges")
        charges_col1, charges_col2, charges_col3 = st.columns(3)

        # Calculer les charges payées et non payées
        charges_payees = df_summary[(df_summary['type'] == 'charge') & (df_summary['payer'])]['charges'].sum() if not df_summary.empty else 0
        charges_non_payees = df_summary[(df_summary['type'] == 'charge') & (~df_summary['payer'])]['charges'].sum() if not df_summary.empty else 0
        total_charges = charges_payees + charges_non_payees

        charges_col1.metric(
            "Charges Payées",
            f"{charges_payees:,.2f} DH"
        )
        charges_col2.metric(
            "Charges Non Payées",
            f"{charges_non_payees:,.2f} DH"
        )
        charges_col3.metric(
            "Total Charges",
            f"{total_charges:,.2f} DH",
            delta=None
        )

        # Séparateur
        st.markdown("---")

        # Détail des recettes
        st.markdown("##### 💰 Détail des Recettes")
        recettes_col1, recettes_col2, recettes_col3 = st.columns(3)

        # Calculer les recettes payées et non payées
        recettes_payees = df_summary[(df_summary['type'] == 'recette') & (df_summary['payer'])]['recettes'].sum() if not df_summary.empty else 0
        recettes_non_payees = df_summary[(df_summary['type'] == 'recette') & (~df_summary['payer'])]['recettes'].sum() if not df_summary.empty else 0
        total_recettes = recettes_payees + recettes_non_payees

        recettes_col1.metric(
            "Recettes Encaissées",
            f"{recettes_payees:,.2f} DH"
        )
        recettes_col2.metric(
            "Recettes Non Encaissées",
            f"{recettes_non_payees:,.2f} DH"
        )
        recettes_col3.metric(
            "Total Recettes",
            f"{total_recettes:,.2f} DH",
            delta=None
        )

        # Séparateur avant le graphique d'évolution
        st.markdown("---")

        # Global evolution chart
        st.plotly_chart(
            create_time_series(
                df_summary,
                f"Évolution Globale - Vue {period}"
            ),
            use_container_width=True
        )

        # Project summary
        st.subheader("📌 Analyse par Projet")
        if not df_project_summary.empty:
            # Créer et afficher le tableau des totaux par projet et période
            project_period_table = df_project_summary.pivot_table(
                values=['charges', 'recettes', 'balance'],
                index=['period'],
                columns=['project'],
                aggfunc='sum',
                fill_value=0
            ).sort_index(ascending=False).round(2)

            # Pagination pour le tableau des projets
            transactions_per_page = 10

            # Initialize pagination state if not exists
            if 'project_page' not in st.session_state:
                st.session_state.project_page = 0

            # Calculate total pages
            total_pages = (len(project_period_table) + transactions_per_page - 1) // transactions_per_page

            # Get current page data
            start_idx = st.session_state.project_page * transactions_per_page
            end_idx = start_idx + transactions_per_page
            current_page_data = project_period_table.iloc[start_idx:end_idx]

            # Formatage des colonnes pour l'affichage
            st.write("Totaux par projet et période:")
            st.dataframe(
                current_page_data.style.format("{:,.2f} DH"),
                use_container_width=True
            )

            # Pagination controls
            col1, col2, col3 = st.columns([2, 3, 2])
            with col2:
                st.write(f"Page {st.session_state.project_page + 1} sur {total_pages}")

            with col1:
                if st.session_state.project_page > 0:
                    if st.button("← Page précédente", key="prev_project"):
                        st.session_state.project_page -= 1
                        st.rerun()

            with col3:
                if st.session_state.project_page < total_pages - 1:
                    if st.button("Page suivante →", key="next_project"):
                        st.session_state.project_page += 1
                        st.rerun()
            # Export buttons for project table
            col1, col2 = st.columns(2)

            # Excel export
            with col1:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    project_period_table.to_excel(writer, sheet_name='Analyse par Projet')
                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="📥 Télécharger en Excel",
                    data=excel_data,
                    file_name=f"analyse_projets_{period}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # PDF export
            with col2:
                def create_pdf(df):
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

                    # Calculer les largeurs des colonnes basées sur le contenu
                    col_widths = [100]  # Largeur fixe pour la première colonne (période)
                    data_widths = [80] * (len(df.columns))  # Largeur uniforme pour les colonnes de données
                    col_widths.extend(data_widths)

                    # Convert DataFrame to list of lists for PDF table
                    data = [['Période'] + [str(col) for col in df.columns.tolist()]]
                    for idx, row in df.iterrows():
                        data.append([str(idx)] + [f"{val:,.2f} DH" for val in row.values])

                    # Create the table with specified column widths
                    t = Table(data, colWidths=col_widths)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),  # Taille réduite pour l'en-tête
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),  # Taille réduite pour le contenu
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Aligner les montants à droite
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    elements.append(t)

                    # Build the PDF
                    doc.build(elements)
                    return buffer.getvalue()

                pdf_data = create_pdf(project_period_table)
                st.download_button(
                    label="📥 Télécharger en PDF",
                    data=pdf_data,
                    file_name=f"analyse_projets_{period}.pdf",
                    mime="application/pdf",
                )

            # Create a bar chart for projects
            fig_projects = go.Figure()

            # Add bars for charges
            fig_projects.add_trace(go.Bar(
                name='Charges',
                x=df_project_summary['project'].unique(),
                y=df_project_summary.groupby('project')['charges'].sum(),
                marker_color='red',
                opacity=0.7
            ))

            # Add bars for recettes
            fig_projects.add_trace(go.Bar(
                name='Recettes',
                x=df_project_summary['project'].unique(),
                y=df_project_summary.groupby('project')['recettes'].sum(),
                marker_color='green',
                opacity=0.7
            ))

            fig_projects.update_layout(
                barmode='group',
                title=f"Répartition par Projet",
                xaxis_title="Projet",
                yaxis_title="Montant (DH)",
                height=400
            )

            st.plotly_chart(fig_projects, use_container_width=True)

            # Detailed project metrics
            for idx, row in df_project_summary.groupby('project').agg({
                'charges': 'sum',
                'recettes': 'sum',
                'balance': 'sum'
            }).reset_index().iterrows():
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    f"{row['project']} - Charges",
                    f"{row['charges']:,.2f} DH"
                )
                col2.metric(
                    f"{row['project']} - Recettes",
                    f"{row['recettes']:,.2f} DH"
                )
                col3.metric(
                    f"{row['project']} - Balance",
                    f"{row['balance']:,.2f} DH",
                    delta=f"{row['balance']:,.2f} DH",
                    delta_color="normal" if row['balance'] > 0 else "inverse"
                )

        # Category summary
        st.subheader("🏷️ Analyse par Catégorie")
        if not df_category_summary.empty:
            # Créer et afficher le tableau des totaux par catégorie et période
            category_period_table = df_category_summary.pivot_table(
                values=['charges', 'recettes', 'balance'],
                index=['period'],
                columns=['category_name'],
                aggfunc='sum',
                fill_value=0
            ).sort_index(ascending=False).round(2)

            # Pagination pour le tableau des catégories
            if 'category_page' not in st.session_state:
                st.session_state.category_page = 0

            # Calculate total pages
            total_pages = (len(category_period_table) + transactions_per_page - 1) // transactions_per_page

            # Get current page data
            start_idx = st.session_state.category_page * transactions_per_page
            end_idx = start_idx + transactions_per_page
            current_page_data = category_period_table.iloc[start_idx:end_idx]

            # Formatage des colonnes pour l'affichage
            st.write("Totaux par catégorie et période:")
            st.dataframe(
                current_page_data.style.format("{:,.2f} DH"),
                use_container_width=True
            )

            # Pagination controls for categories
            col1, col2, col3 = st.columns([2, 3, 2])
            with col2:
                st.write(f"Page {st.session_state.category_page + 1} sur {total_pages}")

            with col1:
                if st.session_state.category_page > 0:
                    if st.button("← Page précédente", key="prev_category"):
                        st.session_state.category_page -= 1
                        st.rerun()

            with col3:
                if st.session_state.category_page < total_pages - 1:
                    if st.button("Page suivante →", key="next_category"):
                        st.session_state.category_page += 1
                        st.rerun()

            # Export buttons for category table
            col1, col2 = st.columns(2)

            # Excel export
            with col1:
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    category_period_table.to_excel(writer, sheet_name='Analyse par Catégorie')
                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="📥 Télécharger en Excel",
                    data=excel_data,
                    file_name=f"analyse_categories_{period}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # PDF export
            with col2:
                pdf_data = create_pdf(category_period_table)
                st.download_button(
                    label="📥 Télécharger en PDF",
                    data=pdf_data,
                    file_name=f"analyse_categories_{period}.pdf",
                    mime="application/pdf",
                )

            # Create a bar chart for categories
            fig_categories = go.Figure()

            # Add bars for charges
            fig_categories.add_trace(go.Bar(
                name='Charges',
                x=df_category_summary['category_name'].unique(),
                y=df_category_summary.groupby('category_name')['charges'].sum(),
                marker_color='red',
                opacity=0.7
            ))

            # Add bars for recettes
            fig_categories.add_trace(go.Bar(
                name='Recettes',
                x=df_category_summary['category_name'].unique(),
                y=df_category_summary.groupby('category_name')['recettes'].sum(),
                marker_color='green',
                opacity=0.7
            ))

            fig_categories.update_layout(
                barmode='group',
                title=f"Répartition par Catégorie",
                xaxis_title="Catégorie",
                yaxis_title="Montant (DH)",
                height=400
            )

            st.plotly_chart(fig_categories, use_container_width=True)

            # Detailed category metrics
            for idx, row in df_category_summary.groupby('category_name').agg({
                'charges': 'sum',
                'recettes': 'sum',
                'balance': 'sum'
            }).reset_index().iterrows():
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    f"{row['category_name']} - Charges",
                    f"{row['charges']:,.2f} DH"
                )
                col2.metric(
                    f"{row['category_name']} - Recettes",
                    f"{row['recettes']:,.2f} DH"
                )
                col3.metric(
                    f"{row['category_name']} - Balance",
                    f"{row['balance']:,.2f} DH",
                    delta=f"{row['balance']:,.2f} DH",
                    delta_color="normal" if row['balance'] > 0 else "inverse"
                )

    else:
        st.info("Aucune donnée disponible pour l'analyse")

if __name__ == "__main__":
    main()