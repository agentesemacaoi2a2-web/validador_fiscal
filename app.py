import streamlit as st
st.set_page_config(page_title="Validador Fiscal", layout="wide")

st.title("🎉 Validador Fiscal NFS - Online!")
st.write("App funcionando!")

# Depois adiciona imports aos poucos
try:
    from validador_fiscal.app.app_completa_melhorada import *
except Exception as e:
    st.error(f"Erro: {str(e)}")
