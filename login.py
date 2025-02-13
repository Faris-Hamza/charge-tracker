import streamlit as st
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

        # CSS amélioré pour un design plus professionnel
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        .css-1d391kg {visibility: hidden;}
        footer {visibility: hidden;}

        /* Masquer le bouton hamburger du menu */
        .st-emotion-cache-1dp5vir {
            display: none;
        }
        .st-emotion-cache-79elbk {
            display: none;
        }

        /* Style personnalisé pour le conteneur principal */
        .main {
            background-color: #f8f9fa;
            padding: 2rem;
        }

        /* Style pour le titre */
        .title-text {
            color: #1f77b4;
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 2rem;
            font-weight: bold;
        }

        /* Style pour le formulaire */
        .stForm {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            margin: 0 auto;
        }

        /* Style pour les boutons */
        .stButton button {
            background-color: #1f77b4;
            color: white;
            font-weight: bold;
            border-radius: 5px;
            border: none;
            padding: 0.5rem 1rem;
            width: 100%;
        }

        .stButton button:hover {
            background-color: #155987;
        }

        /* Style amélioré pour les champs de texte */
        div[data-baseweb="input"] {
            width: 100% !important;
            margin-bottom: 1rem !important;
        }

        div[data-baseweb="input"] input {
            border: 1px solid #e0e0e0 !important;
            border-radius: 5px !important;
            padding: 0.5rem !important;
            font-size: 1rem !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        div[data-baseweb="input"] input:focus {
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
            outline: none !important;
        }

        /* Style pour les messages d'erreur et de succès */
        .stAlert {
            border-radius: 5px;
            margin-top: 1rem;
        }
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