"""
Gerar chave de criptografia para tokens WhatsApp
"""
from cryptography.fernet import Fernet

# Gerar chave
key = Fernet.generate_key()
print("Chave de criptografia gerada:")
print(key.decode())
print("\nAdicione esta chave ao .env como:")
print(f"ENCRYPTION_KEY={key.decode()}")
