"""
Cliente Supabase para integração com banco de dados
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Criar cliente Supabase
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Cliente Supabase inicializado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao inicializar cliente Supabase: {e}")
else:
    print("⚠️ SUPABASE_URL ou SUPABASE_KEY não configurados no .env")


# ============================================================
# FUNÇÕES DE ACESSO AO BANCO DE DADOS
# ============================================================

def salvar_historico_cobranca(dados_cobranca: dict):
    """
    Salva registro de cobrança no histórico
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("historico_cobrancas").insert(dados_cobranca).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao salvar histórico de cobrança: {e}")
        return None


def atualizar_historico_cobranca(id: str, dados_atualizacao: dict):
    """
    Atualiza registro de cobrança no histórico
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("historico_cobrancas").update(dados_atualizacao).eq("id", id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao atualizar histórico de cobrança: {e}")
        return None


def buscar_historico_cobrancas(filtros: dict = None):
    """
    Busca histórico de cobranças com filtros opcionais
    """
    if not supabase:
        return []
    
    try:
        query = supabase.table("historico_cobrancas").select("*")
        
        if filtros:
            if "cliente_id" in filtros:
                query = query.eq("cliente_id", filtros["cliente_id"])
            if "status" in filtros:
                query = query.eq("status", filtros["status"])
            if "vencimento_inicio" in filtros:
                query = query.gte("vencimento", filtros["vencimento_inicio"])
            if "vencimento_fim" in filtros:
                query = query.lte("vencimento", filtros["vencimento_fim"])
        
        response = query.order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Erro ao buscar histórico de cobranças: {e}")
        return []


def salvar_log_mensagem(dados_log: dict):
    """
    Salva log de mensagem no banco de dados
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("logs_mensagens").insert(dados_log).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao salvar log de mensagem: {e}")
        return None


def buscar_configuracao_cobranca():
    """
    Busca configuração de cobrança do banco de dados
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("configuracoes_cobranca").select("*").limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao buscar configuração de cobrança: {e}")
        return None


def salvar_configuracao_cobranca(dados_config: dict):
    """
    Salva ou atualiza configuração de cobrança
    """
    if not supabase:
        return None
    
    try:
        # Verifica se já existe configuração
        config_existente = buscar_configuracao_cobranca()
        
        if config_existente:
            # Atualiza configuração existente
            response = supabase.table("configuracoes_cobranca").update(dados_config).eq("id", config_existente["id"]).execute()
            return response.data[0] if response.data else None
        else:
            # Cria nova configuração
            response = supabase.table("configuracoes_cobranca").insert(dados_config).execute()
            return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao salvar configuração de cobrança: {e}")
        return None


def verificar_cobranca_enviada(titulo_id: int, parcela_id: int, dias_antes: int):
    """
    Verifica se cobrança já foi enviada para evitar duplicação
    """
    if not supabase:
        return False
    
    try:
        response = supabase.table("historico_cobrancas").select("*").eq("titulo_id", titulo_id).eq("parcela_id", parcela_id).eq("dias_antes", dias_antes).eq("status", "enviado").execute()
        return len(response.data) > 0 if response.data else False
    except Exception as e:
        print(f"❌ Erro ao verificar cobrança enviada: {e}")
        return False
