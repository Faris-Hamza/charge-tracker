import streamlit as st
from database import Database
from utils import set_page_config

set_page_config()

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'db' not in st.session_state:
        st.session_state.db = Database()

def show_auth_status():
    st.sidebar.markdown("---")
    if st.session_state.logged_in:
        st.sidebar.success(f"Connecté en tant que {st.session_state.username}")
        if st.sidebar.button("📤 Déconnexion", key="logout"):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.session_state.username = None
            st.rerun()
    else:
        if st.sidebar.button("🔐 Connexion", key="login"):
            st.switch_page("auth/login.py")

def main():
    init_session_state()
    show_auth_status()

    if not st.session_state.logged_in:
        st.warning("Veuillez vous connecter pour accéder à l'application")
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

main()