import sys
import os
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'validador_fiscal'))

try:
    from app.app_completa_melhorada import *
except Exception as e:
    import streamlit as st
    st.error(f"❌ ERRO: {str(e)}")
    st.write(traceback.format_exc())
