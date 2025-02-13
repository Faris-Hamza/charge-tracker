import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

def set_page_config():
    st.set_page_config(
        page_title="Gestion des Charges",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': """
            ### Application de Gestion Financière
            Une application complète pour la gestion de vos finances.
            """,
            'Get help': None,
            'Report a Bug': None
        }
    )

    # Customizing the sidebar style
    st.markdown("""
        <style>
        .css-1d391kg {
            padding-top: 1rem;
        }
        .css-163ttbj {
            position: relative;
            overflow: auto;
            padding: 1rem;
        }
        /* Amélioration du style des liens du menu */
        .css-1oe5cao {
            padding: 0.5rem 1rem;
            margin: 0.2rem 0;
            border-radius: 0.3rem;
            transition: background-color 0.2s ease;
        }
        .css-1oe5cao:hover {
            background-color: rgba(151, 166, 195, 0.15);
        }
        /* Style pour les groupes de menu (préparation pour les futurs sous-menus) */
        .menu-group {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(49, 51, 63, 0.1);
        }
        .menu-group-title {
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            padding-left: 1rem;
        }
        /* Amélioration du contraste et de la lisibilité */
        .css-1oe5cao span {
            color: #31333F;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

def create_time_series(df, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['period'],
        y=df['charges'],
        name='Charges',
        line=dict(color='#E74C3C')
    ))
    fig.add_trace(go.Scatter(
        x=df['period'],
        y=df['recettes'],
        name='Recettes',
        line=dict(color='#2ECC71')
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Période",
        yaxis_title="Montant (DH)",
        template="plotly_white",
        margin=dict(t=50, l=50, r=30, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

# Constants
NATURE_OPTIONS = [
    "Loyer",
    "Électricité",
    "Eau",
    "Internet",
    "Téléphone",
    "Alimentation",
    "Transport",
    "Assurance",
    "Santé",
    "Loisirs",
    "Autres"
]