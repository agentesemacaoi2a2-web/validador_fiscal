import subprocess
import sys
import os

# Ir para o diretório do projeto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Rodar streamlit
subprocess.run([
    sys.executable, "-m", "streamlit", "run", 
    "validador_fiscal/app/app_completa_melhorada.py"
])
