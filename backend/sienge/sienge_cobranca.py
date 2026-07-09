import logging
from datetime import datetime, timedelta
from typing import List, Dict
import requests
import re
import json
from pathlib import Path
from .sienge_config import BASE_URL, json_headers
from .sienge_boletos import buscar_cliente_por_documento

logging.warning("🔔 Rodando módulo sienge_cobranca.py (sistema de cobrança automática com suporte a CNPJ)")

# ============================================================
# 💾 CONFIGURAÇÕES DE COBRANÇA
# ============================================================
COBRANCA_CONFIG_FILE = Path(__file__).parent.parent / "cobranca_config.json"

def carregar_configuracao_cobranca():
    """Carrega configurações de cobrança do arquivo JSON"""
    if COBRANCA_CONFIG_FILE.exists():
        try:
            with open(COBRANCA_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"✅ Configuração de cobrança carregada: {len(config.get('lembretes', []))} lembretes")
                return config
        except Exception as e:
            logging.warning(f"⚠️ Erro ao carregar configuração de cobrança: {e}")
    # Configuração padrão
    return {
        "ativo": False,
        "lembretes": [
            {
                "dias_antes": 5,
                "mensagem": "Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}",
                "enviar_segunda_via": True
            },
            {
                "dias_antes": 1,
                "mensagem": "Olá {cliente}, seu boleto vence amanhã! Valor: R$ {valor}",
                "enviar_segunda_via": True
            }
        ]
    }

# ============================================================
# 🔍 FUNÇÕES AUXILIARES
# ============================================================


def listar_boletos_por_cliente(cliente_id: int):
    """Lista boletos/títulos vinculados a um cliente."""
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        logging.warning(f"⚠️ Erro ao buscar boletos do cliente {cliente_id}: {r.status_code}")
        return []
    data = r.json()
    results = data.get("results") or []
    logging.warning(f"📄 API retornou {len(results)} boletos para cliente {cliente_id}")
    if results:
        logging.warning(f"🔍 Primeiro boleto: {results[0]}")
    return results


def listar_parcelas(titulo_id: int):
    """Lista parcelas de um título."""
    if not titulo_id:
        return []
    url = f"{BASE_URL}/accounts-receivable/receivable-bills/{titulo_id}/installments"
    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


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


# ============================================================
# 📅 VERIFICAR BOLETOS VENCENDO (USANDO CONFIGURAÇÕES PERSONALIZADAS)
# ============================================================
def verificar_boletos_vencendo() -> List[Dict]:
    """
    Busca boletos vencendo baseado nas configurações personalizadas.
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
    
    logging.warning(f"🔍 Verificando boletos com {len(lembretes)} lembretes configurados...")
    
    # Log dos lembretes configurados
    for i, lem in enumerate(lembretes):
        dias = lem.get("dias_antes", 0)
        data = datetime.now() + timedelta(days=dias)
        logging.warning(f"📅 Lembrete {i+1}: dias_antes={dias}, data_alvo={data.date()}")
    
    # Buscar todos os clientes
    url = f"{BASE_URL}/customers"
    r = requests.get(url, headers=json_headers, timeout=30)
    if r.status_code != 200:
        logging.error(f"Erro ao buscar clientes: {r.status_code}")
        return []
    
    clientes = r.json().get("results", [])
    logging.warning(f"📊 Total de clientes: {len(clientes)}")
    
    boletos_vencendo = []
    
    for cliente in clientes:
        cliente_id = cliente.get("id")
        cliente_nome = cliente.get("name")
        cliente_cpf = cliente.get("cpf")
        cliente_telefone = cliente.get("phone") or cliente.get("mobile")
        
        # Log para debug - mostrar todos os campos do cliente
        logging.warning(f"🔍 Cliente {cliente_nome}: dados completos={cliente}")
        
        # Log para debug do telefone
        logging.warning(f"📞 Cliente {cliente_nome}: phone={cliente.get('phone')}, mobile={cliente.get('mobile')}, telefone_final={cliente_telefone}")
        
        if not cliente_id:
            continue
        
        logging.warning(f"👤 Processando cliente: {cliente_nome} (ID: {cliente_id})")
        
        # Buscar boletos do cliente
        boletos = listar_boletos_por_cliente(cliente_id)
        logging.warning(f"📄 Cliente {cliente_nome}: {len(boletos)} boletos encontrados")
        
        for boleto in boletos:
            titulo_id = boleto.get("receivableBillId")
            quitado = boleto.get("payOffDate")
            
            if quitado:
                logging.warning(f"⏭️ Título {titulo_id} já quitado, ignorando")
                continue  # Pular boletos já quitados
            
            # Buscar parcelas
            parcelas = listar_parcelas(titulo_id)
            logging.warning(f"📦 Título {titulo_id}: {len(parcelas)} parcelas")
            
            for parcela in parcelas:
                vencimento_str = parcela.get("dueDate")
                if not vencimento_str:
                    continue
                
                try:
                    vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d")
                except:
                    continue
                
                logging.warning(f"📅 Parcela {parcela.get('id')}: vencimento={vencimento.date()}")
                
                # Verificar se vence em algum dos períodos configurados
                for lembrete in lembretes:
                    dias_antes = lembrete.get("dias_antes", 0)
                    data_limite = datetime.now() + timedelta(days=dias_antes)
                    
                    # Verifica se vence exatamente no dia configurado
                    if vencimento.date() == data_limite.date():
                        logging.warning(f"✅ MATCH! Boleto {titulo_id}/{parcela.get('id')} vence em {dias_antes} dias")
                        boletos_vencendo.append({
                            "cliente_nome": cliente_nome,
                            "cliente_cpf": cliente_cpf,
                            "cliente_telefone": cliente_telefone,
                            "titulo_id": titulo_id,
                            "parcela_id": parcela.get("id"),
                            "vencimento": vencimento_str,
                            "valor": parcela.get("balanceDue") or boleto.get("amount") or 0,
                            "dias_antes": dias_antes,
                            "mensagem_template": lembrete.get("mensagem"),
                            "enviar_segunda_via": lembrete.get("enviar_segunda_via", False)
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
    
    # Substituir variáveis no template
    mensagem = template.replace("{cliente}", cliente)
    mensagem = mensagem.replace("{valor}", valor_formatado)
    mensagem = mensagem.replace("{dias}", str(dias))
    mensagem = mensagem.replace("{vencimento}", vencimento)
    
    # Adicionar segunda via se configurado
    if boleto.get("enviar_segunda_via"):
        link_boleto = gerar_segunda_via(boleto["titulo_id"], boleto["parcela_id"])
        if link_boleto and not link_boleto.startswith("❌"):
            mensagem += f"\n\n📄 **Segunda via:** {link_boleto}"
    
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
