"""
Testar busca de boletos conforme lembretes configurados
"""
import requests

API_URL = "https://assistente-ia-cob.onrender.com"

# Listar boletos disponiveis para ver quais o sistema encontraria
response = requests.get(f"{API_URL}/listar-boletos-teste")
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    data = response.json()
    print(f"\nTotal: {data.get('total')}")
    print(f"Mostrando: {data.get('mostrando')}")
    
    print("\nBoletos encontrados:\n")
    for boleto in data.get("boletos", []):
        print(f"Titulo: {boleto['titulo_id']}, Parcela: {boleto['parcela_id']}")
        print(f"  Cliente: {boleto['cliente_nome']}")
        print(f"  Telefone: {boleto['cliente_telefone']}")
        print(f"  Vencimento: {boleto['vencimento']}")
        print(f"  Valor: {boleto['valor']}")
        print()
