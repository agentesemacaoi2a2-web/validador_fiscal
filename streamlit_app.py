import sys
import os

# Adicionar validador_fiscal ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar e rodar
from validador_fiscal.app.app_completa_melhorada import *
