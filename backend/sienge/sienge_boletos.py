import requests
import logging
import re
from .sienge_config import BASE_URL, json_headers

# ============================================================
# 🚀 IDENTIFICAÇÃO DA VERSÃO
# ============================================================
logging.warning("🚀 Rodando versão 1.9 do sienge_boletos.py (com suporte a CNPJ)")

# ============================================================
# 👤 CLIENTE
# ============================================================
def detectar_documento_tipo(documento: str) -> str:
    """Detecta se o documento é CPF ou CNPJ"""
    # Remove caracteres não numéricos
    doc_limpo = re.sub(r"\D", "", documento)
    
    if len(doc_limpo) == 11:
        return "cpf"
    elif len(doc_limpo) == 14:
        return "cnpj"
    else:
        return "desconhecido"

def buscar_cliente_por_documento(documento: str):
    """Busca cliente no Sienge por CPF ou CNPJ."""
    doc_limpo = re.sub(r"\D", "", documento)
    tipo = detectar_documento_tipo(documento)
    
    logging.info(f"🔍 Buscando cliente com documento: {documento} (tipo: {tipo}, limpo: {doc_limpo})")
    
    # Tenta buscar por CPF primeiro
    if tipo == "cpf":
        url = f"{BASE_URL}/customers?cpf={doc_limpo}"
        logging.info(f"GET {url} (busca por CPF)")
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.info(f"{url} -> {r.status_code}")
        logging.info(f"Resposta: {r.text[:500]}")
        
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or data
            if isinstance(results, list) and len(results) > 0:
                logging.info(f"✅ Cliente encontrado por CPF: {results[0].get('name')}")
                return results[0]
    
    # Tenta buscar por CNPJ (tenta diferentes nomes de campo)
    if tipo == "cnpj":
        # Tenta campo 'cnpj'
        url = f"{BASE_URL}/customers?cnpj={doc_limpo}"
        logging.info(f"GET {url} (busca por CNPJ - campo cnpj)")
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.info(f"{url} -> {r.status_code}")
        logging.info(f"Resposta: {r.text[:500]}")
        
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or data
            if isinstance(results, list) and len(results) > 0:
                logging.info(f"✅ Cliente encontrado por CNPJ: {results[0].get('name')}")
                return results[0]
        
        # Tenta campo 'federalTaxId'
        url = f"{BASE_URL}/customers?federalTaxId={doc_limpo}"
        logging.info(f"GET {url} (busca por CNPJ - campo federalTaxId)")
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.info(f"{url} -> {r.status_code}")
        logging.info(f"Resposta: {r.text[:500]}")
        
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or data
            if isinstance(results, list) and len(results) > 0:
                logging.info(f"✅ Cliente encontrado por federalTaxId: {results[0].get('name')}")
                return results[0]
    
    # Se não encontrou pelo tipo específico, tenta buscar genérico e filtrar
    url = f"{BASE_URL}/customers"
    logging.info(f"GET {url} (busca genérica de todos clientes)")
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"{url} -> {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        results = data.get("results") or data
        if isinstance(results, list):
            logging.info(f"📊 Total de clientes para busca genérica: {len(results)}")
            # Tenta encontrar cliente que contenha o documento em qualquer campo
            for cliente in results:
                # Verifica múltiplos campos possíveis
                campos_para_verificar = [
                    cliente.get("cpf", ""),
                    cliente.get("cnpj", ""),
                    cliente.get("federalTaxId", ""),
                    cliente.get("taxId", ""),
                    cliente.get("document", ""),
                    cliente.get("identification", ""),
                    str(cliente.get("id", "")),
                ]
                
                for campo in campos_para_verificar:
                    campo_limpo = re.sub(r"\D", "", str(campo))
                    if doc_limpo in campo_limpo or campo_limpo in doc_limpo:
                        logging.info(f"✅ Cliente encontrado via busca genérica: {cliente.get('name')} (campo: {campo})")
                        return cliente
    
    logging.warning(f"❌ Cliente não encontrado com documento: {documento}")
    return None

def buscar_cliente_por_cpf(cpf: str):
    """Busca cliente no Sienge pelo CPF (mantido para compatibilidade)."""
    return buscar_cliente_por_documento(cpf)


# ============================================================
# 🧾 BOLETOS / TÍTULOS
# ============================================================
def listar_boletos_por_cliente(cliente_id: int):
    """Lista boletos/títulos vinculados a um cliente."""
    url = f"{BASE_URL}/accounts-receivable/receivable-bills?customerId={cliente_id}"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


def listar_parcelas(titulo_id: int):
    """Lista parcelas de um título."""
    if not titulo_id:
        return []
    url = f"{BASE_URL}/accounts-receivable/receivable-bills/{titulo_id}/installments"
    r = requests.get(url, headers=json_headers, timeout=30)
    logging.info(f"GET {url} -> {r.status_code}")
    if r.status_code != 200:
        return []
    return r.json().get("results") or []


# ============================================================
# 🧠 VERIFICAÇÃO DE SEGUNDA VIA (LOG DETALHADO)
# ============================================================
def boleto_existe(titulo_id: int, parcela_id: int) -> bool:
    """Verifica se existe segunda via real para essa parcela."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    try:
        r = requests.get(url, headers=json_headers, params=params, timeout=20)
        logging.info(f"🔎 Verificando boleto: {params} -> {r.status_code}")
        logging.info(f"Resposta: {r.text[:400]}")

        # 200 = OK
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            if results and results[0].get("urlReport"):
                logging.info(f"🟢 Segunda via encontrada -> {results[0].get('urlReport')}")
                return True

        # 422 = Erro de regra no Sienge
        if r.status_code == 422:
            if "RuntimeException" in r.text or "SiengeBusinessException" in r.text:
                logging.warning(f"⚠️ Erro interno no Sienge ao tentar gerar boleto ({titulo_id}/{parcela_id})")
            else:
                logging.info("🔴 Nenhuma segunda via disponível para essa parcela.")

    except Exception as e:
        logging.error(f"Erro ao verificar boleto ({titulo_id}/{parcela_id}): {e}")
    return False


# ============================================================
# 🔍 BUSCAR BOLETOS POR CPF/CNPJ (CORRIGIDO E APRIMORADO)
# ============================================================
def buscar_boletos_por_documento(documento: str):
    """Busca apenas boletos realmente disponíveis para 2ª via (com logs detalhados). Suporta CPF e CNPJ."""
    cliente = buscar_cliente_por_documento(documento)
    if not cliente:
        return {"erro": f"❌ Nenhum cliente encontrado com o documento {documento}."}

    nome = cliente.get("name")
    cid = cliente.get("id")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cid})")

    boletos = listar_boletos_por_cliente(cid)
    logging.info(f"📊 Total de títulos retornados: {len(boletos)}")
    
    # Log detalhado de todos os títulos
    for b in boletos:
        logging.info(f"📋 Título ID: {b.get('id')} ou {b.get('receivableBillId')} | Valor: {b.get('amount') or b.get('receivableBillValue')} | Quitado: {b.get('payOffDate')}")

    if not boletos:
        return {"erro": f"📭 Nenhum boleto encontrado para {nome}."}

    lista = []
    for b in boletos:
        titulo_id = b.get("id") or b.get("receivableBillId")
        valor = b.get("amount") or b.get("receivableBillValue") or 0.0
        desc = b.get("description") or b.get("documentNumber") or b.get("note") or "-"
        emissao = b.get("issueDate")
        quitado = b.get("payOffDate")

        logging.info(f"🧾 Título {titulo_id} | Valor {valor} | Descrição: {desc}")

        if quitado:
            logging.info(f"⏭️ Ignorando título {titulo_id} (já quitado)")
            continue

        parcelas = listar_parcelas(titulo_id)
        logging.info(f"📦 Parcelas do título {titulo_id}: {len(parcelas)}")

        if not parcelas:
            continue

        for p in parcelas:
            logging.info(f"🧩 Parcela -> {p}")

            # ✅ Usa o campo installmentId como ID principal
            parcela_id = p.get("id") or p.get("installmentId")
            if not parcela_id:
                logging.info("⚠️ Parcela sem ID, ignorada")
                continue

            logging.info(f"🔍 Testando boleto título={titulo_id}, parcela={parcela_id}, valor={p.get('balanceDue')}")
            existe = boleto_existe(titulo_id, parcela_id)
            logging.info(f"Resultado da verificação -> {'🟢 Existe' if existe else '🔴 Não existe'}")

            if not existe:
                continue

            lista.append({
                "titulo_id": titulo_id,
                "parcela_id": parcela_id,
                "descricao": desc,
                "valor": p.get("balanceDue") or valor,
                "vencimento": p.get("dueDate") or emissao,
            })

        # 🔍 Checagem extra para parcelas conhecidas (Sienge às vezes omite)
        parcelas_extras = [56, 99]
        for extra_id in parcelas_extras:
            logging.info(f"🔄 Tentando verificar parcela extra manual: {extra_id} (título {titulo_id})")
            existe = boleto_existe(titulo_id, extra_id)
            if existe:
                lista.append({
                    "titulo_id": titulo_id,
                    "parcela_id": extra_id,
                    "descricao": desc,
                    "valor": valor,
                    "vencimento": emissao,
                })

    if not lista:
        return {"erro": f"📭 Nenhum boleto disponível para segunda via de {nome}."}

    return {
        "nome": nome,
        "boletos": lista
    }

def buscar_boletos_por_cpf(cpf: str):
    """Função de compatibilidade - usa buscar_boletos_por_documento."""
    return buscar_boletos_por_documento(cpf)


# ============================================================
# 🔗 GERAR LINK DO BOLETO (2ª VIA)
# ============================================================
def gerar_link_boleto(titulo_id: int, parcela_id: int) -> str:
    """Gera link da segunda via do boleto."""
    url = f"{BASE_URL}/payment-slip-notification"
    params = {"billReceivableId": titulo_id, "installmentId": parcela_id}

    logging.info(f"GET {url} -> params={params}")
    r = requests.get(url, headers=json_headers, params=params, timeout=30)
    logging.info(f"{url} -> {r.status_code}")
    logging.info(f"Resposta: {r.text[:400]}")

    if r.status_code == 200:
        try:
            data = r.json()
            results = data.get("results") or []
            if results and isinstance(results, list):
                result = results[0]
                link = result.get("urlReport")
                linha_digitavel = result.get("digitableNumber")

                if link:
                    logging.info(f"🟢 Link do boleto gerado: {link}")
                    return (
                        f"📄 **Segunda via gerada com sucesso!**\n"
                        f"🔗 [Clique aqui para abrir o boleto]({link})\n"
                        f"💳 **Linha digitável:** `{linha_digitavel}`"
                    )
        except Exception as e:
            logging.exception("Erro ao processar resposta do boleto:")
            return f"❌ Erro ao processar boleto: {e}"

    elif r.status_code == 422:
        return "⚠️ O Sienge retornou erro interno ao tentar gerar o boleto. Verifique se há dados inconsistentes no título."

    return f"❌ Erro ao gerar boleto ({r.status_code})."
