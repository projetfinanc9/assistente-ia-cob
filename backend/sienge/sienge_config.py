import logging
import os
from base64 import b64encode

logging.info("🔧 Carregando configurações do Sienge...")

# ============================================================
# CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE (Variáveis de ambiente)
# ============================================================
subdominio = os.getenv("SIENGE_SUBDOMINIO")
usuario = os.getenv("SIENGE_USERNAME")
senha = os.getenv("SIENGE_PASSWORD")

logging.info(f"🔧 Configurações Sienge - Subdomain: {subdominio}, User: {usuario}")
logging.info(f"🔧 Variáveis de ambiente: SUBDOMAIN={os.getenv('SIENGE_SUBDOMINIO')}, USERNAME={os.getenv('SIENGE_USERNAME')}, PASSWORD={'***' if os.getenv('SIENGE_PASSWORD') else 'None'}")

BASE_URL = f"https://api.sienge.com.br/{subdominio}/public/api/v1"
_token = b64encode(f"{usuario}:{senha}".encode()).decode()

json_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "application/json",
    "Content-Type": "application/json",
}

# Cabeçalho para PDF
pdf_headers = {
    "Authorization": f"Basic {_token}",
    "accept": "*/*",
}

logging.info(f"✅ Configurações carregadas: {subdominio}@{BASE_URL}")
