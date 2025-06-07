# tools/compile_code.py

# !/usr/bin/env python3
"""
Script para compilar todos os arquivos Python de um projeto em um único arquivo.
Exclui a pasta .venv e pode ser configurado para excluir outras pastas/arquivos.
Inclui os prompts do Firebase para facilitar a depuração.
Versão modificada para garantir compatibilidade com o sistema de conhecimento do Claude.

Para usar: clique com o botão direito no script e execute-o.
Ele irá compilar todos os arquivos no diretório atual em um arquivo chamado "COMPILADO.txt".
"""

import base64
import datetime
import os
import re
import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao PATH para poder importar os módulos da aplicação
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurações padrão - pastas e arquivos a serem ignorados
IGNORED_DIRS = {'.venv', '.git', '__pycache__', '.pytest_cache', '.idea', '.vs', 'build', 'dist',
                'node_modules', 'tools'}
IGNORED_FILES = {'.gitignore', '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo', '*.pyd', '*.so', '*.dll', '*.exe'}

# Extensões de arquivo a serem processadas
INCLUDED_EXTENSIONS = {'.py', '.json', '.yml', '.yaml', '.xml', '.txt', '.md', '.cfg', '.ini'}


def should_ignore_path(path, ignored_dirs, ignored_files):
    """Verifica se um caminho deve ser ignorado com base em padrões."""
    # Verifica diretórios ignorados
    for part in path.parts:
        if part in ignored_dirs:
            return True

    # Verifica padrões de arquivo ignorados
    for pattern in ignored_files:
        if '*' in pattern:
            # Converte padrão glob para regex
            regex_pattern = pattern.replace('.', '\\.').replace('*', '.*')
            if re.match(regex_pattern, path.name):
                return True
        elif pattern == path.name:
            return True

    return False


def get_file_type(file_path):
    """Identifica o tipo de arquivo com base na extensão."""
    ext = file_path.suffix.lower()

    if ext == '.py':
        return 'PYTHON'
    elif ext in {'.json', '.yml', '.yaml'}:
        return 'CONFIG'
    elif ext in {'.txt', '.md'}:
        return 'TEXT'
    elif ext in {'.cfg', '.ini'}:
        return 'CONFIG'
    elif ext in {'.xml'}:
        return 'XML'
    else:
        return 'OTHER'


def read_file_content(file_path):
    """Lê o conteúdo de um arquivo, lidando com diferentes codificações e removendo bytes nulos."""
    # Verifica se é um arquivo de texto comum
    text_extensions = {'.py', '.txt', '.md', '.json', '.yml', '.yaml', '.cfg', '.ini', '.xml'}

    if file_path.suffix.lower() in text_extensions:
        # Tenta ler como texto com diferentes codificações
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    # Remove bytes nulos (caractere \x00)
                    content = content.replace('\x00', '')
                    return content
            except UnicodeDecodeError:
                continue

    # Se não conseguiu ler como texto ou não é um tipo de texto conhecido,
    # lê como binário, remove bytes nulos e codifica em base64
    try:
        with open(file_path, 'rb') as file:
            binary_content = file.read()
            # Remove bytes nulos
            binary_content = binary_content.replace(b'\x00', b'')
            return f"# BINARY CONTENT (base64):\n{base64.b64encode(binary_content).decode('ascii')}"
    except Exception as e:
        return f"# ERROR: Não foi possível ler o arquivo: {str(e)}"


def clean_text_for_claude(text):
    """Limpa o texto para garantir compatibilidade com o conhecimento do Claude."""
    if not text:
        return ""

    # Remove bytes nulos e outros caracteres problemáticos
    cleaned = text.replace('\x00', '')

    # Remove caracteres de controle não imprimíveis exceto quebras de linha e tabs
    cleaned = ''.join(c for c in cleaned if c == '\n' or c == '\t' or c == '\r' or (ord(c) >= 32 and ord(c) < 127) or (
            ord(c) >= 128 and ord(c) <= 255))

    return cleaned


def fetch_firebase_prompts(environment='homolog'):
    """
    Busca os prompts do Firebase para incluir na compilação.
    Requer que o Firebase esteja inicializado.
    """
    try:
        # Importa a classe FirebaseClient do projeto
        from dao.firebase_client import FirebaseClient, init_firebase
        from utils.base64_utils import decode_text

        # Inicializa o Firebase (se necessário)
        init_firebase(environment)

        print("Buscando prompts do Firebase...")

        # Tenta diferentes caminhos para encontrar o prompt base
        base_prompt_paths = [
            'system_prompt',  # Caminho original
            'system_prompts/base',  # Novo caminho modular
            'prompts/base',  # Alternativa
            'base_prompt'  # Outra alternativa
        ]

        base_prompt_data = None
        base_prompt_path = None

        # Tenta cada caminho até encontrar
        for path in base_prompt_paths:
            try:
                print(f"Tentando buscar prompt base em: {path}")
                data = FirebaseClient.fetch_data(path, environment)
                if data:
                    base_prompt_data = data
                    base_prompt_path = path
                    print(f"Prompt base encontrado em: {path}")
                    break
            except Exception as e:
                print(f"Erro ao buscar em {path}: {str(e)}")

        # Busca os contextos específicos - tenta diferentes caminhos
        context_paths = [
            'system_prompts/contexts',
            'prompts/contexts',
            'contexts'
        ]

        contexts_data = {}
        contexts_path = None

        # Tenta cada caminho até encontrar
        for path in context_paths:
            try:
                print(f"Tentando buscar contextos em: {path}")
                data = FirebaseClient.fetch_data(path, environment)
                if data:
                    contexts_data = data
                    contexts_path = path
                    print(f"Contextos encontrados em: {path}")
                    break
            except Exception as e:
                print(f"Erro ao buscar contextos em {path}: {str(e)}")

        # Registro de sucesso
        if base_prompt_data:
            print(f" Prompt base extraído de: {base_prompt_path}")
        else:
            print(" Prompt base não encontrado em nenhum caminho.")

        if contexts_data:
            print(f" {len(contexts_data)} contextos extraídos de: {contexts_path}")
            for context_name in contexts_data.keys():
                print(f"  - {context_name}")
        else:
            print(" Nenhum contexto encontrado.")

        # Resultado a ser retornado
        result = {
            "base_prompt": base_prompt_data,
            "base_prompt_path": base_prompt_path,
            "contexts": contexts_data,
            "contexts_path": contexts_path
        }

        print(f"Extração de prompts concluída.")
        return result
    except Exception as e:
        print(f"Erro ao buscar prompts do Firebase: {str(e)}")
        return {
            "base_prompt": None,
            "contexts": {},
            "error": str(e)
        }


def decode_base64_prompt(base64_string):
    """Decodifica um prompt codificado em Base64 e limpa caracteres inválidos."""
    if not base64_string:
        return "Prompt não encontrado"

    try:
        # Primeiro tenta importar a função decode_text personalizada
        try:
            from utils.base64_utils import decode_text
            decoded = decode_text(base64_string)
        except ImportError:
            # Se não encontrar a função personalizada, usa a implementação padrão
            base64_bytes = base64_string.encode('utf-8')
            text_bytes = base64.b64decode(base64_bytes)
            decoded = text_bytes.decode('utf-8')

        # Limpa o texto para compatibilidade com o Claude
        return clean_text_for_claude(decoded)
    except Exception as e:
        return f"Erro ao decodificar prompt: {str(e)}\nBase64 original: {base64_string[:50]}..."


def compile_project(project_path, output_file, ignored_dirs, ignored_files, included_extensions, add_headers=True,
                    include_prompts=True):
    """Compila todos os arquivos do projeto em um único arquivo compatível com o Claude."""
    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        print(f"Erro: O caminho '{project_path}' não é um diretório válido.")
        return False

    all_files = []

    # Coleta todos os arquivos relevantes
    for root, dirs, files in os.walk(project_path):
        # Remove diretórios ignorados in-place
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            file_path = Path(root) / file

            # Verifica se deve ignorar este arquivo
            if should_ignore_path(file_path, ignored_dirs, ignored_files):
                continue

            # Verifica se a extensão está incluída
            if file_path.suffix.lower() not in included_extensions:
                continue

            # Adiciona à lista de arquivos
            all_files.append(file_path)

    # Ordena os arquivos para uma saída consistente
    all_files.sort()

    # Prepara o conteúdo completo do arquivo antes de escrever
    full_content = f"""# PROJETO COMPILADO
# Gerado automaticamente a partir de {project_path}
# Total de arquivos: {len(all_files)}
# Data de geração: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""

    # Processa cada arquivo
    for file_path in all_files:
        rel_path = file_path.relative_to(project_path)
        file_type = get_file_type(file_path)
        content = read_file_content(file_path)

        # Adiciona cabeçalho do arquivo
        if add_headers:
            separator = '#' + '-' * 78
            full_content += f"\n{separator}\n"
            full_content += f"# ARQUIVO: {rel_path} ({file_type})\n"
            full_content += f"{separator}\n\n"

        # Adiciona o conteúdo limpo
        full_content += clean_text_for_claude(content)
        full_content += '\n\n'

    final_content = clean_text_for_claude(full_content)

    # Escreve o conteúdo no arquivo com codificação UTF-8 sem BOM
    try:
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(final_content)
    except Exception as e:
        print(f"Erro ao escrever arquivo de saída: {str(e)}")
        return False

    # Verifica o arquivo gerado para confirmar que está livre de bytes nulos
    try:
        with open(output_file, 'rb') as check_file:
            content = check_file.read()
            if b'\x00' in content:
                print("AVISO: O arquivo ainda contém bytes nulos!")

                # Tenta corrigir o arquivo manualmente
                print("Tentando corrigir o arquivo manualmente...")
                with open(output_file, 'rb') as in_file:
                    fixed_content = in_file.read().replace(b'\x00', b'')

                with open(output_file, 'wb') as out_file:
                    out_file.write(fixed_content)

                print("Arquivo corrigido manualmente.")
    except Exception as e:
        print(f"Erro ao verificar o arquivo final: {str(e)}")

    print(f"Projeto compilado com sucesso em '{output_file}'.")
    print(f"Total de arquivos processados: {len(all_files)}")
    return True


def validate_and_fix_file(file_path):
    """Verifica e corrige um arquivo para garantir que seja carregável no Claude."""
    try:
        print(f"Validando arquivo: {file_path}")
        with open(file_path, 'rb') as f:
            content = f.read()

        # Verifica bytes nulos
        if b'\x00' in content:
            print("Encontrados bytes nulos. Corrigindo...")
            fixed_content = content.replace(b'\x00', b'')

            # Backup do arquivo original
            backup_path = f"{file_path}.bak"
            with open(backup_path, 'wb') as f:
                f.write(content)
            print(f"Backup criado em: {backup_path}")

            # Salva arquivo corrigido
            with open(file_path, 'wb') as f:
                f.write(fixed_content)
            print(f"Arquivo corrigido e salvo como: {file_path}")
            return True
        else:
            print("Arquivo validado, não contém bytes nulos.")
            return True
    except Exception as e:
        print(f"Erro durante a validação/correção: {str(e)}")
        return False


def main():
    """Função principal - executada ao clicar com o botão direito no script."""
    # Configurações fixas para uso com clique do botão direito
    project_path = '..'  # Diretório pai (raiz do projeto)
    output_file = os.path.join(project_path, 'COMPILADO.txt')  # Nome do arquivo de saída fixo

    print("=== COMPILADOR DE PROJETO PYTHON PARA CLAUDE ===")
    print(f"Compilando todos os arquivos do diretório: {os.path.abspath(project_path)}")
    print(f"Gerando arquivo de saída: {output_file}")
    print("Ignorando pastas: " + ", ".join(IGNORED_DIRS))
    print("Processando...")

    # Executa a compilação
    start_time = time.time()
    success = compile_project(
        project_path,
        output_file,
        IGNORED_DIRS,
        IGNORED_FILES,
        INCLUDED_EXTENSIONS,
        True,  # Sempre adiciona cabeçalhos
        True  # Inclui prompts do Firebase
    )

    if success:
        # Valida e corrige o arquivo final
        fix_success = validate_and_fix_file(output_file)
        if fix_success:
            elapsed_time = time.time() - start_time
            print(f"Compilação concluída em {elapsed_time:.2f} segundos!")
            print(f"Arquivo '{output_file}' gerado com sucesso e validado para uso no Claude.")
        else:
            print(f"AVISO: O arquivo foi gerado mas pode conter problemas para carregamento no Claude.")
    else:
        print("Erro durante a compilação!")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
