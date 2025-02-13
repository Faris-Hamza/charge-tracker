import streamlit as st
from database import Database
from utils import set_page_config

set_page_config()

# Vérifier si l'utilisateur est connecté
if not st.session_state.get('logged_in', False):
    st.warning("Veuillez vous connecter pour accéder à cette page")
    st.stop()

st.title("📊 Gestion des Charges")

st.markdown("""
### Bienvenue dans votre application de gestion des charges

Cette application vous permet de :
- Saisir vos charges et recettes
- Consulter des rapports détaillés
- Visualiser des tableaux de bord d'analyse

Utilisez le menu latéral pour naviguer entre les différentes sections.
""")

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()
