import streamlit as st

def kpi_card(title: str, value: str, delta: str = None, color: str = "normal"):
    st.metric(label=title, value=value, delta=delta)

def render_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.divider()
