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
    Busca configuração de cobrança do banco de dados com lembretes separados
    """
    if not supabase:
        return None
    
    try:
        # Buscar configuração
        response_config = supabase.table("configuracoes_cobranca").select("*").limit(1).execute()
        
        if not response_config.data:
            return None
        
        config = response_config.data[0]
        configuracao_id = config["id"]
        
        # Buscar lembretes da tabela separada
        response_lembretes = supabase.table("lembretes_cobranca").select("*").eq("configuracao_id", configuracao_id).execute()
        
        # Adicionar lembretes à configuração
        lembretes = []
        if response_lembretes.data:
            for lembrete in response_lembretes.data:
                lembretes.append({
                    "dias_antes": lembrete["dias_antes"],
                    "mensagem": lembrete["mensagem"],
                    "enviar_segunda_via": lembrete["enviar_segunda_via"]
                })
        
        config["lembretes"] = lembretes
        return config
    except Exception as e:
        print(f"❌ Erro ao buscar configuração de cobrança: {e}")
        return None


def salvar_configuracao_cobranca(dados_config: dict):
    """
    Salva ou atualiza configuração de cobrança com lembretes em tabela separada
    """
    if not supabase:
        print("⚠️ Cliente Supabase não inicializado")
        return None
    
    try:
        print(f"📝 Tentando salvar configuração: {dados_config}")
        
        # Extrair lembretes dos dados
        lembretes = dados_config.pop("lembretes", [])
        
        # Verifica se já existe configuração
        config_existente = buscar_configuracao_cobranca()
        
        if config_existente:
            print(f"🔄 Atualizando configuração existente ID: {config_existente['id']}")
            configuracao_id = config_existente["id"]
            
            # Atualiza configuração existente (sem lembretes)
            response = supabase.table("configuracoes_cobranca").update(dados_config).eq("id", configuracao_id).execute()
            
            # Deletar lembretes antigos
            supabase.table("lembretes_cobranca").delete().eq("configuracao_id", configuracao_id).execute()
            
            # Inserir novos lembretes
            for lembrete in lembretes:
                supabase.table("lembretes_cobranca").insert({
                    "configuracao_id": configuracao_id,
                    "dias_antes": lembrete["dias_antes"],
                    "mensagem": lembrete["mensagem"],
                    "enviar_segunda_via": lembrete["enviar_segunda_via"]
                }).execute()
            
            print(f"✅ Configuração atualizada com {len(lembretes)} lembretes")
            return response.data[0] if response.data else None
        else:
            print(f"➕ Criando nova configuração")
            # Cria nova configuração (sem lembretes)
            response = supabase.table("configuracoes_cobranca").insert(dados_config).execute()
            
            if response.data:
                configuracao_id = response.data[0]["id"]
                
                # Inserir lembretes
                for lembrete in lembretes:
                    supabase.table("lembretes_cobranca").insert({
                        "configuracao_id": configuracao_id,
                        "dias_antes": lembrete["dias_antes"],
                        "mensagem": lembrete["mensagem"],
                        "enviar_segunda_via": lembrete["enviar_segunda_via"]
                    }).execute()
                
                print(f"✅ Configuração criada com {len(lembretes)} lembretes")
            
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


def buscar_configuracao_sienge():
    """
    Busca configuração do Sienge no Supabase
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("configuracoes_sienge").select("*").limit(1).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao buscar configuração do Sienge: {e}")
        return None


def salvar_configuracao_sienge(dados_config: dict):
    """
    Salva configuração do Sienge no Supabase
    """
    if not supabase:
        return None
    
    try:
        config_existente = buscar_configuracao_sienge()
        
        if config_existente:
            # Atualizar configuração existente
            configuracao_id = config_existente["id"]
            response = supabase.table("configuracoes_sienge").update({
                "subdomain": dados_config.get("subdomain"),
                "username": dados_config.get("username"),
                "password": dados_config.get("password")
            }).eq("id", configuracao_id).execute()
            return response.data[0] if response.data else None
        else:
            # Criar nova configuração
            response = supabase.table("configuracoes_sienge").insert({
                "subdomain": dados_config.get("subdomain"),
                "username": dados_config.get("username"),
                "password": dados_config.get("password")
            }).execute()
            return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Erro ao salvar configuração do Sienge: {e}")
        return None
