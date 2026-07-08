import logging
import os
import json
from base64 import b64encode
from pathlib import Path

logging.info("🔧 Carregando configurações do Sienge...")

# Arquivo de configurações
CONFIG_FILE = Path(__file__).parent.parent / "sienge_config.json"

# ============================================================
# 💾 FUNÇÕES DE PERSISTÊNCIA
# ============================================================
def carregar_configuracoes():
    """Carrega configurações do arquivo JSON se existir"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"✅ Configurações carregadas do arquivo: {CONFIG_FILE}")
                return config
        except Exception as e:
            logging.warning(f"⚠️ Erro ao carregar arquivo de configurações: {e}")
    return {}

def salvar_configuracoes(subdomain: str, username: str, password: str):
    """Salva configurações no arquivo JSON"""
    try:
        config = {
            "subdomain": subdomain,
            "username": username,
            "password": password
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logging.info(f"✅ Configurações salvas no arquivo: {CONFIG_FILE}")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao salvar configurações: {e}")
        return False

# ============================================================
# 🔐 CONFIGURAÇÕES DE AUTENTICAÇÃO SIENGE
# ============================================================
# Prioriza variáveis de ambiente sobre arquivo de configuração
subdominio = os.getenv("SIENGE_SUBDOMINIO") or config_salva.get("subdomain") or "cctcontrol"
usuario = os.getenv("SIENGE_USERNAME") or config_salva.get("username") or "cctcontrol-api"
senha = os.getenv("SIENGE_PASSWORD") or config_salva.get("password") or "9SQ2MaNrFOeZOOuOAqeSRy7bYWYDDf85"

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
