import subprocess
import os
import sys
import time
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin(executable_path):
    try:
        if not is_admin():
            print("\033[91m[DEBUG] Solicitando privilégios de administrador...\033[0m")
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                executable_path,
                None, 
                None, 
                1
            )
            return True
        return False
    except Exception as e:
        print(f"\033[91m[DEBUG] Erro ao elevar privilégios: {str(e)}\033[0m")
        return False

def main():
    # Caminho para o executável principal
    exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', 'bronze.exe')
    
    print("\033[91m[DEBUG] Iniciando sessão de debug...\033[0m")
    print(f"\033[91m[DEBUG] Executável principal: {exe_path}\033[0m")
    
    try:
        # Tenta executar com privilégios de administrador
        if run_as_admin(exe_path):
            print("\033[91m[DEBUG] Painel Bronze iniciado com privilégios elevados!\033[0m")
        else:
            print("\033[91m[DEBUG] Erro ao iniciar com privilégios elevados\033[0m")
            
        print("\033[91m[DEBUG] Console de debug ativo. Pressione Ctrl+C para encerrar...\033[0m")
        
        # Mantém o console de debug aberto
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\033[91m[DEBUG] Encerrando sessão de debug...\033[0m")
    except Exception as e:
        print(f"\033[91m[DEBUG] Erro: {str(e)}\033[0m")
    finally:
        print("\033[91m[DEBUG] Sessão finalizada.\033[0m")
        time.sleep(2)

if __name__ == "__main__":
    main()