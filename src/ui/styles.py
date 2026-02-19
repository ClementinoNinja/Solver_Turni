import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
        }
        .reportview-container {
            background: #f0f2f6
        }
    </style>
    """, unsafe_allow_html=True)
