import streamlit as st
from database import Database
from utils import set_page_config
import re

set_page_config()

# Vérifier si l'utilisateur est connecté et est admin
if not st.session_state.get('logged_in', False):
    st.warning("Veuillez vous connecter pour accéder à cette page")
    st.stop()
elif st.session_state.get('user_role') != 'admin':
    st.error("Accès non autorisé. Cette page est réservée aux administrateurs.")
    st.stop()

st.title("👥 Gestion des Utilisateurs")

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()

# Fonction pour valider l'email
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Fonction pour valider le mot de passe
def is_valid_password(password):
    return len(password) >= 8

# Section pour créer un nouvel utilisateur
st.subheader("Créer un nouvel utilisateur")
with st.form("new_user_form"):
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Nom d'utilisateur")
        new_password = st.text_input("Mot de passe", type="password")
        new_role = st.selectbox("Rôle", ["user", "admin"])
    with col2:
        new_full_name = st.text_input("Nom complet")
        new_email = st.text_input("Email")
    
    submitted = st.form_submit_button("Créer l'utilisateur")
    
    if submitted:
        if not all([new_username, new_password, new_role]):
            st.error("Tous les champs obligatoires doivent être remplis")
        elif not is_valid_password(new_password):
            st.error("Le mot de passe doit contenir au moins 8 caractères")
        elif new_email and not is_valid_email(new_email):
            st.error("Format d'email invalide")
        else:
            try:
                st.session_state.db.create_user(
                    username=new_username,
                    password=new_password,
                    role=new_role,
                    full_name=new_full_name,
                    email=new_email
                )
                st.success(f"Utilisateur {new_username} créé avec succès!")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")

# Liste des utilisateurs existants
st.subheader("Utilisateurs existants")
users = st.session_state.db.get_all_users()

for user in users:
    with st.expander(f"{user['username']} ({user['role']})"):
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            full_name = st.text_input("Nom complet", value=user['full_name'] or "", key=f"name_{user['id']}")
            email = st.text_input("Email", value=user['email'] or "", key=f"email_{user['id']}")
        
        with col2:
            new_password = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", 
                                       type="password", 
                                       key=f"pwd_{user['id']}")
        
        with col3:
            if st.button("Mettre à jour", key=f"update_{user['id']}"):
                if new_password and not is_valid_password(new_password):
                    st.error("Le mot de passe doit contenir au moins 8 caractères")
                elif email and not is_valid_email(email):
                    st.error("Format d'email invalide")
                else:
                    try:
                        st.session_state.db.update_user(
                            user_id=user['id'],
                            full_name=full_name,
                            email=email,
                            new_password=new_password if new_password else None
                        )
                        st.success("Informations mises à jour avec succès!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la mise à jour: {str(e)}")
            
            if user['username'] != 'admin' and st.button("Supprimer", key=f"delete_{user['id']}"):
                try:
                    st.session_state.db.delete_user(user['id'])
                    st.success(f"Utilisateur {user['username']} supprimé avec succès!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la suppression: {str(e)}")
