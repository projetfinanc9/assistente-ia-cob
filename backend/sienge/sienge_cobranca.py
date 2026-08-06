import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import re
import json
from pathlib import Path
from .sienge_config import BASE_URL, json_headers
from .sienge_boletos import buscar_cliente_por_documento, gerar_link_boleto

# ============================================================
# 💾 SISTEMA DE CACHE
# ============================================================
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def obter_dados_cache(cache_key: str, validade_horas: int = 24) -> Dict:
    """Obtém dados do cache se ainda válido"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Verificar validade
        cache_time = datetime.fromisoformat(cache_data.get("timestamp", ""))
        if datetime.now() - cache_time > timedelta(hours=validade_horas):
            logging.warning(f"🔄 Cache {cache_key} expirado")
            return None
        
        logging.warning(f"✅ Cache {cache_key} válido (idade: {(datetime.now() - cache_time).total_seconds() / 3600:.1f}h)")
        return cache_data.get("data")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao ler cache {cache_key}: {e}")
        return None

def salvar_cache(cache_key: str, data: Dict):
    """Salva dados no cache"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.warning(f"⚠️ Erro ao salvar cache {cache_key}: {e}")

def invalidar_cache(cache_key: str):
    """Invalida um cache específico (deleta o arquivo)"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if cache_file.exists():
        try:
            cache_file.unlink()
            logging.warning(f"🗑️ Cache {cache_key} invalidado com sucesso")
            return True
        except Exception as e:
            logging.warning(f"⚠️ Erro ao invalidar cache {cache_key}: {e}")
            return False
    else:
        logging.warning(f"⚠️ Cache {cache_key} não existe")
        return False

logging.warning("🔔 Rodando módulo sienge_cobranca.py (sistema de cobrança automática com suporte a CNPJ)")

# ============================================================
# 💾 CONFIGURAÇÕES DE COBRANÇA (Supabase)
# ============================================================
def carregar_configuracao_cobranca():
    """Carrega configurações de cobrança do Supabase"""
    try:
        from supabase_client import buscar_configuracao_cobranca
        config_supabase = buscar_configuracao_cobranca()
        
        if config_supabase:
            logging.info(f"✅ Configuração de cobrança carregada do Supabase: {len(config_supabase.get('lembretes', []))} lembretes")
            return {
                "ativo": config_supabase.get("ativo", False),
                "horario_execucao": config_supabase.get("horario_execucao", "09:00"),
                "mensagem_atendimento": config_supabase.get("mensagem_atendimento", "Olá, esse número é usado apenas para envio automático. Caso tenha alguma dúvida, fale com um de nossos atendentes pelo número (91) 9999-9999"),
                "lembretes": config_supabase.get("lembretes", [])
            }
    except Exception as e:
        logging.warning(f"⚠️ Erro ao carregar configuração do Supabase: {e}")
    
    # Configuração padrão
    return {
        "ativo": False,
        "horario_execucao": "09:00",
        "mensagem_atendimento": "Olá, esse número é usado apenas para envio automático. Caso tenha alguma dúvida, fale com um de nossos atendentes pelo número (91) 9999-9999",
        "lembretes": [
            {
                "dias_antes": -5,
                "mensagem": "Olá {cliente}, seu boleto vence em 5 dias. Valor: R$ {valor}",
                "enviar_segunda_via": True
            },
            {
                "dias_antes": -1,
                "mensagem": "Olá {cliente}, seu boleto vence amanhã! Valor: R$ {valor}",
                "enviar_segunda_via": True
            }
        ]
    }

# ============================================================
# 🔍 FUNÇÕES AUXILIARES
# ============================================================


def listar_boletos_por_cliente(cliente_id: int, usar_cache: bool = True):
    """Lista boletos/títulos vinculados a um cliente com cache."""
    cache_key = f"boletos_cliente_{cliente_id}"
    
    # Tentar obter do cache
    if usar_cache:
        dados_cache = obter_dados_cache(cache_key, validade_horas=24)
        if dados_cache is not None:
            logging.warning(f"📄 Cache hit para boletos do cliente {cliente_id}")
            return dados_cache
    
    # Buscar da API
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        logging.warning(f"⚠️ Erro ao buscar boletos do cliente {cliente_id}: {r.status_code}")
        return []
    data = r.json()
    results = data.get("results") or []
    logging.warning(f"📄 API retornou {len(results)} boletos para cliente {cliente_id}")
    
    # Salvar no cache
    if results:
        salvar_cache(cache_key, results)
        logging.warning(f"� Boletos do cliente {cliente_id} cacheados")
    
    return results


def listar_parcelas(titulo_id: int, usar_cache: bool = True):
    """Lista parcelas de um título com cache."""
    if not titulo_id:
        return []
    
    cache_key = f"parcelas_titulo_{titulo_id}"
    
    # Tentar obter do cache
    if usar_cache:
        dados_cache = obter_dados_cache(cache_key, validade_horas=24)
        if dados_cache is not None:
            logging.warning(f"📦 Cache hit para parcelas do título {titulo_id}")
            return dados_cache
    
    # Buscar da API
    url = f"{BASE_URL}/accounts-receivable/receivable-bills/{titulo_id}/installments"
    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        return []
    results = r.json().get("results") or []
    
    # Salvar no cache
    if results:
        salvar_cache(cache_key, results)
        logging.warning(f"💾 Parcelas do título {titulo_id} cacheadas")
    
    return results


def tem_boleto_apto(titulo_id: int, installment_id: int) -> tuple[bool, str | None]:
    """
    Verifica se a parcela é apta pra segunda via chamando a API diretamente.
    Retorna (apta, urlReport).
    Usa cache para reduzir requisições ao Sienge.
    """
    import time
    cache_key = f"boleto_apto_{titulo_id}_{installment_id}"
    
    # Tentar obter do cache (24h - aptidão não muda frequentemente)
    cache_result = obter_dados_cache(cache_key, validade_horas=24)
    if cache_result is not None:
        logging.warning(f"💾 Cache hit para parcela {installment_id}: {cache_result}")
        return cache_result
    
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": installment_id}
    max_retries = 3
    
    for tentativa in range(1, max_retries + 1):
        r = requests.get(url, headers=json_headers, params=params, timeout=30)
        
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                url_report = results[0].get("urlReport")
                logging.warning(f"✅ Parcela {installment_id} apta: urlReport={url_report}")
                salvar_cache(cache_key, (True, url_report))
                return True, url_report
            salvar_cache(cache_key, (False, None))
            return False, None
        
        if r.status_code == 422:
            # Parcela não apta: sem cobrança, nosso número zerado ou saldo zerado
            error_msg = r.json().get('clientMessage', 'Erro desconhecido')
            logging.warning(f"⏭️ Parcela {installment_id} não apta: {error_msg}")
            salvar_cache(cache_key, (False, None))
            return False, None
        
        if r.status_code == 429:
            wait_time = 2 * tentativa
            logging.warning(f"⚠️ Erro 429 (Too Many Requests) ao checar parcela {installment_id}. Aguardando {wait_time}s antes de tentar novamente...")
            time.sleep(wait_time)
            continue
        
        # Erro 403 (permissão negada) - usar fallback assumindo que parcela é apta
        if r.status_code == 403:
            logging.warning(f"⚠️ API payment-slip-notification retornou 403 (sem permissão)")
            logging.warning(f"🔄 Usando fallback: assumindo parcela {installment_id} apta (foi encontrada via bulk-data)")
            salvar_cache(cache_key, (True, None))
            return True, None
        
        # outros erros (401, 500, etc) — loga separado pra não confundir com "não apta"
        logging.warning(f"⚠️ Erro inesperado ({r.status_code}) ao checar parcela {installment_id} do título {titulo_id}")
        break
    
    # Fallback: se a parcela foi encontrada via bulk-data, assumir que é apta
    logging.warning(f"⚠️ Não foi possível verificar aptidão via API, assumindo apta por fallback")
    salvar_cache(cache_key, (True, None))
    return True, None


def listar_parcelas_por_periodo_bulk(data_inicio: str, data_fim: str, cost_centers_ids: Optional[List[int]] = None) -> List[Dict]:
    """
    Usa API Bulk-data para buscar parcelas por período de vencimento.
    Economia massiva de requisições comparado à API tradicional.
    
    Args:
        data_inicio: Data início do período
        data_fim: Data fim do período
        cost_centers_ids: Lista de IDs de centros de custo para filtrar (opcional)
    """
    # Criar chave de cache incluindo os centros de custo
    cache_key_suffix = f"_{','.join(map(str, cost_centers_ids))}" if cost_centers_ids else ""
    cache_key = f"bulk_parcelas_{data_inicio}_{data_fim}{cache_key_suffix}"
    
    # Tentar obter do cache
    dados_cache = obter_dados_cache(cache_key, validade_horas=1)  # Cache de 1h para dados de período
    if dados_cache is not None:
        logging.warning(f"📦 Cache hit para bulk data {data_inicio} a {data_fim}")
        return dados_cache
    
    # Usar API Bulk-data com filtro de vencimento (selectionType=D)
    url = f"{BASE_URL.replace('/api/v1', '/api/bulk-data/v1')}/income"
    params = {
        "startDate": data_inicio,
        "endDate": data_fim,
        "selectionType": "D"  # D = data de vencimento da parcela
    }
    
    # Adicionar filtro de enterprise_codes se fornecidos
    if cost_centers_ids:
        params["enterpriseCode"] = cost_centers_ids
        logging.warning(f"🎯 Filtrando por enterprise_codes: {cost_centers_ids}")
    
    logging.warning(f"🔍 Buscando parcelas via Bulk-data: {data_inicio} a {data_fim}")
    logging.warning(f"🔗 URL: {url}")
    logging.warning(f"🔑 Headers: {json_headers}")
    logging.warning(f"📋 Params: {params}")
    r = requests.get(url, headers=json_headers, params=params, timeout=60)
    
    if r.status_code != 200:
        logging.warning(f"⚠️ Erro ao buscar bulk data: {r.status_code}")
        logging.warning(f"⚠️ Response: {r.text[:500]}")
        return []
    
    data = r.json()
    results = data.get("data", [])
    
    # Salvar no cache (incluir enterprise_codes na chave para invalidar quando filtro mudar)
    if results:
        cache_key_completo = f"{cache_key}_{'_'.join(map(str, sorted(cost_centers_ids)))}" if cost_centers_ids else cache_key
        salvar_cache(cache_key_completo, results)
        logging.warning(f"💾 {len(results)} parcelas cacheadas via Bulk-data")
    
    return results


def boleto_existe(titulo_id: int, parcela_id: int) -> bool:
    """Verifica se existe segunda via real para essa parcela."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}
    try:
        r = requests.get(url, headers=json_headers, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            if results and results[0].get("urlReport"):
                return True
    except Exception as e:
        logging.error(f"Erro ao verificar boleto ({titulo_id}/{parcela_id}): {e}")
    return False


def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """Gera link da segunda via do boleto."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    if r.status_code == 200:
        try:
            data = r.json()
            results = data.get("results") or []
            if results and isinstance(results, list):
                result = results[0]
                link = result.get("urlReport")
                linha_digitavel = result.get("digitableNumber")
                if link:
                    return f"📄 **Segunda via gerada!**\n🔗 [Clique aqui]({link})\n💳 **Linha:** `{linha_digitavel}`"
        except Exception as e:
            logging.exception("Erro ao processar resposta do boleto:")
            return f"❌ Erro ao processar boleto: {e}"
    return f"❌ Erro ao gerar boleto ({r.status_code})."


def baixar_pdf_boleto(titulo_id: int, parcela_id: int, pdf_url: str = None) -> bytes:
    """
    Baixa o PDF do boleto da API Sienge.
    Se pdf_url for fornecido, usa diretamente (evita requisição duplicada).
    Caso contrário, verifica se a parcela é apta antes de baixar.
    Retorna o conteúdo do PDF em bytes ou None se houver erro.
    """
    # Se não foi fornecida URL, verifica se a parcela é apta
    if not pdf_url:
        apta, pdf_url = tem_boleto_apto(titulo_id, parcela_id)
        if not apta or not pdf_url:
            logging.warning(f"⚠️ Parcela {titulo_id}/{parcela_id} não apta ou sem URL de PDF")
            return None
    
    try:
        logging.warning(f"📥 Baixando PDF do boleto {titulo_id}/{parcela_id}")
        pdf_response = requests.get(pdf_url, timeout=30)
        if pdf_response.status_code == 200:
            logging.warning(f"✅ PDF baixado com sucesso ({len(pdf_response.content)} bytes)")
            return pdf_response.content
        else:
            logging.warning(f"⚠️ Erro ao baixar PDF: {pdf_response.status_code}")
    except Exception as e:
        logging.error(f"❌ Erro ao baixar PDF do boleto: {e}")
    
    return None


# ============================================================
# 📅 VERIFICAR BOLETOS VENCENDO (USANDO API BULK-DATA)
# ============================================================
def verificar_boletos_vencendo() -> List[Dict]:
    """
    Busca boletos vencendo usando API Bulk-data com filtros de data.
    Economia massiva de requisições comparado à API tradicional.
    Retorna lista de dicionários com informações do cliente e boletos.
    """
    config = carregar_configuracao_cobranca()
    logging.warning(f"🔧 Configuração carregada: {config}")
    
    if not config.get("ativo"):
        logging.warning("⚠️ Sistema de cobrança automática está desativado")
        return []
    
    lembretes = config.get("lembretes", [])
    if not lembretes:
        logging.warning("⚠️ Nenhum lembrete configurado")
        return []
    
    # Obter centros de custo dos empreendimentos ativos
    try:
        from supabase_client import supabase
        from sienge.sienge_empreendimentos import obter_cost_centers_ativos
        
        cost_centers_ids = obter_cost_centers_ativos(supabase)
        
        if not cost_centers_ids:
            logging.warning("⚠️ Nenhum centro de custo encontrado em empreendimentos ativos")
            # Tentar usar company_ids como fallback
            result = supabase.table("empreendimentos_cobranca").select("company_id").eq("ativo", True).execute()
            company_ids = []
            for item in result.data:
                if item.get("company_id"):
                    company_ids.append(item["company_id"])
            
            if company_ids:
                cost_centers_ids = list(set(company_ids))
                logging.warning(f"🔄 Usando {len(cost_centers_ids)} company_ids como fallback para centros de custo")
            else:
                logging.warning("⚠️ Nenhum company_id encontrado também, usando todos os empreendimentos")
                cost_centers_ids = None
        else:
            logging.warning(f"🎯 Filtrando cobrança para {len(cost_centers_ids)} centros de custo de empreendimentos ativos")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao obter centros de custo ativos, usando todos: {e}")
        cost_centers_ids = None
    
    logging.warning(f"🔍 Verificando boletos com {len(lembretes)} lembretes configurados...")
    
    # Calcular datas alvo com base na data atual e configurações
    # Exemplo: hoje = 04/08, dias_antes = -6 → data alvo = 10/08 (vence em 6 dias)
    hoje = datetime.now()
    datas_alvo = []
    
    for lem in lembretes:
        dias_antes = lem.get("dias_antes", 0)
        
        if dias_antes < 0:
            # Dias antes do vencimento (negativo): busca boletos que vencem no futuro
            # -6 dias antes = boleto vence em 6 dias = hoje + 6
            data_alvo = hoje + timedelta(days=abs(dias_antes))
        elif dias_antes > 0:
            # Dias depois do vencimento (positivo): busca boletos que venceram no passado
            # +6 dias depois = boleto venceu há 6 dias = hoje - 6
            data_alvo = hoje - timedelta(days=dias_antes)
        else:
            # No dia do vencimento
            data_alvo = hoje
        
        datas_alvo.append(data_alvo)
        logging.warning(f"📅 Lembrete: {dias_antes} dias → data alvo: {data_alvo.strftime('%Y-%m-%d')}")
    
    # Calcular range de busca (mínimo e máximo das datas alvo)
    if datas_alvo:
        data_inicio = min(datas_alvo).strftime("%Y-%m-%d")
        data_fim = max(datas_alvo).strftime("%Y-%m-%d")
        logging.warning(f"📅 Range de busca: {data_inicio} até {data_fim}")
    else:
        # Fallback se não houver lembretes
        data_inicio = hoje.strftime("%Y-%m-%d")
        data_fim = (hoje + timedelta(days=7)).strftime("%Y-%m-%d")
        logging.warning(f"📅 Range de busca (fallback): {data_inicio} até {data_fim}")
    
    # Usar API Bulk-data (1 requisição apenas!) com filtro de centros de custo
    parcelas_bulk = listar_parcelas_por_periodo_bulk(data_inicio, data_fim, cost_centers_ids)
    
    if not parcelas_bulk:
        logging.warning("📭 Nenhuma parcela encontrada no período via Bulk-data")
        return []
    
    logging.warning(f"📊 {len(parcelas_bulk)} parcelas encontradas via Bulk-data")
    
    # Log dos lembretes configurados
    for i, lem in enumerate(lembretes):
        dias = lem.get("dias_antes", 0)
        tipo = "antes" if dias < 0 else "depois" if dias > 0 else "no dia"
        logging.warning(f"📅 Lembrete {i+1}: {dias} dias {tipo} do vencimento")
    
    # Buscar lista de clientes se cache não existir (para obter telefones)
    # TTL reduzido para 1 hora para evitar dados desatualizados
    cache_clientes = obter_dados_cache("lista_clientes", validade_horas=1)
    if not cache_clientes:
        logging.warning("📊 Cache de clientes não existe, buscando da API...")
        url = f"{BASE_URL}/customers"
        r = requests.get(url, headers=json_headers, timeout=30)
        if r.status_code == 200:
            cache_clientes = r.json().get("results", [])
            salvar_cache("lista_clientes", cache_clientes)
            logging.warning(f"📊 {len(cache_clientes)} clientes cacheados")
        else:
            logging.warning(f"⚠️ Erro ao buscar clientes: {r.status_code}")
            cache_clientes = []
    
    boletos_vencendo = []
    
    # Processar parcelas retornadas pelo Bulk-data
    for parcela in parcelas_bulk:
        # Verificar se parcela tem baixa (paga)
        receipts = parcela.get("receipts", [])
        if receipts:
            logging.warning(f"⏭️ Parcela {parcela.get('installmentId')} já tem baixa, ignorando")
            continue
        
        # Extrair dados da parcela
        vencimento_str = parcela.get("dueDate")
        if not vencimento_str:
            continue
        
        # Verificar se parcela tem ID válido (indica que parcela foi gerada)
        installment_id = parcela.get("installmentId")
        if not installment_id:
            logging.warning(f"⏭️ Título sem parcela gerada (sem installmentId), ignorando")
            continue
        
        # Garantir que vencimento_str seja apenas a data (YYYY-MM-DD)
        # Se vier com hora, extrair apenas a parte da data
        if "T" in vencimento_str:
            vencimento_str = vencimento_str.split("T")[0]
        
        try:
            vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d")
        except:
            continue
        
        logging.warning(f"📅 Parcela {installment_id}: vencimento={vencimento.date()}")
        
        # Verificar se deve ser notificado hoje (baseado no vencimento)
        for lembrete in lembretes:
            dias_antes = lembrete.get("dias_antes", 0)
            data_notificacao = vencimento + timedelta(days=dias_antes)
            
            # Verifica se hoje é o dia da notificação
            if hoje.date() == data_notificacao.date():
                logging.warning(f"✅ MATCH! Parcela {parcela.get('installmentId')} - Vencimento: {vencimento.date()}, Notificação: {dias_antes} dias, Data alvo: {data_notificacao.date()}")
                
                # Verificar se parcela é apta para gerar boleto
                titulo_id = parcela.get("billId")
                parcela_id = parcela.get("installmentId")
                apta, url_report = tem_boleto_apto(titulo_id, parcela_id)
                
                if not apta:
                    logging.warning(f"⏭️ Parcela {parcela_id} não apta para geração de boleto - pulando")
                    continue
                
                # Buscar telefone do cliente (usar cache se disponível)
                cliente_id = parcela.get("clientId")
                cliente_nome = parcela.get("clientName")
                cliente_telefone = None
                
                # Tentar obter telefone do cache de clientes
                cache_clientes = obter_dados_cache("lista_clientes", validade_horas=24)
                if cache_clientes:
                    for cliente in cache_clientes:
                        if cliente.get("id") == cliente_id:
                            phones = cliente.get("phones", [])
                            if phones:
                                for phone in phones:
                                    if phone.get("main"):
                                        cliente_telefone = phone.get("number")
                                        break
                                if not cliente_telefone:
                                    cliente_telefone = phones[0].get("number")
                            break
                
                boletos_vencendo.append({
                    "cliente_id": cliente_id,
                    "cliente_nome": cliente_nome,
                    "cliente_telefone": cliente_telefone,
                    "titulo_id": titulo_id,
                    "parcela_id": parcela_id,
                    "vencimento": vencimento_str,
                    "valor": parcela.get("balanceAmount") or parcela.get("originalAmount") or 0,
                    "dias_antes": dias_antes,
                    "mensagem_template": lembrete.get("mensagem"),
                    "enviar_segunda_via": lembrete.get("enviar_segunda_via", False),
                    "envio_pdf": lembrete.get("envio_pdf", False),
                    "pdf_url": url_report  # URL do PDF da verificação de aptidão
                })
                logging.warning(f"✅ Boleto encontrado: {cliente_nome} - Vence em {dias_antes} dias")
    
    logging.info(f"📊 Total de boletos para cobrança: {len(boletos_vencendo)}")
    return boletos_vencendo


# ============================================================
# 📝 GERAR MENSAGEM DE COBRANÇA (USANDO CONFIGURAÇÕES PERSONALIZADAS)
# ============================================================
def gerar_mensagem_cobranca(boleto: Dict) -> str:
    """Gera mensagem personalizada de cobrança usando template configurado."""
    cliente = boleto["cliente_nome"]
    valor = boleto["valor"]
    dias = boleto["dias_antes"]
    vencimento = boleto["vencimento"]
    template = boleto.get("mensagem_template", "Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}")
    
    # Formatar valor
    try:
        valor_formatado = f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        valor_formatado = f"R$ {valor}"
    
    # Formatar dias para texto amigável (apenas número absoluto)
    if dias < 0:
        dias_texto = f"{abs(dias)}"
    elif dias > 0:
        dias_texto = f"{dias}"
    else:
        dias_texto = "hoje"
    
    # Substituir variáveis no template
    mensagem = template.replace("{cliente}", cliente)
    mensagem = mensagem.replace("{valor}", valor_formatado)
    mensagem = mensagem.replace("{dias}", dias_texto)
    mensagem = mensagem.replace("{vencimento}", vencimento)
    
    # Manter compatibilidade com enviar_segunda_via (legado)
    if boleto.get("enviar_segunda_via"):
        link_boleto = gerar_link_boleto(boleto["titulo_id"], boleto["parcela_id"])
        if link_boleto and not link_boleto.startswith("❌"):
            mensagem += f"\n\n{link_boleto}"
    
    return mensagem


# ============================================================
# 📊 RELATÓRIO DE COBRANÇAS (USANDO CONFIGURAÇÕES PERSONALIZADAS)
# ============================================================
def gerar_relatorio_cobrancas() -> str:
    """Gera relatório textual dos boletos vencendo baseado nas configurações."""
    boletos = verificar_boletos_vencendo()
    
    if not boletos:
        return "✅ Nenhum boleto vencendo nos períodos configurados."
    
    config = carregar_configuracao_cobranca()
    lembretes = config.get("lembretes", [])
    periodos = ", ".join([f"{l['dias_antes']} dias" for l in lembretes])
    
    linhas = [f"📊 **Relatório de Cobranças - {periodos}**\n"]
    linhas.append(f"Total de boletos: {len(boletos)}\n")
    
    # Agrupar por cliente
    por_cliente = {}
    for boleto in boletos:
        cliente = boleto["cliente_nome"]
        if cliente not in por_cliente:
            por_cliente[cliente] = []
        por_cliente[cliente].append(boleto)
    
    for cliente, lista_boletos in por_cliente.items():
        linhas.append(f"👤 **{cliente}**")
        for b in lista_boletos:
            valor = b["valor"]
            try:
                valor_formatado = f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                valor_formatado = f"R$ {valor}"
            
            linhas.append(f"  • Vence em {b['dias_antes']} dias: {valor_formatado} ({b['vencimento']})")
        linhas.append("")
    
    return "\n".join(linhas)
