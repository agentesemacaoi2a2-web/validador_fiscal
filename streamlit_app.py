import streamlit as st
import sys
import os

st.write("✅ Iniciando app...")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'validador_fiscal'))

st.write("✅ Path adicionado")

try:
    st.write("Tentando importar app...")
    from app.app_completa_melhorada import *
    st.write("✅ App carregada com sucesso!")
except Exception as e:
    import traceback
    st.error(f"❌ ERRO NO IMPORT: {str(e)}")
    st.write(traceback.format_exc())
