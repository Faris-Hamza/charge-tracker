import streamlit as st
from functools import wraps

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('logged_in', False):
            st.error("⚠️ Veuillez vous connecter pour accéder à cette page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
