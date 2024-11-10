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

# Após as outras constantes (DATA_URL, CACHE_FILE, etc) e antes das classes/funções
CONFIÁVEIS = {
    'JOGOS': {
        'SCENE': [
            'CODEX', 'PLAZA', 'CPY', 'SKIDROW', 'RELOADED',
            'HOODLUM', 'RAZOR1911', 'PROPHET', 'FLT', 'DODI',
            'EMPRESS', 'STEAMPUNKS', 'ACTiVATED', 'ALI213'
        ],
        'P2P': [
            'FitGirl', 'ElAmigos', 'DODI', 'KaOs', 'Masquerade',
            'BlackBox', 'CorePack', 'xatab', 'RAVEN'
        ]
    },
    'SOFTWARE': {
        'SCENE': [
            'F4CG', 'URET', 'MAZE', 'DiGiTAL', 'CORE',
            'AMPED', 'ThumperDC', 'DVT', 'TSZ'
        ],
        'P2P': [
            'Diakov', 'RSLOAD', 'SOFT4PC', 'CRACKSurl',
            'SANET', 'TFPDL', 'SADEEMPC', 'CRACKSmod'
        ]
    },
    'FILMES': {
        'SCENE': [
            'SPARKS', 'AMIABLE', 'GECKOS', 'EVO', 'RARBG',
            'FUM', 'ROVERS', 'DRONES', 'CMRG', 'LOST'
        ],
        'P2P': [
            'YIFY', 'RARBG', 'QxR', 'UTR', 'STUTTERSHIT',
            'VYNDROS', 'SAMPA', 'ION10', 'PSA', 'FLUX'
        ]
    },
    'SERIES': {
        'SCENE': [
            'DIMENSION', 'DEFLATE', 'SYNCOPY', 'FLUX',
            'NTb', 'ION10', 'CAKES', 'TEPES', 'KINGS'
        ],
        'P2P': [
            'RARTV', 'ETHiCS', 'SMURF', 'TOMMY', 'KiNGS',
            'PROPER', 'AMZN', 'NF', 'WEBDL', 'iNTERNAL'
        ]
    }
}

MALICIOSOS = {
    'CONHECIDOS': [
        'FAKEINSTALL', 'MALWARELAB', 'CRYPTOMINER',
        'RANSOMGROUP', 'FAKECRACK', 'COINMINER',
        'BOTNET', 'TROJANDEV', 'MALWAREDIST',
        'FAKERELEASE', 'SCAMGROUP', 'FAKESCENE'
    ],
    'PADRÕES_SUSPEITOS': [
        'FREE-DOWNLOAD', 'HACK-TOOLS', 'CRACKED-2024',
        'PATCH-FIX', 'KEYGEN-WORKS', 'ACTIVATION-HACK',
        'PREMIUM-CRACK', 'UNLOCKED-VERSION', 'PRO-VERSION',
        'FULL-ACCESS', 'NO-SURVEY', 'WORKING-CRACK'
    ],
    'EXTENSÕES_PERIGOSAS': [
        '.exe.zip', '.js.scr', '.bat.pif', '.cmd.exe',
        '.vbs.exe', '.ps1.exe', '.msi.exe', '.dll.scr'
    ],
    'NOMES_SUSPEITOS': [
        'setup_crack', 'patch_fix', 'keygen_working',
        'activation_tool', 'license_generator',
        'premium_unlock', 'free_coins', 'hack_tool',
        'password_stealer', 'miner_config'
    ]
}

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
    """Registra o acesso no histórico"""
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute('''
                INSERT INTO historico (caminho, data_acesso)
                VALUES (?, ?)
            ''', (" > ".join(caminho), datetime.now()))
            conn.commit()
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao registrar histórico: {str(e)}")

def mostrar_historico():
    try:
        with sqlite3.connect(DB_FILE, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            historico = conn.execute('''
                SELECT DISTINCT caminho, MAX(data_acesso) as ultima_visita, 
                       COUNT(*) as total_acessos
                FROM historico 
                GROUP BY caminho 
                ORDER BY ultima_visita DESC 
                LIMIT 10
            ''').fetchall()
            
            if not historico:
                print_vermelho("\n[!] Nenhum histórico encontrado!")
                return
            
            print_vermelho("\n=== HISTÓRICO DE NAVEGAÇÃO ===")
            for i, (caminho, data, total) in enumerate(historico, 1):
                data_formatada = datetime.fromisoformat(data).strftime("%d/%m/%Y %H:%M")
                print_vermelho(f"\n{i}. Caminho acessado: {caminho}")
                print_vermelho(f"   Último acesso: {data_formatada}")
                print_vermelho(f"   Total de acessos: {total}")
            
            print_vermelho("\nL - Limpar histórico | V - Voltar")
            escolha = input_vermelho("\nEscolha uma opção: ").upper()
            
            if escolha == 'L':
                conn.execute('DELETE FROM historico')
                conn.commit()
                print_vermelho("\n[+] Histórico limpo com sucesso!")
                time.sleep(1.5)
                
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
                           :                                                      
                          t#,     L.                                            ,;
  .          j.          ;##W.    EW:        ,ft                              f#i 
  Ef.        EW,        :#L:WE    E##;       t#E                            .E#t  
  E#Wi       E##j      .KG  ,#D   E###t      t#E      ,##############Wf.   i#W,   
  E#K#D:     E###D.    EE    ;#f  E#fE#f     t#E       ........jW##Wt     L#D.    
  E#t,E#f.   E#jG#W;  f#.     t#i E#t D#G    t#E             tW##Kt     :K#Wfff;  
  E#WEE##Wt  E#t t##f :#G     GK  E#t  f#E.  t#E           tW##E;       i##WLLLLt 
  E##Ei;;;;. E#t  :K#E:;#L   LW.  E#t   t#K: t#E         tW##E;          .E#L     
  E#DWWt     E#KDDDD###it#f f#:   E#t    ;#W,t#E      .fW##D,              f#E:   
  E#t f#K;   E#f,t#Wi,,, f#D#;    E#t     :K#D#E    .f###D,                 ,WW;  
  E#Dfff##E, E#t  ;#W:    G#t     E#t      .E##E  .f####Gfffffffffff;        .D#; 
  jLLLLLLLLL;DWi   ,KK:    t      ..         G#E .fLLLLLLLLLLLLLLLLLi          tt 
                                              fE                                  
                                               ,                                  
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
        
        pagina = 1
        ITENS_POR_PAGINA = 10
        todos_resultados = []
        
        # Faz a busca inicial para ter todos os resultados
        url = f"https://apibay.org/q.php?q={termo}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            todos_resultados = response.json()
            
            if not todos_resultados or todos_resultados[0].get('name') == 'No results returned':
                print_vermelho("\n[!] Nenhum resultado encontrado!")
                input_vermelho("\nPressione Enter para voltar...")
                return
            
            total_paginas = (len(todos_resultados) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA
            
            while True:
                limpar_tela()
                print_vermelho(ASCII_ART)
                print_vermelho(f"\n[*] Resultados para: {termo}")
                print_vermelho(f"[*] Página {pagina} de {total_paginas}")
                print_vermelho("=" * 50)
                
                # Calcula o índice inicial e final para a página atual
                inicio = (pagina - 1) * ITENS_POR_PAGINA
                fim = min(inicio + ITENS_POR_PAGINA, len(todos_resultados))
                resultados_pagina = todos_resultados[inicio:fim]
                
                # Agora a numeração é contínua usando o índice inicial
                for i, item in enumerate(resultados_pagina, inicio + 1):
                    nome = item.get('name', 'N/A')
                    tamanho = format_size(int(item.get('size', 0)))
                    seeds = item.get('seeders', 'N/A')
                    leeches = item.get('leechers', 'N/A')
                    
                    print_vermelho(f"\n[{i}] {nome}")
                    print_vermelho(f"    Tamanho: {tamanho}")
                    print_vermelho(f"    Seeds: {seeds} | Leeches: {leeches}")
                    print_vermelho("-" * 50)
                
                # Menu de navegação
                print_vermelho("\nNavegação:")
                if pagina > 1:
                    print_vermelho("A - Página anterior")
                if pagina < total_paginas:
                    print_vermelho("P - Próxima página")
                print_vermelho("E - Escolher torrent")
                print_vermelho("V - Voltar ao menu")
                print_vermelho(f"\nPágina {pagina}/{total_paginas} - Total de {len(todos_resultados)} resultados")
                
                escolha = input_vermelho("\nEscolha uma opção: ").upper()
                
                if escolha == 'E':
                    try:
                        num = int(input_vermelho("\nDigite o número do torrent: "))
                        if inicio + 1 <= num <= fim:
                            item_selecionado = resultados_pagina[num - inicio - 1]
                            analise = analisar_torrent(item_selecionado)
                            
                            while True:
                                mostrar_detalhes_torrent(item_selecionado, analise)
                                sub_escolha = input_vermelho("\nEscolha uma opção: ").upper()
                                
                                if sub_escolha == 'C':
                                    magnet = f"magnet:?xt=urn:btih:{item_selecionado.get('info_hash')}"
                                    copiar_para_clipboard(magnet)
                                    print_vermelho("\n[+] Magnet link copiado para a área de transferência!")
                                    time.sleep(1.5)
                                elif sub_escolha == 'V':
                                    break
                    except ValueError:
                        print_vermelho("\n[!] Por favor, digite um número válido!")
                        time.sleep(1.5)
                elif escolha == 'P' and pagina < total_paginas:
                    pagina += 1
                elif escolha == 'A' and pagina > 1:
                    pagina -= 1
                elif escolha == 'V':
                    break
                else:
                    print_vermelho("\n[!] Opção inválida!")
                    time.sleep(1.5)
                
        except requests.RequestException as e:
            print_vermelho(f"\n[!] Erro ao fazer a busca: {str(e)}")
            print_vermelho("[*] Tentando servidor alternativo...")
            
            try:
                alt_url = f"https://piratebay.party/api/search?q={termo}"
                response = requests.get(alt_url, headers=headers, timeout=10)
                response.raise_for_status()
                todos_resultados = response.json()
            except:
                print_vermelho("[!] Falha também no servidor alternativo")
                
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
        
        # Adiciona o registro no histórico quando entrar em um novo menu
        if caminho:  # Só registra se não estiver no menu principal
            adicionar_historico(caminho)
        
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
        print_vermelho(ASCII_ART)
        print_vermelho("\n" + " > ".join(caminho))
        
        # Adiciona o registro no histórico quando visualizar links
        adicionar_historico(caminho)
        
        # Encontra o tamanho máximo necessário para a tabela
        max_width = max(
            len(titulo),
            max(len(str(link['url'] if isinstance(link, dict) else link)) for link in links),
            len("C - Copiar URL | F - Favoritar | V - Voltar")
        ) + 6  # Aumenta a margem
        
        # Garante que a largura é suficiente para todos os conteúdos
        max_width = max(max_width, 80)  # Largura mínima de 80 caracteres
        
        # Funções auxiliares para criar linhas da tabela
        def criar_borda(left, mid, right):
            return f"{left}{mid * max_width}{right}"
        
        def criar_linha_conteudo(texto, centralizar=False):
            if centralizar:
                espacos = max_width - len(texto)
                texto = texto.center(max_width)
            return f"║{texto}{' ' * (max_width - len(texto))}║"
        
        # Desenha a tabela
        print_vermelho(criar_borda("╔", "═", "╗"))
        print_vermelho(criar_linha_conteudo(titulo, centralizar=True))
        print_vermelho(criar_borda("╠", "═", "╣"))
        
        # Mostra os links numerados
        for i, link in enumerate(links, 1):
            if isinstance(link, dict) and 'url' in link:
                url = link['url']
                descricao = link.get('descrição', '')
                print_vermelho(criar_linha_conteudo(f" {i}. {url}"))
                if descricao:
                    print_vermelho(criar_linha_conteudo(f" → {descricao}"))
            else:
                url = str(link)
                print_vermelho(criar_linha_conteudo(f" {i}. {url}"))
            
            # Adiciona linha separadora se não for o último item
            if i < len(links):
                print_vermelho(criar_borda("╠", "═", "╣"))
        
        print_vermelho(criar_borda("╠", "═", "╣"))
        print_vermelho(criar_linha_conteudo(" C - Copiar URL | F - Favoritar | V - Voltar"))
        print_vermelho(criar_borda("╚", "═", "╝"))
        
        escolha = input_vermelho("\nEscolha uma opção: ").upper()
        
        if escolha == 'V':
            break
        elif escolha == 'C':
            try:
                num = int(input_vermelho("Digite o número do link para copiar: "))
                if 1 <= num <= len(links):
                    link = links[num-1]
                    url = link['url'] if isinstance(link, dict) and 'url' in link else str(link)
                    copiar_para_clipboard(url)
                    print_vermelho("\n[+] URL copiada para a área de transferência!")
                    time.sleep(1.5)
                else:
                    print_vermelho("\n[!] Número inválido!")
                    time.sleep(1)
            except ValueError:
                print_vermelho("\n[!] Por favor, digite um número válido!")
                time.sleep(1)
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
                SELECT DISTINCT caminho, MAX(data_acesso) as ultima_visita, 
                       COUNT(*) as total_acessos
                FROM historico 
                GROUP BY caminho 
                ORDER BY ultima_visita DESC 
                LIMIT 10
            ''').fetchall()
            
            if not historico:
                print_vermelho("\n[!] Nenhum histórico encontrado!")
                return
            
            print_vermelho("\n=== HISTÓRICO DE NAVEGAÇÃO ===")
            for i, (caminho, data, total) in enumerate(historico, 1):
                data_formatada = datetime.fromisoformat(data).strftime("%d/%m/%Y %H:%M")
                print_vermelho(f"\n{i}. Caminho acessado: {caminho}")
                print_vermelho(f"   Último acesso: {data_formatada}")
                print_vermelho(f"   Total de acessos: {total}")
            
            print_vermelho("\nL - Limpar histórico | V - Voltar")
            escolha = input_vermelho("\nEscolha uma opção: ").upper()
            
            if escolha == 'L':
                conn.execute('DELETE FROM historico')
                conn.commit()
                print_vermelho("\n[+] Histórico limpo com sucesso!")
                time.sleep(1.5)
                
    except Exception as e:
        print_vermelho(f"\n[!] Erro ao mostrar histórico: {str(e)}")

CATEGORIAS_DETALHADAS = {
    'JOGOS': {
        'AAA': {
            'min_size': 30_000_000_000,  # 30GB
            'max_size': 150_000_000_000, # 150GB
            'grupos_confiaveis': [
                'CODEX', 'EMPRESS', 'FLT', 'PLAZA', 'CPY', 
                'SKIDROW', 'RELOADED', 'RAZOR1911', 'HOODLUM',
                'PROPHET', 'STEAMPUNKS', 'ACTiVATED', 'ALI213',
                'DODI', 'RUNE', 'CHRONOS', 'DARKSiDERS',
                'EMPRESS', 'PARADOX', 'CONSPIR4CY', 'FAIRLIGHT',
                'DEVIANCE', '3DM', 'PLAZA', 'FCKDRM'
            ],
            'extensoes_esperadas': ['.iso', '.bin']
        },
        'INDIE': {
            'min_size': 100_000_000,     # 100MB
            'max_size': 30_000_000_000,  # 30GB
            'grupos_confiaveis': [
                'PLAZA', 'CODEX', 'SKIDROW', 'TiNYiSO',
                'DARKSiDERS', 'RAZOR1911', 'GOG', 'DOGE',
                'SiMPLEX', 'PROPHET', 'ENiGMA', 'TENOKE'
            ],
            'extensoes_esperadas': ['.iso', '.bin']
        },
        'REPACK': {
            'min_size': 5_000_000_000,   # 5GB
            'max_size': 80_000_000_000,  # 80GB
            'grupos_confiaveis': [
                'FitGirl', 'DODI', 'ElAmigos', 'KaOs',
                'Masquerade', 'BlackBox', 'CorePack', 'xatab',
                'RAVEN', 'R.G. Mechanics', 'Mr DJ', 'FreeGOG',
                'CPG Repacks', 'GNARLY', 'M4CKD0GE'
            ],
            'compressao_esperada': True
        }
    },
    'SOFTWARE': {
        'OS': {
            'min_size': 2_000_000_000,   # 2GB
            'max_size': 20_000_000_000,  # 20GB
            'grupos_confiaveis': [
                'MSDN', 'VLSC', 'Gen2', 'WindowsAddict',
                'Murphy78', 'abbodi1406', 'Ghost Spectre',
                'Rectify11', 'GHOST007', 'WZT', 'AIO'
            ],
            'extensoes_esperadas': ['.iso', '.wim']
        },
        'APPS': {
            'min_size': 1_000_000,       # 1MB
            'max_size': 10_000_000_000,  # 10GB
            'grupos_confiaveis': [
                'F4CG', 'MAZE', 'DiGiTAL', 'URET', 'CORE',
                'AMPED', 'ThumperDC', 'DVT', 'TSZ', 'CRD',
                'Diakov', 'RSLOAD', 'SOFT4PC', 'CRACKSurl',
                'SANET', 'TFPDL', 'SADEEMPC', 'CRACKSmod',
                'PainteR', 'FoXtrot', 'MESMERiZE', 'ZWT'
            ],
            'verificacao_extra': True
        }
    },
    'FILMES': {
        'HD': {
            'min_size': 8_000_000_000,   # 8GB
            'max_size': 30_000_000_000,  # 30GB
            'grupos_confiaveis': [
                'SPARKS', 'AMIABLE', 'GECKOS', 'EVO', 'RARBG',
                'FUM', 'ROVERS', 'DRONES', 'CMRG', 'LOST',
                'BLOW', 'VETO', 'FLAME', 'BAKED', 'DEMAND'
            ],
            'extensoes_esperadas': ['.mkv', '.mp4']
        },
        'REMUX': {
            'min_size': 15_000_000_000,  # 15GB
            'max_size': 100_000_000_000, # 100GB
            'grupos_confiaveis': [
                'FraMeSToR', 'EPSiLON', 'KRaLiMaRKo',
                'HDCLUB', 'HDMaNiAcS', 'iFT', 'HiFi',
                'DON', 'COASTER', 'BeyondHD', 'LEGi0N',
                'THRONE', 'SiCFLY', 'BMF', 'HDVN'
            ],
            'extensoes_esperadas': ['.mkv']
        },
        'WEB-DL': {
            'min_size': 2_000_000_000,   # 2GB
            'max_size': 15_000_000_000,  # 15GB
            'grupos_confiaveis': [
                'EVO', 'RARBG', 'ION10', 'NTG', 'CMRG',
                'STRONTiUM', 'SMURF', 'FLUX', 'TEPES',
                'MZABI', 'NEBULANCE', 'NAISU', 'APEX',
                'VOID', 'SCARE', 'EDGE', 'DAWN'
            ],
            'extensoes_esperadas': ['.mkv', '.mp4']
        }
    },
    'SERIES': {
        'EPISODIO': {
            'min_size': 500_000_000,     # 500MB
            'max_size': 5_000_000_000,   # 5GB
            'grupos_confiaveis': [
                'DIMENSION', 'DEFLATE', 'NTb', 'FLUX',
                'SYNCOPY', 'CAKES', 'TEPES', 'KINGS',
                'ION10', 'CRONE', 'NEBULANCE', 'GOSSIP',
                'EDITH', 'SMURF', 'SURCODE', 'RTFM'
            ],
            'extensoes_esperadas': ['.mkv', '.mp4']
        },
        'TEMPORADA': {
            'min_size': 5_000_000_000,   # 5GB
            'max_size': 100_000_000_000, # 100GB
            'grupos_confiaveis': [
                'FLUX', 'CAKES', 'TEPES', 'KINGS',
                'DIMENSION', 'DEFLATE', 'NTb', 'ION10',
                'SYNCOPY', 'NEBULANCE', 'GOSSIP', 'EDITH',
                'SMURF', 'SURCODE', 'RTFM', 'MZABI'
            ],
            'extensoes_esperadas': ['.mkv', '.mp4']
        }
    }
}

def verificar_seguranca(torrent):
    """Sistema robusto de verificação de segurança"""
    nome = torrent.get('name', '').upper()
    tamanho = int(torrent.get('size', 0))
    
    resultado = {
        'score': 70,  # Score inicial
        'alertas': [],
        'categoria_detectada': None,
        'subcategoria_detectada': None,
        'grupo_detectado': None,
        'verificacoes': {
            'tamanho': False,
            'grupo': False,
            'extensao': False,
            'seeds': False
        }
    }
    
    # Separar o nome em partes para melhor detecção
    partes_nome = nome.replace('-', ' ').replace('_', ' ').replace('.', ' ').split()
    
    # Primeiro, vamos tentar detectar o grupo diretamente
    for categoria, subcategorias in CATEGORIAS_DETALHADAS.items():
        for subcategoria, specs in subcategorias.items():
            for grupo in specs['grupos_confiaveis']:
                if grupo.upper() in partes_nome:  # Verifica cada parte do nome
                    resultado['verificacoes']['grupo'] = True
                    resultado['score'] += 20
                    resultado['grupo_detectado'] = grupo
                    resultado['categoria_detectada'] = categoria
                    resultado['subcategoria_detectada'] = subcategoria
                    break
            if resultado['grupo_detectado']:
                break
        if resultado['grupo_detectado']:
            break
    
    # Verifica tamanho
    if specs['min_size'] <= tamanho <= specs['max_size']:
        resultado['verificacoes']['tamanho'] = True
        resultado['score'] += 10
    
    # Verifica extensões se especificadas
    if 'extensoes_esperadas' in specs:
        for ext in specs['extensoes_esperadas']:
            if nome.endswith(ext.upper()):
                resultado['verificacoes']['extensao'] = True
                resultado['score'] += 10
                break
    
    # Verifica seeds/leechers
    seeds = int(torrent.get('seeders', 0))
    leeches = int(torrent.get('leechers', 0))
    ratio = seeds/max(leeches, 1)
    
    if seeds > 10 and ratio > 1:
        resultado['verificacoes']['seeds'] = True
        resultado['score'] += 10
    elif seeds == 0:
        resultado['score'] -= 20
        resultado['alertas'].append("⚠️ Sem seeds ativos")
    elif ratio < 0.5:
        resultado['score'] -= 10
        resultado['alertas'].append("⚠️ Baixa proporção de seeds")
    
    # Verifica grupos maliciosos
    for grupo in MALICIOSOS['CONHECIDOS']:
        if grupo.upper() in nome:
            resultado['score'] -= 50
            resultado['alertas'].append(f"⚠️ Grupo malicioso detectado: {grupo}")
    
    # Verifica padrões suspeitos
    for padrao in MALICIOSOS['PADRÕES_SUSPEITOS']:
        if padrao.upper() in nome:
            resultado['score'] -= 15
            resultado['alertas'].append(f"⚠️ Padrão suspeito detectado: {padrao}")
    
    # Verifica extensões perigosas
    for ext in MALICIOSOS['EXTENSÕES_PERIGOSAS']:
        if nome.endswith(ext.upper()):
            resultado['score'] -= 30
            resultado['alertas'].append(f"⚠️ Extensão perigosa detectada: {ext}")
    
    # Ajusta score final
    resultado['score'] = max(0, min(resultado['score'], 100))
    
    # Limita a 95% se não tiver todas as verificações positivas
    if resultado['score'] > 95:
        todas_verificacoes = all(resultado['verificacoes'].values())
        if not todas_verificacoes:
            resultado['score'] = 95
            resultado['alertas'].append("ℹ️ Score limitado a 95% por falta de verificaões completas")
    
    return resultado

def mostrar_detalhes_torrent(item, analise):
    """Mostra os detalhes do torrent com análise detalhada"""
    limpar_tela()
    print_vermelho(ASCII_ART)
    
    # Função auxiliar para criar separadores
    def print_separador(texto=""):
        print_vermelho("\n" + "=" * 50)
        if texto:
            print_vermelho(f"\n=== {texto} ===")
            print_vermelho("=" * 50)
    
    # Função para mostrar itens em lista
    def print_lista(items, prefix="• "):
        for item in items:
            print_vermelho(f"{prefix}{item}")
    
    # Cabeçalho
    print_separador("DETALHES DO TORRENT")
    
    # Informações básicas em formato de tabela
    info_basica = [
        f"Nome: {item.get('name')}",
        f"Tamanho: {format_size(int(item.get('size', 0)))}",
        f"Seeds: {item.get('seeders')} | Leeches: {item.get('leechers')}",
        f"Data de Upload: {analise['data_upload'].strftime('%d/%m/%Y %H:%M')}",
        f"Info Hash: {analise['info_hash']}"
    ]
    print_lista(info_basica)
    
    # Análise de Segurança
    print_separador("ANÁLISE DE SEGURANÇA")
    score = analise['score']
    
    # Mapa de níveis de risco
    RISK_LEVELS = {
        (80, 101): ("BAIXO RISCO", Fore.GREEN, "✅"),
        (60, 80): ("RISCO MODERADO", Fore.YELLOW, "⚠️"),
        (40, 60): ("ALTO RISCO", Fore.RED, "⚠️"),
        (0, 40): ("EXTREMAMENTE PERIGOSO", Fore.RED, "☠️")
    }
    
    # Determina o nível de risco
    for (min_score, max_score), (nivel, cor, icone) in RISK_LEVELS.items():
        if min_score <= score < max_score:
            print(cor + f"{icone} Score de Confiabilidade: {score}/100")
            print(cor + f"{icone} Nível de Risco: {nivel}")
            break
    
    # Análise Detalhada
    print_separador("ANÁLISE DETALHADA")
    
    # Idade do torrent
    idade_dias = (datetime.now() - analise['data_upload']).days
    idade_info = [f"Idade do Torrent: {idade_dias} dias"]
    if idade_dias < 7:
        idade_info.append("⚠️ Torrent muito recente, requer cautela adicional")
    elif idade_dias > 365:
        idade_info.append("✅ Torrent bem estabelecido, maior probabilidade de confiabilidade")
    print_lista(idade_info)
    
    # Análise de Seeds/Leechers
    seeds = int(item.get('seeders', 0))
    leeches = int(item.get('leechers', 0))
    ratio = seeds/max(leeches, 1)
    
    ratio_info = [f"Ratio Seeds/Leechers: {ratio:.2f}"]
    if ratio < 0.5:
        ratio_info.append("⚠️ Poucos seeds em relação aos leechers, possível honeypot")
    elif ratio > 5:
        ratio_info.append("✅ Boa proporção de seeds, indicando confiabilidade")
    elif seeds == 0:
        ratio_info.append("⚠️ Sem seeds ativos, download pode ser impossível")
    print_lista(ratio_info)
    
    # Análise de Tamanho
    tamanho = int(item.get('size', 0))
    tamanho_esperado = {
        'JOGO': (500_000_000, 150_000_000_000),  # 500MB - 150GB
        'FILME': (500_000_000, 15_000_000_000),   # 500MB - 15GB
        'SÉRIE': (100_000_000, 5_000_000_000),    # 100MB - 5GB
        'SOFTWARE': (1_000_000, 10_000_000_000)   # 1MB - 10GB
    }
    
    # Grupos detectados com categorização
    if analise['grupos']:
        print_vermelho("\n• Grupos Detectados:")
        for grupo in analise['grupos']:
            icone = "⚠️" if "MALICIOSO" in grupo else "✅"
            categoria = grupo.split("(")[-1].strip(")")
            print_vermelho(f"  {icone} {grupo}")
            if categoria in tamanho_esperado:
                min_size, max_size = tamanho_esperado[categoria]
                if not min_size <= tamanho <= max_size:
                    print_vermelho(f"   Tamanho suspeito para categoria {categoria}")
    else:
        print_vermelho("\n• Grupos: Nenhum grupo conhecido detectado")
        print_vermelho("  ⚠️ Sem confirmação de fonte confiável")
    
    # Alertas específicos
    if analise['detalhes']:
        print_vermelho("\n• Alertas de Segurança:")
        for detalhe in analise['detalhes']:
            print_vermelho(f"  {detalhe}")
    
    # Recomendações de Segurança
    print_separador("RECOMENDAÇÕES DE SEGURANÇA")
    
    RECOMENDACOES = {
        (80, 101): [
            "✅ Torrent considerado seguro",
            "✅ Origem confiável verificada",
            "✅ Pode prosseguir com o download normalmente",
            "ℹ️ Recomenda-se ainda usar antivírus atualizado",
            "ℹ️ Sempre verifique a integridade dos arquivos após o download"
        ],
        (60, 80): [
            "⚠️ Torrent com risco moderado",
            "ℹ️ Verificar arquivo com antivírus antes de executar",
            "ℹ️ Recomenda-se usar sandbox para primeira execução",
            "ℹ️ Monitore atividades suspeitas após instalação",
            "ℹ️ Verifique checksums se disponíveis"
        ],
        (40, 60): [
            "⚠️ ALTO RISCO - CUIDADO REDOBRADO",
            "⚠️ Forte possibilidade de malware/vírus",
            "ℹ️ Use VM isolada se precisar realmente baixar",
            "❌ Não execute em sistema principal",
            "ℹ️ Análise em sandbox obrigatória",
            "ℹ️ Considere fontes alternativas"
        ],
        (0, 40): [
            "☠️ PERIGO - NÃO RECOMENDADO",
            "☠️ Altíssimo risco de malware/ransomware",
            "❌ Download fortemente desencorajado",
            "ℹ️ Procure fontes alternativas mais seguras",
            "⚠️ Possível honeypot/armadilha",
            "❌ Não baixe em hipótese alguma"
        ]
    }
    
    for (min_score, max_score), recomendacoes in RECOMENDACOES.items():
        if min_score <= score < max_score:
            print_lista(recomendacoes)
            break
    
    # Opções
    print_separador()
    print_vermelho("\nOpções:")
    print_lista([
        "C - Copiar Magnet Link",
        "H - Ver Hash em VirusTotal",
        "V - Voltar"
    ])

def analisar_torrent(item):
    """Analisa um torrent usando o novo sistema de verificação"""
    resultado = verificar_seguranca(item)
    
    return {
        'score': resultado['score'],
        'grupos': [resultado['grupo_detectado']] if resultado['grupo_detectado'] else [],
        'detalhes': resultado['alertas'],
        'data_upload': datetime.fromtimestamp(int(item.get('added', 0))),
        'info_hash': item.get('info_hash', ''),
        'categoria': resultado['categoria_detectada'],
        'subcategoria': resultado['subcategoria_detectada'],
        'verificacoes': resultado['verificacoes']
    }

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