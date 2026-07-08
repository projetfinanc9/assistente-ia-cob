import requests
import logging
import time
import json
from datetime import datetime, timedelta
from .sienge_config import BASE_URL, json_headers, _token

logging.warning("🚀 Rodando versão 6.0 do sienge_financeiro.py (com nomes de contas financeiras e IA integrada)")

_cache = {}

def get_cached(url):
    if not url:
        return "N/A"
    if url in _cache:
        return _cache[url]
    try:
        r = requests.get(url, headers=json_headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            name = data.get("name") or data.get("description") or data.get("fantasyName") or "N/A"
            _cache[url] = name
            return name
    except Exception as e:
        logging.error(f"⚠️ Erro ao buscar {url}: {e}")
    _cache[url] = "N/A"
    return "N/A"

# ============================================================
# 🧾 Apropriação Financeira (Plano de Contas)
# ============================================================
def get_apropriacoes_financeiras(bill_id: int):
    """
    Busca as apropriações financeiras (categorias orçamentárias)
    vinculadas a um título específico no Sienge.
    """
    try:
        url = f"{BASE_URL}/bills/{bill_id}/budget-categories"
        r = requests.get(url, headers=json_headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            aprop_detalhes = []
            for item in results:
                categoria_codigo = item.get("paymentCategoriesId", "N/A")
                categoria_nome = categoria_codigo
                centro = "N/A"
                percentual = item.get("percentage", 0)

                for link in item.get("links", []):
                    if link.get("rel") == "debtor":
                        centro = get_cached(link.get("href"))
                    if link.get("rel") == "paymentCategory":  # 🔥 Nome da conta financeira
                        categoria_nome = get_cached(link.get("href"))

                aprop_detalhes.append({
                    "categoria": categoria_nome,
                    "percentual": percentual,
                    "debtor": centro,
                })
            return aprop_detalhes
        elif r.status_code == 404:
            return []
    except Exception as e:
        logging.exception(f"⚠️ Erro em get_apropriacoes_financeiras: {e}")
    return []

# ============================================================
# Datas padrão
# ============================================================
def periodo_padrao():
    fim = datetime.now().date()
    inicio = fim - timedelta(days=365)
    return inicio.isoformat(), fim.isoformat()

# ============================================================
# Função base GET
# ============================================================
def sienge_get(endpoint, params=None, max_retries=3):
    url = f"{BASE_URL}/{endpoint}"
    if params is None:
        params = {}
    if "startDate" not in params:
        inicio, fim = periodo_padrao()
        params["startDate"], params["endDate"] = inicio, fim

    for tentativa in range(1, max_retries + 1):
        try:
            r = requests.get(url, headers=json_headers, params=params, timeout=40)
            if r.status_code == 200:
                data = r.json()
                return data.get("results") or data
            elif r.status_code == 429:
                time.sleep(2 * tentativa)
            elif r.status_code >= 500:
                time.sleep(2)
        except Exception as e:
            logging.exception(f"❌ Erro em sienge_get: {e}")
            time.sleep(2)
    return []

# ============================================================
# 💰 Relatórios Financeiros
# ============================================================
def gerar_relatorio_json(params=None, **kwargs):
    if not params:
        params = kwargs or {}

    contas_pagar = sienge_get("bills", params)
    contas_receber = sienge_get("accounts-receivable/receivable-bills", params)

    total_receitas = sum(float(c.get("receivableBillValue") or 0) for c in contas_receber)
    total_despesas = sum(float(c.get("totalInvoiceAmount") or c.get("totalValueAmount") or 0) for c in contas_pagar)
    lucro = total_receitas - total_despesas

    dre_formatado = {
        "receitas": f"R$ {total_receitas:,.2f}",
        "despesas": f"R$ {total_despesas:,.2f}",
        "lucro": f"R$ {lucro:,.2f}",
    }

    todas_despesas = []
    for item in contas_pagar:
        links = {l["rel"]: l["href"] for l in item.get("links", [])}
        empresa = get_cached(links.get("company", "")) if "company" in links else "N/A"
        fornecedor = get_cached(links.get("creditor", "")) if "creditor" in links else "N/A"
        centro = get_cached(links.get("departmentsCost", "")) if "departmentsCost" in links else "N/A"
        obra = get_cached(links.get("buildingsCost", "")) if "buildingsCost" in links else "N/A"

        bill_id = item.get("id")
        aprop_fin = get_apropriacoes_financeiras(bill_id) if bill_id else []

        todas_despesas.append({
            "empresa": empresa,
            "fornecedor": fornecedor,
            "centro_custo": centro,
            "obra": obra,
            "status": item.get("status", "N/A"),
            "valor_total": float(item.get("totalInvoiceAmount") or item.get("totalValueAmount") or 0),
            "data_vencimento": item.get("dueDate", "N/A"),
            "descricao": item.get("notes") or item.get("description") or "",
            "documento": item.get("documentNumber", ""),
            "tipo_lancamento": item.get("originId", ""),
            "apropriacoes_financeiras": aprop_fin,
        })

    logging.info(f"🧾 Total despesas extraídas: {len(todas_despesas)}")

    return {
        "todas_despesas": todas_despesas,
        "dre": {"formatado": dre_formatado},
        "total_registros": len(todas_despesas)
    }
