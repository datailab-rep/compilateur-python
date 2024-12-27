import streamlit as st
import sys
import io
import re
import uuid
from typing import List, Tuple, Dict
import traceback
import importlib
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# Initialisation de l'état de session pour l'historique d'exécution et le stockage des variables
if 'execution_history' not in st.session_state:
    st.session_state.execution_history = []
if 'execution_state' not in st.session_state:
    st.session_state.execution_state = {}

# Configuration et modules autorisés
ALLOWED_MODULES = [
    'math', 're', 'random', 'time', 'datetime', 'collections',
    'itertools', 'functools', 'statistics', 'typing', 'operator',
    'json', 'csv', 'numpy', 'pandas', 'scipy', 'sklearn',
    'matplotlib', 'matplotlib.pyplot', 'seaborn', 'plotly',
    'torch', 'tensorflow', 'keras', 'sympy', 'networkx', 'pillow',
    'requests', 'beautifulsoup4', 'nltk', 'pytz', 'emoji', 'pytest'
]


# Configuration de la page Streamlit avec un thème amélioré
st.set_page_config(
    page_title="Console Python de Data AI Lab",
    page_icon="🐍",
    layout="wide"
)

# Style CSS personnalisé avec un design moderne et élégant
st.markdown("""
    <style>
    /* Thème global */
    .stApp {
        background-color: #f4f6f9;
        font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
    }

    /* Titre principal */
    .title {
        color: #2c3e50;
        text-align: center;
        font-weight: 700;
        margin-bottom: 20px;
        background: linear-gradient(45deg, #3498db, #2ecc71);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
    }

    /* Zone de code */
    .stTextArea > div > div > textarea {
        background-color: #f8f9fa;
        border: 2px solid #3498db;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        font-family: 'Fira Code', monospace;
    }

    /* Bouton d'exécution */
    .stButton > button {
        background-color: #2ecc71;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #27ae60;
        transform: scale(1.05);
    }

    /* Cellules d'historique */
    .stExpander {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
        padding: 10px;
    }

    /* Code et sortie */
    .stCodeBlock {
        background-color: #f1f3f5;
        border-left: 4px solid #3498db;
        border-radius: 5px;
        padding: 10px;
        font-family: 'Fira Code', monospace;
    }

    /* Messages de succès et d'erreur */
    .stSuccess, .stError {
        border-radius: 8px;
        padding: 10px;
    }

    .stSuccess {
        background-color: rgba(46, 204, 113, 0.1);
        border-left: 4px solid #2ecc71;
    }

    .stError {
        background-color: rgba(231, 76, 60, 0.1);
        border-left: 4px solid #e74c3c;
    }
    </style>
""", unsafe_allow_html=True)


def executer_code_en_securite(code: str, execution_state: dict) -> Tuple[bool, str, List[plt.Figure]]:
    """
    Exécuter du code Python en toute sécurité avec persistance d'état et messages d'erreur personnalisés
    """
    old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
    stdin_capture = io.StringIO()
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    sys.stdin, sys.stdout, sys.stderr = stdin_capture, stdout_capture, stderr_capture

    figures_capturees = []

    try:
        # Créer un environnement d'exécution avec l'état existant
        exec_globals = {
            '__builtins__': __builtins__,
            'plt': plt,
            'sns': sns,
            'np': np,
            'pd': pd,
        }

        # Ajouter l'état existant
        exec_globals.update(execution_state)

        # Gérer les imports et l'exécution du code
        instructions_import = []
        code_sans_imports = []

        for ligne in code.split('\n'):
            if ligne.strip().startswith(('import ', 'from ')):
                instructions_import.append(ligne)
            else:
                code_sans_imports.append(ligne)

        # Exécuter les imports
        for import_stmt in instructions_import:
            exec(import_stmt, exec_globals)

        # Exécuter le code principal
        exec('\n'.join(code_sans_imports), exec_globals)

        # Mettre à jour l'état d'exécution avec les nouvelles variables
        execution_state.update({
            k: v for k, v in exec_globals.items()
            if not k.startswith('__') and k not in ('plt', 'sns', 'np', 'pd')
        })

        # Capturer les figures
        figures_capturees = [plt.figure(num) for num in plt.get_fignums()]

        sortie = stdout_capture.getvalue()
        return True, sortie.strip() if sortie.strip() else "Code exécuté avec succès.", figures_capturees

    except Exception as e:
        # Personnaliser le message d'erreur
        if isinstance(e, NameError):
            # Pour les erreurs de variable non définie
            return False, f"'{e.name}' n'est pas défini", []
        elif isinstance(e, TypeError):
            # Pour les erreurs de type
            return False, str(e).split(':')[-1].strip(), []
        elif isinstance(e, SyntaxError):
            # Pour les erreurs de syntaxe
            return False, f"Erreur de syntaxe: {e.msg}", []
        elif isinstance(e, ImportError):
            # Pour les erreurs d'importation
            return False, f"Erreur d'importation: {str(e)}", []
        else:
            # Pour tout autre type d'erreur
            return False, str(e), []

    finally:
        sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr
        stdin_capture.close()
        stdout_capture.close()
        stderr_capture.close()


def est_code_securise(code: str) -> Tuple[bool, str]:
    """
    Vérifier si le code est sûr à exécuter
    """
    modeles_non_securises = [r'open\(', r'exec\(', r'eval\(']

    for modele in modeles_non_securises:
        if re.search(modele, code):
            return False, "Modèle de code non sécurisé détecté"

    imports = re.findall(r'^import\s+(\w+)', code, re.MULTILINE)
    imports_depuis = re.findall(r'^from\s+(\w+)', code, re.MULTILINE)

    imports_non_autorises = [
        imp for imp in set(imports + imports_depuis)
        if not any(imp.startswith(autorise) for autorise in ALLOWED_MODULES)
    ]

    if imports_non_autorises:
        return False, f"Imports non autorisés : {', '.join(imports_non_autorises)}"

    return True, "Le code semble sûr"


def main():
    st.markdown('<h1 class="title">🐍 Console Python de Data AI Lab</h1>', unsafe_allow_html=True)

    # Créer deux colonnes pour la disposition
    col1, col2 = st.columns([3, 1])

    with col1:
        # Zone de saisie de code avec un placeholder informatif
        nouveau_code = st.text_area(
            "Nouvelle Cellule de Code :",
            height=300,
        )



    # Bouton d'exécution avec une icône
    if st.button("🚀 Exécuter le Code"):
        if nouveau_code.strip():
            # Vérifier la sécurité du code
            est_securise, message_securite = est_code_securise(nouveau_code)

            if not est_securise:
                st.error(f"⚠️ {message_securite}")
            else:
                # Exécuter le code et stocker dans l'historique
                succes, sortie, figures = executer_code_en_securite(
                    nouveau_code,
                    st.session_state.execution_state
                )

                st.session_state.execution_history.append({
                    'code': nouveau_code,
                    'output': sortie,
                    'figures': figures,
                    'success': succes
                })

    # Afficher l'historique d'exécution dans l'ordre inverse
    if st.session_state.execution_history:
        st.subheader("📜 Historique d'Exécution")
        for cellule in reversed(st.session_state.execution_history):
            with st.expander("Cellule de Code", expanded=True):
                st.code(cellule['code'], language='python')
                if cellule['success']:
                    st.success("✅ Sortie :")
                    if cellule['output']:
                        st.code(cellule['output'])
                    for fig in cellule['figures']:
                        st.pyplot(fig)
                else:
                    st.error("❌ Erreur :")
                    st.error(cellule['output'])
    else:
        st.info("🔍 Aucun historique d'exécution. Commencez à coder!")


if __name__ == "__main__":
    main()