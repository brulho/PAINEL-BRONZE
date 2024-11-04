import requests
import json
import time
import os

# URL do seu repositório GitHub onde o JSON está armazenado
DATA_URL = "https://raw.githubusercontent.com/seu_usuario/seu_repositorio/main/links.json"

def carregar_dados():
    print("Carregando base de dados...")
    try:
        response = requests.get(DATA_URL)
        response.raise_for_status()  # Lança um erro se a requisição falhar
        dados = response.json()
        print("Concluído.")
        return dados
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return {}

def mostrar_topicos(dados):
    print("\nO que você quer acessar?")
    for i, topico in enumerate(dados.keys(), start=1):
        print(f"{i} - {topico}")
    escolha = int(input("Escolha um tópico: ")) - 1
    topico_selecionado = list(dados.keys())[escolha]
    print(f"\nLinks para {topico_selecionado}:")
    for link in dados[topico_selecionado]:
        print(link)

def main():
    dados = carregar_dados()
    if dados:
        mostrar_topicos(dados)

if __name__ == "__main__":
    main()