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

def login():
    init_session_state()
    st.title("🔐 Connexion")

    with st.form("login_form"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

        if submitted:
            if not username or not password:
                st.error("Veuillez remplir tous les champs")
            else:
                user = st.session_state.db.verify_login(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user['role']
                    st.session_state.username = user['username']
                    st.success("Connexion réussie!")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect")

    st.markdown("""
    ### Identifiants de test:
    - Admin: username: `admin`, password: `admin123`
    - Utilisateur: username: `user`, password: `user123`
    """)

login()
