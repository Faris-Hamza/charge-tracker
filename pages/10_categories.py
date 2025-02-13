import streamlit as st
import pandas as pd
from database import Database
from utils import set_page_config

set_page_config()

# Vérifier si l'utilisateur est connecté
if not st.session_state.get('logged_in', False):
    st.warning("Veuillez vous connecter pour accéder à cette page")
    st.stop()

st.title("🏷️ Gestion des Catégories")

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()

# Form for adding new categories
with st.form("category_form"):
    st.subheader("Ajouter une nouvelle catégorie")
    name = st.text_input("Nom de la catégorie")
    description = st.text_area("Description (optionnelle)")

    submitted = st.form_submit_button("Ajouter")

    if submitted and name:
        try:
            st.session_state.db.add_category(name, description)
            st.success(f"Catégorie '{name}' ajoutée avec succès!")
        except Exception as e:
            if "unique constraint" in str(e).lower():
                st.error("Cette catégorie existe déjà.")
            else:
                st.error(f"Erreur lors de l'ajout de la catégorie: {str(e)}")

# Display existing categories
st.subheader("Catégories existantes")
df = st.session_state.db.get_categories()
if not df.empty:
    # Pour chaque catégorie
    for idx, row in df.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{row['name']}**")
            if row['description']:
                st.write(row['description'])
        with col2:
            st.write(pd.to_datetime(row['created_at']).strftime('%d/%m/%Y %H:%M'))
        with col3:
            # Afficher le bouton de suppression uniquement pour les admins
            if st.session_state.get('user_role') == 'admin':
                if st.button("Supprimer", key=f"del_cat_{row['id']}"):
                    try:
                        st.session_state.db.delete_category(int(row['id']))
                        st.success(f"Catégorie '{row['name']}' supprimée avec succès!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
else:
    st.info("Aucune catégorie n'a été créée.")