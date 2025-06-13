import os
import sys


def get_project_root():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        script_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(script_path)


def get_credential_path(filename):
    root_dir = get_project_root()

    possible_paths = [
        os.path.join(root_dir, filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.getcwd()), filename),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    default_path = os.path.join(root_dir, filename)
    print(f"AVISO: Arquivo {filename} não encontrado. Usando caminho padrão: {default_path}")
    return default_path
