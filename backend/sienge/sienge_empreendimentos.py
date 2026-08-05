import logging
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional
from .sienge_config import BASE_URL, json_headers

logging.warning("🚀 Rodando módulo sienge_empreendimentos.py (gestão de empreendimentos)")

# ============================================================
# API DE EMPREENDIMENTOS SIENGE
# ============================================================

def listar_empreendimentos_sienge(company_id: Optional[int] = None, enterprise_type: Optional[int] = None) -> List[Dict]:
    """
    Busca lista de empreendimentos no Sienge com paginação.
    
    Args:
        company_id: Filtra por empresa (opcional)
        enterprise_type: Tipo do empreendimento (1=Obra e Centro de custo, 2=Obra, 3=Centro de custo, 4=Centro de custo associado a obra)
    
    Returns:
        Lista de empreendimentos
    """
    try:
        url = f"{BASE_URL}/enterprises"
        all_results = []
        offset = 0
        limit = 100  # Limite por página
        
        while True:
            params = {}
            
            if company_id:
                params["companyId"] = company_id
            if enterprise_type:
                params["type"] = enterprise_type
            
            params["limit"] = limit
            params["offset"] = offset
            
            logging.info(f"📋 Buscando empreendimentos no Sienge: {url}")
            logging.info(f"📋 Parâmetros: {params}")
            
            r = requests.get(url, headers=json_headers, params=params, timeout=30)
            logging.info(f"📋 Status: {r.status_code}")
            
            if r.status_code != 200:
                logging.error(f"❌ Erro ao buscar empreendimentos: {r.status_code} - {r.text}")
                break
            
            data = r.json()
            results = data.get("results") or []
            
            if not results:
                break
            
            all_results.extend(results)
            logging.info(f"✅ {len(results)} empreendimentos nesta página (total até agora: {len(all_results)})")
            
            # Verificar se há mais páginas
            if len(results) < limit:
                break
            
            offset += limit
        
        logging.info(f"✅ {len(all_results)} empreendimentos encontrados no Sienge (total)")
        return all_results
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar empreendimentos do Sienge: {e}")
        return []


def buscar_detalhes_empreendimento(enterprise_id: int) -> Optional[Dict]:
    """
    Busca detalhes completos de um empreendimento específico.
    
    Args:
        enterprise_id: ID do empreendimento
    
    Returns:
        Detalhes do empreendimento ou None
    """
    try:
        url = f"{BASE_URL}/enterprises/{enterprise_id}"
        logging.info(f"🔍 Buscando detalhes do empreendimento {enterprise_id}")
        
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.info(f"🔍 Status: {r.status_code}")
        
        if r.status_code != 200:
            logging.error(f"❌ Erro ao buscar detalhes do empreendimento: {r.status_code} - {r.text}")
            return None
        
        data = r.json()
        logging.info(f"✅ Detalhes do empreendimento {enterprise_id} obtidos com sucesso")
        return data
        
    except Exception as e:
        logging.error(f"❌ Erro ao buscar detalhes do empreendimento {enterprise_id}: {e}")
        return None


def buscar_agrupamentos_empreendimento(enterprise_id: int) -> Optional[Dict]:
    """
    Busca agrupamentos de unidades de um empreendimento.
    
    Args:
        enterprise_id: ID do empreendimento
    
    Returns:
        Agrupamentos ou None
    """
    try:
        url = f"{BASE_URL}/enterprises/{enterprise_id}/groupings"
        logging.info(f"📦 Buscando agrupamentos do empreendimento {enterprise_id}")
        
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.info(f"📦 Status: {r.status_code}")
        
        if r.status_code != 200:
            logging.warning(f"⚠️ Erro ao buscar agrupamentos: {r.status_code}")
            return None
        
        data = r.json()
        logging.info(f"✅ Agrupamentos do empreendimento {enterprise_id} obtidos")
        return data
        
    except Exception as e:
        logging.warning(f"⚠️ Erro ao buscar agrupamentos do empreendimento {enterprise_id}: {e}")
        return None


# ============================================================
# FUNÇÕES DE SUPABASE
# ============================================================

def salvar_empreendimento_supabase(supabase_client, empreendimento_data: Dict) -> Dict:
    """
    Salva ou atualiza um empreendimento no Supabase.
    
    Args:
        supabase_client: Cliente do Supabase
        empreendimento_data: Dados do empreendimento
    
    Returns:
        Registro salvo no Supabase
    """
    try:
        # Extrair campos principais
        enterprise_id = empreendimento_data.get("id")
        enterprise_name = empreendimento_data.get("name")
        enterprise_type = empreendimento_data.get("type")
        company_id = empreendimento_data.get("companyId")
        
        logging.warning(f"💾 Salvando empreendimento {enterprise_id} - {enterprise_name}")
        
        # Usar companyId como cost_center_id (solução alternativa pois API de agrupamentos retorna 403)
        cost_center_ids = []
        if company_id:
            cost_center_ids = [company_id]
            logging.warning(f"📦 Usando companyId {company_id} como centro de custo para empreendimento {enterprise_id}")
        else:
            logging.warning(f"⚠️ Empreendimento {enterprise_id} não tem companyId")
        
        # Verificar se já existe
        existing = supabase_client.table("empreendimentos_cobranca").select("*").eq("enterprise_id", enterprise_id).execute()
        
        if existing.data:
            # Atualizar registro existente
            update_data = {
                "enterprise_name": enterprise_name,
                "enterprise_type": enterprise_type,
                "company_id": company_id,
                "cost_center_ids": cost_center_ids if cost_center_ids else None,
                "sienge_data": empreendimento_data,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Atualizar campos detalhados se disponíveis
            if "addressDetails" in empreendimento_data:
                update_data["address_details"] = empreendimento_data["addressDetails"]
            if "buildingStatus" in empreendimento_data:
                update_data["building_status"] = empreendimento_data["buildingStatus"]
            if "costCenterStatus" in empreendimento_data:
                update_data["cost_center_status"] = empreendimento_data["costCenterStatus"]
            if "buildingEnabledForIntegration" in empreendimento_data:
                update_data["building_enabled_for_integration"] = empreendimento_data["buildingEnabledForIntegration"]
            if "constructionDetails" in empreendimento_data:
                update_data["construction_details"] = empreendimento_data["constructionDetails"]
            if "salesDetails" in empreendimento_data:
                update_data["sales_details"] = empreendimento_data["salesDetails"]
            
            result = supabase_client.table("empreendimentos_cobranca").update(update_data).eq("enterprise_id", enterprise_id).execute()
            logging.info(f"🔄 Empreendimento {enterprise_id} atualizado no Supabase com {len(cost_center_ids)} centros de custo")
            return result.data[0]
        else:
            # Criar novo registro
            insert_data = {
                "enterprise_id": enterprise_id,
                "enterprise_name": enterprise_name,
                "enterprise_type": enterprise_type,
                "company_id": company_id,
                "cost_center_ids": cost_center_ids if cost_center_ids else None,
                "ativo": False,  # Default inativo
                "sienge_data": empreendimento_data
            }
            
            # Adicionar campos detalhados se disponíveis
            if "addressDetails" in empreendimento_data:
                insert_data["address_details"] = empreendimento_data["addressDetails"]
            if "buildingStatus" in empreendimento_data:
                insert_data["building_status"] = empreendimento_data["buildingStatus"]
            if "costCenterStatus" in empreendimento_data:
                insert_data["cost_center_status"] = empreendimento_data["costCenterStatus"]
            if "buildingEnabledForIntegration" in empreendimento_data:
                insert_data["building_enabled_for_integration"] = empreendimento_data["buildingEnabledForIntegration"]
            if "constructionDetails" in empreendimento_data:
                insert_data["construction_details"] = empreendimento_data["constructionDetails"]
            if "salesDetails" in empreendimento_data:
                insert_data["sales_details"] = empreendimento_data["salesDetails"]
            
            result = supabase_client.table("empreendimentos_cobranca").insert(insert_data).execute()
            logging.info(f"✅ Empreendimento {enterprise_id} criado no Supabase com {len(cost_center_ids)} centros de custo")
            return result.data[0]
            
    except Exception as e:
        logging.error(f"❌ Erro ao salvar empreendimento no Supabase: {e}")
        raise


def listar_empreendimentos_supabase(supabase_client, ativo_only: bool = False) -> List[Dict]:
    """
    Lista empreendimentos do Supabase.
    
    Args:
        supabase_client: Cliente do Supabase
        ativo_only: Se True, retorna apenas empreendimentos ativos
    
    Returns:
        Lista de empreendimentos
    """
    try:
        query = supabase_client.table("empreendimentos_cobranca").select("*")
        
        if ativo_only:
            query = query.eq("ativo", True)
        
        query = query.order("enterprise_name")
        
        result = query.execute()
        logging.info(f"📋 {len(result.data)} empreendimentos listados no Supabase")
        return result.data
        
    except Exception as e:
        logging.error(f"❌ Erro ao listar empreendimentos do Supabase: {e}")
        return []


def atualizar_status_empreendimento(supabase_client, enterprise_id: int, ativo: bool) -> Dict:
    """
    Atualiza o status de um empreendimento.
    
    Args:
        supabase_client: Cliente do Supabase
        enterprise_id: ID do empreendimento
        ativo: Novo status
    
    Returns:
        Registro atualizado
    """
    try:
        result = supabase_client.table("empreendimentos_cobranca").update({
            "ativo": ativo,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("enterprise_id", enterprise_id).execute()
        
        status_str = "ativado" if ativo else "desativado"
        logging.info(f"✅ Empreendimento {enterprise_id} {status_str} com sucesso")
        return result.data[0]
        
    except Exception as e:
        logging.error(f"❌ Erro ao atualizar status do empreendimento: {e}")
        raise


def obter_cost_centers_ativos(supabase_client) -> List[int]:
    """
    Obtém lista de IDs de centros de custo dos empreendimentos ativos.
    Usa company_ids como fallback se cost_center_ids estiver vazio.
    
    Args:
        supabase_client: Cliente do Supabase
    
    Returns:
        Lista de IDs de centros de custo
    """
    try:
        result = supabase_client.table("empreendimentos_cobranca").select("*").eq("ativo", True).execute()
        
        logging.warning(f"🔍 {len(result.data)} empreendimentos ativos encontrados no Supabase")
        
        cost_centers = []
        for item in result.data:
            enterprise_id = item.get("enterprise_id")
            enterprise_name = item.get("enterprise_name")
            cc_ids = item.get("cost_center_ids")
            company_id = item.get("company_id")
            
            # Priorizar cost_center_ids, usar company_id como fallback
            if cc_ids:
                cost_centers.extend(cc_ids)
                logging.warning(f"📋 Empreendimento {enterprise_id} ({enterprise_name}): cost_center_ids={cc_ids}")
            elif company_id:
                cost_centers.append(company_id)
                logging.warning(f"📋 Empreendimento {enterprise_id} ({enterprise_name}): usando company_id={company_id} como fallback")
            else:
                logging.warning(f"⚠️ Empreendimento {enterprise_id} ({enterprise_name}): sem cost_center_ids ou company_id")
        
        # Remove duplicatas
        cost_centers_unicos = list(set(cost_centers))
        logging.warning(f"🎯 {len(cost_centers_unicos)} centros de custo únicos encontrados em empreendimentos ativos")
        
        return cost_centers_unicos
        
    except Exception as e:
        logging.error(f"❌ Erro ao obter centros de custo ativos: {e}")
        return []


def salvar_log_sincronizacao(supabase_client, log_data: Dict) -> Dict:
    """
    Salva log de sincronização de empreendimentos.
    
    Args:
        supabase_client: Cliente do Supabase
        log_data: Dados do log
    
    Returns:
        Log salvo
    """
    try:
        result = supabase_client.table("logs_sincronizacao_empreendimentos").insert(log_data).execute()
        logging.info(f"📝 Log de sincronização salvo")
        return result.data[0]
        
    except Exception as e:
        logging.error(f"❌ Erro ao salvar log de sincronização: {e}")
        raise


# ============================================================
# FUNÇÃO PRINCIPAL DE SINCRONIZAÇÃO
# ============================================================

def sincronizar_empreendimentos(supabase_client, company_id: Optional[int] = None, enterprise_type: Optional[int] = None) -> Dict:
    """
    Sincroniza empreendimentos do Sienge com o Supabase.
    
    Args:
        supabase_client: Cliente do Supabase
        company_id: Filtra por empresa (opcional)
        enterprise_type: Tipo do empreendimento (opcional)
    
    Returns:
        Estatísticas da sincronização
    """
    inicio = datetime.now()
    logging.warning("🔄 Iniciando sincronização de empreendimentos...")
    
    stats = {
        "total_empreendimentos": 0,
        "novos_empreendimentos": 0,
        "empreendimentos_atualizados": 0,
        "erros": 0,
        "detalhes_erro": None,
        "duracao_segundos": 0
    }
    
    try:
        # Buscar empreendimentos do Sienge
        empreendimentos_sienge = listar_empreendimentos_sienge(company_id, enterprise_type)
        stats["total_empreendimentos"] = len(empreendimentos_sienge)
        
        if not empreendimentos_sienge:
            logging.warning("⚠️ Nenhum empreendimento encontrado no Sienge")
            stats["detalhes_erro"] = "Nenhum empreendimento encontrado no Sienge"
            return stats
        
        # Buscar empreendimentos existentes no Supabase
        existentes = listar_empreendimentos_supabase(supabase_client)
        existentes_ids = {e["enterprise_id"] for e in existentes}
        
        # Processar cada empreendimento
        for emp in empreendimentos_sienge:
            try:
                enterprise_id = emp.get("id")
                if not enterprise_id:
                    continue
                
                # Salvar no Supabase
                salvar_empreendimento_supabase(supabase_client, emp)
                
                # Contar estatísticas
                if enterprise_id in existentes_ids:
                    stats["empreendimentos_atualizados"] += 1
                else:
                    stats["novos_empreendimentos"] += 1
                    
            except Exception as e:
                stats["erros"] += 1
                logging.error(f"❌ Erro ao processar empreendimento {emp.get('id')}: {e}")
        
        # Calcular duração
        fim = datetime.now()
        stats["duracao_segundos"] = (fim - inicio).total_seconds()
        
        # Salvar log de sincronização
        log_data = {
            "total_empreendimentos": stats["total_empreendimentos"],
            "novos_empreendimentos": stats["novos_empreendimentos"],
            "empreendimentos_atualizados": stats["empreendimentos_atualizados"],
            "erros": stats["erros"],
            "detalhes_erro": stats["detalhes_erro"],
            "duracao_segundos": stats["duracao_segundos"]
        }
        salvar_log_sincronizacao(supabase_client, log_data)
        
        logging.warning(f"✅ Sincronização concluída: {stats['novos_empreendimentos']} novos, {stats['empreendimentos_atualizados']} atualizados, {stats['erros']} erros")
        return stats
        
    except Exception as e:
        stats["erros"] += 1
        stats["detalhes_erro"] = str(e)
        logging.error(f"❌ Erro na sincronização de empreendimentos: {e}")
        
        # Salvar log mesmo com erro
        fim = datetime.now()
        stats["duracao_segundos"] = (fim - inicio).total_seconds()
        log_data = {
            "total_empreendimentos": stats["total_empreendimentos"],
            "novos_empreendimentos": stats["novos_empreendimentos"],
            "empreendimentos_atualizados": stats["empreendimentos_atualizados"],
            "erros": stats["erros"],
            "detalhes_erro": stats["detalhes_erro"],
            "duracao_segundos": stats["duracao_segundos"]
        }
        salvar_log_sincronizacao(supabase_client, log_data)
        
        return stats