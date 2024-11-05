# Bibliotecas padrão do Python
import os
import sys
import json
import time
import ctypes
import subprocess
from colorama import init, Fore
from rich.console import Console
from rich.progress import Progress
import requests
import pickle
from datetime import datetime
import threading
import sqlite3
from pathlib import Path

# Inicialização
init(autoreset=True)
console = Console()

# URL do JSON e constantes
DATA_URL = "https://raw.githubusercontent.com/brulho/PAINEL-BRONZE/refs/heads/main/dados.json"

# Constantes para cache e banco de dados
CACHE_FILE = "bronze_cache.pkl"
DB_FILE = "bronze.db"
CACHE_TIMEOUT = 3600  # 1 hora

# Adicionar adaptador de data/hora personalizado
sqlite3.register_adapter(datetime, lambda val: val.isoformat())
sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode()))

class BronzeDB:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BronzeDB, cls).__new__(cls)
            cls._instance.conn = sqlite3.connect(DB_FILE, timeout=30, isolation_level=None)
            cls._instance.conn.execute("PRAGMA journal_mode=WAL")
            cls._instance.criar_tabelas()
        return cls._instance
    
    def criar_tabelas(self):
        self.conn.executescript('''
            BEGIN;
            CREATE TABLE IF NOT EXISTS favoritos (
                url TEXT PRIMARY KEY,
                titulo TEXT,
                categoria TEXT,
                data_adicao TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caminho TEXT,
                data_acesso TIMESTAMP
            );
            COMMIT;
        ''')
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

# Gerenciamento de Cache
def salvar_cache(dados):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump({
            'dados': dados,
            'timestamp': datetime.now()
        }, f)

def carregar_cache():
    try:
        if not Path(CACHE_FILE).exists():
            return None
        
        with open(CACHE_FILE, 'rb') as f:
            cache = pickle.load(f)
            
        if (datetime.now() - cache['timestamp']).total_seconds() > CACHE_TIMEOUT:
            os.remove(CACHE_FILE)  # Remove cache expirado
            return None
            
        return cache['dados']
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao carregar cache: {str(e)}")
        if Path(CACHE_FILE).exists():
            os.remove(CACHE_FILE)  # Remove cache corrompido
        return None

# Funções para Favoritos
def adicionar_favorito(url, titulo, categoria):
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            # Verifica se já existe
            existente = conn.execute('SELECT 1 FROM favoritos WHERE url = ?', (url,)).fetchone()
            if existente:
                print_vermelho("\n[!] Este link já está nos favoritos!")
                time.sleep(1)
                return
                
            # Adiciona novo favorito
            conn.execute('''
                INSERT INTO favoritos (url, titulo, categoria, data_adicao)
                VALUES (?, ?, ?, ?)
            ''', (url, titulo, categoria, datetime.now()))
            conn.commit()
            print_vermelho("\n[+] Link adicionado aos favoritos!")
            time.sleep(1)
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao adicionar favorito: {str(e)}")
        time.sleep(1)

def mostrar_favoritos():
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            favoritos = conn.execute('''
                SELECT url, titulo, categoria, data_adicao 
                FROM favoritos 
                ORDER BY data_adicao DESC
            ''').fetchall()
            
            if not favoritos:
                print_vermelho("\n[!] Nenhum favorito encontrado!")
                return
            
            print_vermelho("\n=== FAVORITOS ===")
            for i, (url, titulo, categoria, data) in enumerate(favoritos, 1):
                print_vermelho(f"\n{i}. {titulo}")
                print_vermelho(f"   Categoria: {categoria}")
                print_vermelho(f"   URL: {url}")
                print_vermelho(f"   Adicionado em: {data}")
                
            print_vermelho("\nR - Remover favorito | V - Voltar")
            escolha = input_vermelho("\nEscolha uma opção: ").upper()
            
            if escolha == 'R':
                try:
                    num = int(input_vermelho("Digite o número do favorito para remover: "))
                    if 1 <= num <= len(favoritos):
                        url = favoritos[num-1][0]
                        remover_favorito(url)
                except ValueError:
                    print_vermelho("\n[!] Número inválido!")
                    time.sleep(1)
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao mostrar favoritos: {str(e)}")
        time.sleep(1)

def remover_favorito(url):
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute('DELETE FROM favoritos WHERE url = ?', (url,))
            conn.commit()
            print_vermelho("\n[+] Link removido dos favoritos!")
            time.sleep(1)
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao remover favorito: {str(e)}")
        time.sleep(1)

# Histórico de Navegação
def adicionar_historico(caminho):
    db = BronzeDB()
    db.conn.execute('''
        INSERT INTO historico (caminho, data_acesso)
        VALUES (?, ?)
    ''', (" > ".join(caminho), datetime.now()))
    db.conn.commit()

def mostrar_historico():
    try:
        # Criar nova conexão específica para esta função
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            historico = conn.execute('''
                SELECT DISTINCT caminho, MAX(data_acesso) as ultima_visita
                FROM historico 
                GROUP BY caminho 
                ORDER BY ultima_visita DESC 
                LIMIT 10
            ''').fetchall()
            
            if not historico:
                print_vermelho("\n[!] Nenhum histórico encontrado!")
                return
            
            print_vermelho("\n=== HISTÓRICO RECENTE ===")
            for i, (caminho, data) in enumerate(historico, 1):
                print_vermelho(f"\n{i}. {caminho}")
                print_vermelho(f"   Último acesso: {data}")
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao mostrar histórico: {str(e)}")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def print_vermelho(texto):
    print(Fore.RED + str(texto))

def input_vermelho(prompt):
    return input(Fore.RED + prompt)

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

# ASCII Art e mensagens iniciais
ASCII_ART = """
    ██████╗ ██████╗  ██████╗ ███╗   ██╗███████╗███████╗
    ██╔══██╗██╔══██╗██╔═══██╗████╗  ██║╚══███╔╝██╔════
    ██████╔╝██████╔╝██║   ██║██╔██╗ ██║  ██    █████╗
    ██╔══██╗██╔══██╗██║   ██║█║╚██╗██║ ███╔╝  ██╔══╝
    ██████╔╝██║  ██║╚██████╔╝██║ ╚████║███████╗███████╗
    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚══════╝
"""

def iniciar_sistema():
    if not is_admin():
        print_vermelho("[!] Este programa precisa ser executado como administrador!")
        input_vermelho("\nPressione Enter para sair...")
        sys.exit(1)

    limpar_tela()
    print_vermelho(ASCII_ART)
    print_vermelho("[!] SISTEMA DO BRONZE DE ACESSO RESTRITO [!]")
    print_vermelho("[*] APENAS MEMBROS DO BRONZE AUTORIZADOS [*]")
    print_vermelho("[+] TODAS AS OPERAÇÕES SÃO MONITORADAS E REGISTRADAS [+]\n")
    
    # Corrigido o problema do display
    progress = Progress(console=console)
    with progress:
        task = progress.add_task("[red]Iniciando sistema...", total=100)
        for i in range(100):
            time.sleep(0.02)
            progress.update(task, advance=1)
    
    limpar_tela()
    mostrar_menu_principal()

def mostrar_menu_principal():
    while True:
        limpar_tela()
        print(Fore.RED + ASCII_ART)
        print(Fore.RED + "╔═══════════════════════════════╗")
        print(Fore.RED + "║    PAINEL DO BRONZE v1.0      ║")
        print(Fore.RED + "╠═══════════════════════════════╣")
        print(Fore.RED + "║ 1 - Acessar Database          ║")
        print(Fore.RED + "║ 2 - Pesquisar Torrents        ║")
        print(Fore.RED + "║ 3 - Favoritos                 ║")
        print(Fore.RED + "║ 4 - Histórico                 ║")
        print(Fore.RED + "║ 0 - Encerrar Sessão           ║")
        print(Fore.RED + "╚═══════════════════════════════╝")
        
        try:
            escolha = input(Fore.RED + "\n[Bronze] Digite sua opção: ")
            if escolha == "0":
                print_slow(Fore.RED + "\n[!] Encerrando sessão do Bronze...")
                break
            elif escolha == "1":
                dados = carregar_dados()
                if dados:
                    mostrar_menu(dados)
            elif escolha == "2":
                pesquisar_torrents()
            elif escolha == "3":
                mostrar_favoritos()
                input_vermelho("\nPressione Enter para continuar...")
            elif escolha == "4":
                mostrar_historico()
                input_vermelho("\nPressione Enter para continuar...")
            else:
                print_vermelho("[!] Opção inválida!")
                time.sleep(1)
        except ValueError:
            print_vermelho("[!] Entrada inválida!")
            time.sleep(1)

def pesquisar_torrents():
    limpar_tela()
    print_vermelho(ASCII_ART)
    print_vermelho("\n[*] PESQUISA DE TORRENTS")
    print_vermelho("=" * 50)
    
    try:
        termo = input_vermelho("\nDigite o termo de busca: ")
        if not termo:
            print_vermelho("[!] Termo de busca não pode estar vazio!")
            time.sleep(2)
            return
        
        print_vermelho("\n[*] Pesquisando torrents...")
        
        # URL da API do The Pirate Bay
        url = f"https://apibay.org/q.php?q={termo}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            resultados = response.json()
            
            if not resultados or resultados[0].get('name') == 'No results returned':
                print_vermelho("\n[!] Nenhum resultado encontrado!")
                return
            
            print_vermelho("\nResultados encontrados:")
            print_vermelho("=" * 50)
            
            # Mostra apenas os primeiros 10 resultados
            for item in resultados[:10]:
                nome = item.get('name', 'N/A')
                tamanho = format_size(int(item.get('size', 0)))
                seeds = item.get('seeders', 'N/A')
                leeches = item.get('leechers', 'N/A')
                magnet = f"magnet:?xt=urn:btih:{item.get('info_hash')}"
                
                print_vermelho(f"\nNome: {nome}")
                print_vermelho(f"Tamanho: {tamanho}")
                print_vermelho(f"Seeds: {seeds}")
                print_vermelho(f"Leeches: {leeches}")
                print_vermelho(f"Magnet: {magnet}")
                print_vermelho("-" * 50)
            
        except requests.RequestException as e:
            print_vermelho(f"\n[!] Erro ao fazer a busca: {str(e)}")
            print_vermelho("[*] Tentando servidor alternativo...")
            
            # Tenta servidor alternativo
            try:
                alt_url = f"https://piratebay.party/api/search?q={termo}"
                response = requests.get(alt_url, headers=headers, timeout=10)
                response.raise_for_status()
                # ... processa resultados ...
            except:
                print_vermelho("[!] Falha também no servidor alternativo")
                
        except Exception as e:
            print_vermelho(f"\n[!] Erro inesperado: {str(e)}")
        
    except KeyboardInterrupt:
        print_vermelho("\n\n[!] Pesquisa cancelada pelo usuário.")
    except Exception as e:
        print_vermelho(f"\n[!] Erro inesperado: {str(e)}")
    
    input_vermelho("\nPressione Enter para voltar ao menu...")

def format_size(size_bytes):
    """Formata o tamanho em bytes para formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def carregar_dados():
    # Tenta carregar do cache primeiro
    dados_cache = carregar_cache()
    if dados_cache:
        return dados_cache
        
    console.print(Fore.RED + "Carregando base de dados do Bronze...")
    with Progress(console=console, transient=True) as progress:
        task = progress.add_task("[red]Carregando...", total=None)
        try:
            headers = {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            response = requests.get(DATA_URL, timeout=10, headers=headers)
            response.raise_for_status()
            dados = response.json()
            
            # Salva no cache
            salvar_cache(dados)
            return dados
            
        except requests.RequestException as e:
            print_vermelho(f"\n[!] Erro ao carregar dados: {str(e)}")
            print_vermelho("[*] Tentando carregar do cache...")
            
            dados_cache = carregar_cache()
            if dados_cache:
                print_vermelho("[+] Dados carregados do cache!")
                return dados_cache
            else:
                print_vermelho("[!] Nenhum cache disponível!")
                time.sleep(2)
                return None

def mostrar_menu(dados, nivel=0, caminho=[]):
    while True:
        limpar_tela()
        print(Fore.RED + ASCII_ART)
        print(Fore.RED + "\n" + " > ".join(caminho))
        print(Fore.RED + "\nO que você quer acessar?")
        
        opcoes = list(dados.keys())
        
        # Adicionar informação sobre submenus
        for i, opcao in enumerate(opcoes, 1):
            item = dados[opcao]
            if isinstance(item, dict):
                if 'url' in item:
                    print(Fore.RED + f"{i} - {opcao} [Link]")
                else:
                    print(Fore.RED + f"{i} - {opcao} [Pasta]")
            elif isinstance(item, list):
                print(Fore.RED + f"{i} - {opcao} [{len(item)} links]")
            else:
                print(Fore.RED + f"{i} - {opcao}")
        
        print(Fore.RED + ("0 - Voltar" if nivel > 0 else "0 - Sair"))
        
        try:
            escolha = input(Fore.RED + "\nEscolha uma opção: ")
            if escolha == "0":
                if nivel == 0:
                    print(Fore.RED + "Saindo...")
                    break
                else:
                    return
                
            if not escolha.isdigit() or int(escolha) < 1 or int(escolha) > len(opcoes):
                print(Fore.RED + "[!] Opção inválida!")
                time.sleep(1)
                continue
                
            escolha = int(escolha) - 1
            opcao_selecionada = opcoes[escolha]
            novo_caminho = caminho + [opcao_selecionada]
            item_selecionado = dados[opcao_selecionada]

            if isinstance(item_selecionado, dict):
                if 'url' in item_selecionado:
                    mostrar_links(opcao_selecionada, [item_selecionado], novo_caminho)
                else:
                    mostrar_menu(item_selecionado, nivel + 1, novo_caminho)
            elif isinstance(item_selecionado, list):
                mostrar_links(opcao_selecionada, item_selecionado, novo_caminho)
            elif isinstance(item_selecionado, str):
                mostrar_links(opcao_selecionada, [item_selecionado], novo_caminho)
            else:
                print(Fore.RED + "[!] Formato de dados inválido!")
                time.sleep(1)
                
        except ValueError:
            print(Fore.RED + "[!] Por favor, digite um número válido!")
            time.sleep(1)

def mostrar_links(titulo, links, caminho):
    while True:
        limpar_tela()
        print(Fore.RED + ASCII_ART)
        print(Fore.RED + "\n" + " > ".join(caminho))
        
        print(Fore.RED + "╔" + "═" * 70 + "╗")
        print(Fore.RED + f"║{titulo.center(70)}║")
        print(Fore.RED + "╠" + "═" * 70 + "╣")
        
        # Mostra os links numerados
        for i, link in enumerate(links, 1):
            if isinstance(link, dict) and 'url' in link:
                url = link['url']
                descricao = link.get('descrição', '')
                print(Fore.RED + f"║ {i}. {url:<65} ║")
                if descricao:
                    print(Fore.RED + f"║ → {descricao:<67}║")
            else:
                url = str(link)
                print(Fore.RED + f"║ {i}. {url:<65} ║")
        
        print(Fore.RED + "╠" + "═" * 70 + "╣")
        print(Fore.RED + "║ C - Copiar URL | F - Favoritar | V - Voltar                        ║")
        print(Fore.RED + "╚" + "═" * 70 + "╝")
        
        escolha = input_vermelho("\nEscolha uma opção: ").upper()
        
        if escolha == 'V':
            break
        elif escolha == 'F':
            try:
                num = int(input_vermelho("Digite o número do link para favoritar: "))
                if 1 <= num <= len(links):
                    link = links[num-1]
                    url = link['url'] if isinstance(link, dict) and 'url' in link else str(link)
                    adicionar_favorito(url, titulo, " > ".join(caminho))
                    time.sleep(1)
                else:
                    print_vermelho("\n[!] Número inválido!")
                    time.sleep(1)
            except ValueError:
                print_vermelho("\n[!] Por favor, digite um número válido!")
                time.sleep(1)

# Adicionar esta nova função para copiar para a área de transferência
def copiar_para_clipboard(texto):
    if os.name == 'nt':  # Windows
        comando = 'echo ' + texto.strip() + '| clip'
        os.system(comando)
    else:  # Linux/Unix
        try:
            import pyperclip
            pyperclip.copy(texto)
        except ImportError:
            print_vermelho("[!] Módulo pyperclip não encontrado. Instalando...")
            os.system('pip install pyperclip')
            import pyperclip
            pyperclip.copy(texto)

def print_slow(text):
    for char in text:
        print(Fore.RED + char, end='', flush=True)
        time.sleep(0.03)
    print()

def mostrar_historico():
    try:
        # Criar nova conexão específica para esta função
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            historico = conn.execute('''
                SELECT DISTINCT caminho, MAX(data_acesso) as ultima_visita
                FROM historico 
                GROUP BY caminho 
                ORDER BY ultima_visita DESC 
                LIMIT 10
            ''').fetchall()
            
            if not historico:
                print_vermelho("\n[!] Nenhum histórico encontrado!")
                return
            
            print_vermelho("\n=== HISTÓRICO RECENTE ===")
            for i, (caminho, data) in enumerate(historico, 1):
                print_vermelho(f"\n{i}. {caminho}")
                print_vermelho(f"   Último acesso: {data}")
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao mostrar histórico: {str(e)}")

if __name__ == "__main__":
    try:
        iniciar_sistema()
    except KeyboardInterrupt:
        print_vermelho("\n\n[!] Programa encerrado pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print_vermelho(f"\n[!] Erro inesperado: {str(e)}")
        input_vermelho("\nPressione Enter para sair...")
        sys.exit(1)