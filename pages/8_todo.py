import streamlit as st
import pandas as pd
from database import Database
from utils import set_page_config
from datetime import datetime, timedelta
import json
from auth.auth_decorator import require_auth

set_page_config()

@require_auth
def main():
    st.title("📋 To Do List")

    # Initialize database connection
    if 'db' not in st.session_state:
        st.session_state.db = Database()

    # Create todo table if not exists
    st.session_state.db.create_todo_table()

    # Form for adding new task
    st.subheader("✨ Nouveau Projet")
    with st.form("new_task_form"):
        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input("Nom du projet", key="project_name")
            due_date = st.date_input(
                "Date d'échéance",
                value=datetime.now() + timedelta(days=7),
                min_value=datetime.now().date()
            )

        with col2:
            description = st.text_area("Description du projet")
            requirements = st.text_area("Besoins pour le projet")

        # Dynamic steps input
        st.subheader("Étapes du projet")
        num_steps = st.number_input("Nombre d'étapes", min_value=1, value=3)
        steps = []

        for i in range(num_steps):
            col1, col2 = st.columns([3, 1])
            with col1:
                step_description = st.text_input(f"Étape {i+1}", key=f"step_{i}")
            steps.append({
                "description": step_description,
                "completed": False,
                "order": i + 1
            })

        submitted = st.form_submit_button("Ajouter le projet")

        if submitted:
            if not project_name:
                st.error("Le nom du projet est obligatoire.")
            else:
                try:
                    st.session_state.db.add_todo_task(
                        project_name=project_name,
                        due_date=due_date,
                        description=description,
                        steps=json.dumps(steps),
                        requirements=requirements
                    )
                    st.success("Projet ajouté avec succès!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de l'ajout du projet: {str(e)}")

    # Display existing tasks
    st.subheader("📝 Projets en cours")
    tasks_df = st.session_state.db.get_todo_tasks()

    if not tasks_df.empty:
        for _, task in tasks_df.iterrows():
            # Vérifier si toutes les étapes sont complétées
            steps = json.loads(task['steps']) if isinstance(task['steps'], str) else task['steps']
            all_completed = all(step.get('completed', False) for step in steps)

            # Ajouter l'icône d'état (vert si complété, gris sinon)
            status_icon = "✅" if all_completed else "⭕"

            with st.expander(f"{status_icon} {task['project_name']} (Échéance: {task['due_date'].strftime('%d/%m/%Y')})"):
                # Colonnes pour le contenu et le bouton de suppression
                main_col, del_col = st.columns([5, 1])

                with main_col:
                    # Project details
                    st.write("**Description:**")
                    st.write(task['description'] if task['description'] else "Aucune description")

                    st.write("**Besoins:**")
                    st.write(task['requirements'] if task['requirements'] else "Aucun besoin spécifié")

                    # Steps with checkboxes
                    st.write("**Étapes:**")
                    updated_steps = []

                    for step in steps:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{step['order']}. {step['description']}")
                        with col2:
                            step['completed'] = st.checkbox(
                                "Terminé",
                                value=step.get('completed', False),
                                key=f"step_{task['id']}_{step['order']}"
                            )
                        updated_steps.append(step)

                with del_col:
                    if st.button("🗑️", key=f"delete_task_{task['id']}"):
                        try:
                            st.session_state.db.delete_todo_task(task['id'])
                            st.success("Projet supprimé avec succès!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la suppression: {str(e)}")

                # Save changes if steps were modified
                new_steps = json.dumps(updated_steps)
                if new_steps != task['steps']:
                    try:
                        st.session_state.db.update_todo_task(
                            task_id=task['id'],
                            steps=new_steps
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de la mise à jour: {str(e)}")
    else:
        st.info("Aucun projet dans la liste pour le moment.")

if __name__ == "__main__":
    main()