import streamlit as st
import hashlib
from database import Database
from utils import set_page_config

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'db' not in st.session_state:
        st.session_state.db = Database()
    
    # Check for admin user
    check_admin_user()

def check_admin_user():
    """Vérifie si un administrateur existe et en crée un si nécessaire."""
    try:
        with st.session_state.db.conn.cursor() as cur:
            # Vérifier si des utilisateurs existent
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            
            if user_count == 0:
                # Créer un utilisateur admin par défaut
                default_admin = {
                    'username': 'admin',
                    'password': 'admin123',  # À changer après la première connexion
                    'role': 'admin',
                    'full_name': 'Administrator',
                    'email': 'admin@example.com'
                }
                
                st.session_state.db.create_user(
                    username=default_admin['username'],
                    password=default_admin['password'],
                    role=default_admin['role'],
                    full_name=default_admin['full_name'],
                    email=default_admin['email']
                )
                
                st.warning("""
                    ⚠️ Un compte administrateur par défaut a été créé:
                    - Utilisateur: admin
                    - Mot de passe: admin123
                    Veuillez vous connecter et changer le mot de passe immédiatement.
                """)
    except Exception as e:
        st.error(f"Erreur lors de la vérification/création de l'administrateur: {str(e)}")

def show_auth_status():
    with st.container():
        col1, col2, col3, auth_col = st.columns([1, 1, 1, 1])
        with auth_col:
            if st.session_state.logged_in:
                st.success(f"👤 {st.session_state.username}")
                if st.button("📤 Déconnexion", key="logout"):
                    st.session_state.logged_in = False
                    st.session_state.user_role = None
                    st.session_state.username = None
                    st.rerun()

def login():
    # Configuration de la page
    if not st.session_state.get('logged_in', False):
        st.set_page_config(
            page_title="Connexion - Gestion des Charges",
            layout="wide",
            initial_sidebar_state="collapsed"
        )

        # [Previous CSS styles remain the same]
        st.markdown("""
        <style>
        /* Your existing CSS styles here */
        </style>
        """, unsafe_allow_html=True)
    else:
        set_page_config()

    init_session_state()
    show_auth_status()

    if st.session_state.logged_in:
        st.markdown('<h1 class="title-text">📊 Gestion des Charges</h1>', unsafe_allow_html=True)
        st.markdown("""
        ### Bienvenue dans votre application de gestion des charges

        Cette application vous permet de :
        - Saisir vos charges et recettes
        - Consulter des rapports détaillés
        - Visualiser des tableaux de bord d'analyse

        Utilisez le menu latéral pour naviguer entre les différentes sections.
        """)
        return

    # Centrer le contenu de la page de connexion
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<h1 class="title-text">🔐 Connexion</h1>', unsafe_allow_html=True)

        with st.form("login_form"):
            st.markdown("### Entrez vos identifiants")
            username = st.text_input("👤 Nom d'utilisateur")
            password = st.text_input("🔑 Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")

            if submitted:
                if not username or not password:
                    st.error("⚠️ Veuillez remplir tous les champs")
                else:
                    user = st.session_state.db.verify_login(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_role = user['role']
                        st.session_state.username = user['username']
                        st.success("✅ Connexion réussie!")
                        st.rerun()
                    else:
                        st.error("❌ Nom d'utilisateur ou mot de passe incorrect")

        st.markdown("""
        <div style='text-align: center; color: #666; margin-top: 2rem;'>
            Pour vous connecter, veuillez utiliser vos identifiants.
        </div>
        """, unsafe_allow_html=True)

login()
