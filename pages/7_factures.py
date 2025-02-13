import streamlit as st
import pandas as pd
from datetime import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from database import Database
from utils import set_page_config
from num2words import num2words
from auth.auth_decorator import require_auth
import json

set_page_config()

def get_next_invoice_number(date_facture):
    """Génère un numéro de facture selon le format souhaité"""
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    sequence = st.session_state.db.get_next_invoice_sequence()
    return f"297002{date_facture.strftime('%d%m%y')}{sequence:04d}"

def init_session_state():
    """Initialise les variables de session si elles n'existent pas"""
    if 'client_info' not in st.session_state:
        st.session_state.client_info = {
            "nom": "",
            "ice": "",
            "adresse": ""
        }
    if 'invoice_lines' not in st.session_state:
        st.session_state.invoice_lines = [{
            'description': '',
            'quantite': 1,
            'prix_unitaire': 0.0,
            'tva': 20
        }]
    if 'last_dates' not in st.session_state:
        st.session_state.last_dates = {
            'date_debut': datetime.now().date(),
            'date_fin': datetime.now().date()
        }

@require_auth
def main():
    st.title("🧾 Génération de Factures")

    # Initialize database connection and session state
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    init_session_state()

    # Créer deux onglets: Nouvelle Facture et Historique
    tab1, tab2 = st.tabs(["📝 Nouvelle Facture", "📚 Historique"])

    with tab1:
        # Informations client
        st.subheader("📋 Informations Client")

        # Utiliser les dernières valeurs sauvegardées
        nom = st.text_input("Nom/Raison sociale", value=st.session_state.client_info["nom"])
        ice = st.text_input("ICE", value=st.session_state.client_info["ice"])
        adresse = st.text_area("Adresse", value=st.session_state.client_info["adresse"])

        # Mettre à jour les informations client
        st.session_state.client_info = {
            "nom": nom,
            "ice": ice,
            "adresse": adresse
        }

        # Informations facture
        st.subheader("📝 Détails de la Facture")
        col1, col2 = st.columns(2)
        with col1:
            invoice_date = st.date_input("Date Facture")
            invoice_number = st.text_input("N° Facture", get_next_invoice_number(invoice_date))

        # Période de facturation
        st.subheader("📅 Période de Facturation")
        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input("Du", value=st.session_state.last_dates['date_debut'], key="date_debut")
        with col2:
            date_fin = st.date_input("Au", value=st.session_state.last_dates['date_fin'], key="date_fin")

        # Mettre à jour les dates
        st.session_state.last_dates = {
            'date_debut': date_debut,
            'date_fin': date_fin
        }

        # Lignes de facture
        st.subheader("📊 Lignes de Facture")

        # Bouton pour ajouter une nouvelle ligne
        if st.button("➕ Ajouter une ligne"):
            st.session_state.invoice_lines.append({
                'description': '',
                'quantite': 1,
                'prix_unitaire': 0.0,
                'tva': 20
            })

        # Afficher les lignes de facture
        for idx, line in enumerate(st.session_state.invoice_lines):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])

            with col1:
                line['description'] = st.text_input(
                    "Description",
                    value=line['description'],
                    key=f"desc_{idx}"
                )
            with col2:
                line['quantite'] = st.number_input(
                    "Quantité",
                    min_value=1,
                    value=line['quantite'],
                    key=f"qty_{idx}"
                )
            with col3:
                line['prix_unitaire'] = st.number_input(
                    "Prix unitaire HT",
                    min_value=0.0,
                    value=float(line['prix_unitaire']),
                    key=f"price_{idx}"
                )
            with col4:
                line['tva'] = st.number_input(
                    "TVA %",
                    min_value=0,
                    max_value=20,
                    value=int(line['tva']),
                    key=f"tva_{idx}"
                )
            with col5:
                if idx > 0 and st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.invoice_lines.pop(idx)
                    st.rerun()

        # Calculs
        total_ht = sum(line['quantite'] * line['prix_unitaire'] for line in st.session_state.invoice_lines)
        total_tva = sum(line['quantite'] * line['prix_unitaire'] * (line['tva']/100) for line in st.session_state.invoice_lines)
        total_ttc = total_ht + total_tva

        # Afficher les totaux
        st.subheader("💰 Totaux")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total HT", f"{total_ht:,.2f} DH")
        col2.metric("Total TVA", f"{total_tva:,.2f} DH")
        col3.metric("Total TTC", f"{total_ttc:,.2f} DH")

        def create_invoice_pdf():
            buffer = io.BytesIO()

            # Configuration du document avec des marges adaptées
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=1.5*cm,
                leftMargin=1.5*cm,
                topMargin=2.5*cm,
                bottomMargin=3*cm
            )

            elements = []
            styles = getSampleStyleSheet()

            # En-tête avec date à droite
            header_data = [
                ["", "Date: " + invoice_date.strftime("%d/%m/%Y")],
                ["", f"Période de facturation: Du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"]
            ]
            header_table = Table(header_data, colWidths=[400, 150])
            header_table.setStyle(TableStyle([
                ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (-1, -1), (-1, -1), 10),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))

            # Titre Facture
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=1,
                spaceAfter=20
            )
            elements.append(Paragraph("FACTURE", header_style))

            # Informations client et facture
            info_data = [
                ["N° Facture:", invoice_number],
                ["Client:", st.session_state.client_info["nom"]],
                ["ICE:", st.session_state.client_info["ice"]],
                ["Adresse:", st.session_state.client_info["adresse"]]
            ]

            info_table = Table(info_data, colWidths=[100, 300])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 20))

            # Lignes de facture
            invoice_data = [["Description", "Quantité", "Prix Unit. HT", "TVA", "Total HT"]]
            for line in st.session_state.invoice_lines:
                total_line = line['quantite'] * line['prix_unitaire']
                invoice_data.append([
                    line['description'],
                    str(line['quantite']),
                    f"{line['prix_unitaire']:,.2f} DH",
                    f"{line['tva']}%",
                    f"{total_line:,.2f} DH"
                ])

            # Ajouter les totaux
            invoice_data.extend([
                ["", "", "", "Total HT:", f"{total_ht:,.2f} DH"],
                ["", "", "", "Total TVA:", f"{total_tva:,.2f} DH"],
                ["", "", "", "Total TTC:", f"{total_ttc:,.2f} DH"]
            ])

            # Créer le tableau des lignes
            invoice_table = Table(invoice_data, colWidths=[250, 60, 80, 60, 80])
            invoice_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -4), 1, colors.black),
                ('LINEABOVE', (3, -3), (-1, -3), 1, colors.black),
                ('LINEABOVE', (3, -2), (-1, -2), 1, colors.black),
                ('LINEABOVE', (3, -1), (-1, -1), 2, colors.black),
                ('ALIGN', (0, -3), (2, -1), 'RIGHT'),
            ]))
            elements.append(invoice_table)
            elements.append(Spacer(1, 20))

            # Montant en lettres
            montant_lettres = num2words(total_ttc, lang='fr')
            montant_text = f"Arrêté la présente facture à la somme de : {montant_lettres.upper()} DIRHAMS"
            elements.append(Paragraph(montant_text, ParagraphStyle(
                'MontantText',
                parent=styles['Normal'],
                fontSize=10,
                alignment=0,
                spaceBefore=10,
                spaceAfter=20
            )))

            # Ajouter un espace pour pousser le footer vers le bas
            elements.append(Spacer(1, 50))

            # Footer avec les informations de la société (en bas de page)
            footer_text = """
            <para alignment="center">
            <font size="10"><b>STE HABIBCASH SARL</b></font><br/>
            <font size="8">ICE: 002184554000026<br/>
            DR IKOURAMN AIT BRAIM CR BOUNAAMAN - TIZNIT<br/>
            RC: 3939 - Patente: 49567063 - IF: 33668520 - CNSS: 2436357</font>
            </para>
            """

            footer = Paragraph(footer_text, ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                alignment=1,
                textColor=colors.black,
                leading=14  # Espacement entre les lignes
            ))

            # Créer un cadre pour le footer qui sera toujours en bas de page
            frame = Frame(
                doc.leftMargin,
                doc.bottomMargin - 2*cm,  # Position plus basse
                doc.width,
                2*cm,  # Hauteur du footer
                showBoundary=0
            )

            elements.append(Spacer(1, 1*cm))  # Espace avant le footer
            elements.append(footer)

            doc.build(elements)
            buffer.seek(0)
            return buffer

        # Bouton pour générer la facture
        if st.button("📄 Générer la facture"):
            if not st.session_state.client_info["nom"] or not st.session_state.client_info["ice"]:
                st.error("Veuillez remplir au moins le nom et l'ICE du client.")
            elif not any(line['description'] for line in st.session_state.invoice_lines):
                st.error("Veuillez ajouter au moins une ligne de facture avec une description.")
            else:
                pdf_buffer = create_invoice_pdf()

                # Sauvegarder la facture dans la base de données
                try:
                    totals_info = {
                        'total_ht': total_ht,
                        'total_tva': total_tva,
                        'total_ttc': total_ttc
                    }
                    st.session_state.db.add_invoice(
                        invoice_number=invoice_number,
                        date=invoice_date,
                        client_info=st.session_state.client_info,
                        lines=st.session_state.invoice_lines,
                        totals_info=totals_info,
                        pdf_data=pdf_buffer.getvalue()
                    )

                    st.download_button(
                        label="⬇️ Télécharger la facture PDF",
                        data=pdf_buffer,
                        file_name=f"facture_{invoice_number}.pdf",
                        mime="application/pdf"
                    )
                    st.success("Facture générée et sauvegardée avec succès!")
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde de la facture: {str(e)}")

    with tab2:
        st.subheader("📚 Historique des Factures")
        invoices = st.session_state.db.get_invoices()

        if invoices:
            for invoice in invoices:
                with st.expander(f"Facture {invoice['invoice_number']} - {invoice['date'].strftime('%d/%m/%Y')}"):
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        # Afficher les informations de la facture
                        client_info = invoice['client_info']
                        st.write(f"**Client:** {client_info['nom']}")
                        st.write(f"**ICE:** {client_info['ice']}")

                        # Afficher les totaux
                        totals = invoice['totals_info']
                        st.write(f"**Total HT:** {totals['total_ht']:,.2f} DH")
                        st.write(f"**Total TVA:** {totals['total_tva']:,.2f} DH")
                        st.write(f"**Total TTC:** {totals['total_ttc']:,.2f} DH")

                        # Bouton pour télécharger le PDF
                        pdf_data = st.session_state.db.get_invoice_pdf(invoice['id'])
                        if pdf_data:
                            st.download_button(
                                label="⬇️ Télécharger le PDF",
                                data=pdf_data,
                                file_name=f"facture_{invoice['invoice_number']}.pdf",
                                mime="application/pdf",
                                key=f"pdf_{invoice['id']}"
                            )

                    with col2:
                        # Bouton de suppression
                        if st.button("🗑️", key=f"del_invoice_{invoice['id']}"):
                            try:
                                st.session_state.db.delete_invoice(invoice['id'])
                                st.success("Facture supprimée avec succès!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression: {str(e)}")
        else:
            st.info("Aucune facture dans l'historique.")

if __name__ == "__main__":
    main()