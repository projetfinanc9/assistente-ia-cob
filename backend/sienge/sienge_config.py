import logging
import os
from base64 import b64encode

logging.info("🔧 Carregando configurações do Sienge...")

# ============================================================
# � CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE (Supabase)
# ============================================================
# Carrega configurações do Supabase
subdominio = "cctcontrol"
usuario = "cctcontrol-api"
senha = "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

# Tenta carregar do Supabase
try:
    from supabase_client import buscar_configuracao_sienge
    config_supabase = buscar_configuracao_sienge()
    if config_supabase:
        subdominio = config_supabase.get("subdomain", subdominio)
        usuario = config_supabase.get("username", usuario)
        senha = config_supabase.get("password", senha)
        logging.info(f"✅ Configurações carregadas do Supabase")
    else:
        logging.warning(f"⚠️ Nenhuma configuração encontrada no Supabase, usando valores padrão")
except Exception as e:
    logging.warning(f"⚠️ Erro ao carregar configurações do Supabase: {e}")

# Prioriza variáveis de ambiente sobre Supabase
subdominio = os.getenv("SIENGE_SUBDOMINIO") or subdominio
usuario = os.getenv("SIENGE_USERNAME") or usuario
senha = os.getenv("SIENGE_PASSWORD") or senha

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
