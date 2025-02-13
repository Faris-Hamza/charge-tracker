import streamlit as st
from database import Database
from utils import set_page_config

set_page_config()

# Vérifier si l'utilisateur est connecté
if not st.session_state.get('logged_in', False):
    st.warning("Veuillez vous connecter pour accéder à cette page")
    st.stop()

st.title("🏢 Gestion des Projets")

# Initialize database connection
if 'db' not in st.session_state:
    st.session_state.db = Database()

# Initialize session state for editing
if 'editing_project' not in st.session_state:
    st.session_state.editing_project = None

# Formulaire pour ajouter un nouveau projet
st.subheader("Ajouter un nouveau projet")
with st.form("new_project_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Nom du projet")
        inclus_calcul = st.checkbox("Inclure dans les calculs entre associés", value=True,
                                  help="Si coché, ce projet sera inclus dans les calculs et répartitions entre associés")
    with col2:
        description = st.text_area("Description")

    submitted = st.form_submit_button("Ajouter")

    if submitted:
        if not name:
            st.error("Le nom du projet est obligatoire")
        else:
            try:
                st.session_state.db.add_project(name, description, inclus_calcul)
                st.success(f"Projet '{name}' ajouté avec succès!")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'ajout du projet: {str(e)}")

# Liste des projets existants
st.subheader("Projets existants")
projects = st.session_state.db.get_projects()

if not projects.empty:
    for _, project in projects.iterrows():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            # Mode édition ou affichage
            if st.session_state.editing_project == project['id']:
                new_name = st.text_input(
                    "Nouveau nom",
                    value=project['name'],
                    key=f"edit_{project['id']}"
                )
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    if st.button("💾 Sauvegarder", key=f"save_{project['id']}"):
                        try:
                            st.session_state.db.update_project_name(project['id'], new_name)
                            st.session_state.editing_project = None
                            st.success(f"Nom du projet modifié avec succès!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                with col1_2:
                    if st.button("❌ Annuler", key=f"cancel_{project['id']}"):
                        st.session_state.editing_project = None
                        st.rerun()
            else:
                st.markdown(f"**{project['name']}**")
                if project['description']:
                    st.write(project['description'])
        with col2:
            # Bouton d'édition
            if st.button("✏️", key=f"edit_btn_{project['id']}", help="Modifier le nom"):
                st.session_state.editing_project = project['id']
                st.rerun()
        with col3:
            # Option pour modifier l'inclusion dans les calculs
            if st.checkbox("Inclus dans les calculs",
                         value=project['inclus_calcul'],
                         key=f"incl_{project['id']}",
                         help="Cocher pour inclure ce projet dans les calculs entre associés"):
                if not project['inclus_calcul']:  # Si le statut change de False à True
                    st.session_state.db.update_project_inclusion(project['id'], True)
                    st.rerun()
            else:
                if project['inclus_calcul']:  # Si le statut change de True à False
                    st.session_state.db.update_project_inclusion(project['id'], False)
                    st.rerun()
        with col4:
            if st.button("🗑️", key=f"del_{project['id']}"):
                try:
                    st.session_state.db.delete_project(int(project['id']))
                    st.success(f"Projet '{project['name']}' supprimé avec succès!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Erreur lors de la suppression: {str(e)}")
        st.divider()
else:
    st.info("Aucun projet n'a été créé")