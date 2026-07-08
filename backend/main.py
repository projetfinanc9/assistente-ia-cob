from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
import logging, re, base64, os
import json
from pathlib import Path
import pandas as pd
import requests  # <-- para chamar a API do WhatsApp Cloud
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Twilio
from twilio.rest import Client

# === MÓDULOS LOCAIS ===
from sienge.sienge_pedidos import (
    listar_pedidos_pendentes,
    itens_pedido,
    autorizar_pedido,
    reprovar_pedido,
    gerar_relatorio_pdf_bytes,
)
from sienge.sienge_boletos import buscar_boletos_por_documento, gerar_link_boleto
from sienge.sienge_financeiro import gerar_relatorio_json
from sienge.sienge_ia import gerar_analise_financeira
from sienge.sienge_cobranca import (
    verificar_boletos_vencendo,
    gerar_mensagem_cobranca,
    gerar_relatorio_cobrancas,
)
from dashboard_financeiro import gerar_relatorio_gamma

# ============================================================
# 🚀 CONFIGURAÇÃO DO SERVIDOR FASTAPI
# ============================================================
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# ============================================================
# 🌐 CONFIGURAÇÃO CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
        "https://constru-ai-connect.lovable.app",
        "https://constru-ai-connect-prwx.onrender.com",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ⏰ SCHEDULER PARA COBRANÇAS AUTOMÁTICAS
# ============================================================
scheduler = AsyncIOScheduler()

async def job_cobranca():
    """Job agendado: verificar boletos vencendo baseado nas configurações"""
    logging.info("🔔 Executando job de cobrança automática...")
    try:
        boletos = verificar_boletos_vencendo()
        for boleto in boletos:
            if boleto.get("cliente_telefone"):
                mensagem = gerar_mensagem_cobranca(boleto)
                # Enviar via WhatsApp Cloud API se configurado
                if WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN:
                    numero = re.sub(r"\D", "", boleto["cliente_telefone"])
                    if numero.startswith("55"):
                        send_whatsapp_cloud_message(numero, mensagem)
        logging.info(f"✅ Job de cobrança concluído. {len(boletos)} boletos processados.")
    except Exception as e:
        logging.error(f"❌ Erro no job de cobrança: {e}")

# Configurar job (executar diariamente às 9h)
scheduler.add_job(job_cobranca, CronTrigger(hour=9, minute=0))

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# 🚀 EVENTO DE STARTUP
# ============================================================
@app.on_event("startup")
async def startup_event():
    """Inicia o scheduler quando o servidor sobe"""
    scheduler.start()
    logging.info("⏰ Scheduler iniciado - Jobs de cobrança automática ativos")

# ============================================================
# 🔐 CONFIG TWILIO (WHATSAPP)
# ============================================================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logging.info("✅ Cliente Twilio inicializado com sucesso.")
    except Exception as e:
        logging.error(f"❌ Erro ao inicializar cliente Twilio: {e}")
else:
    logging.warning("⚠️ TWILIO_ACCOUNT_SID ou TWILIO_AUTH_TOKEN não configurados.")

# ============================================================
# 🔐 CONFIG WHATSAPP CLOUD API (META)
# ============================================================
# Defina no Render:
#   WHATSAPP_PHONE_NUMBER_ID = <Identificação do número de telefone>
#   WHATSAPP_TOKEN = <Token gerado na Meta>
#   WHATSAPP_VERIFY_TOKEN = construai123   (mesmo usado no painel da Meta)
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "construai123")

# ============================================================
# 📩 MODELOS DE DADOS
# ============================================================
class Message(BaseModel):
    user: str
    text: str

class SiengeConfig(BaseModel):
    subdomain: str
    username: str
    password: str

class LembreteCobranca(BaseModel):
    dias_antes: int
    mensagem: str
    enviar_segunda_via: bool

class ConfiguracaoCobranca(BaseModel):
    ativo: bool
    lembretes: List[LembreteCobranca]

# ============================================================
# 🧮 FUNÇÕES AUXILIARES
# ============================================================
def money(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

usuarios_contexto = {}

def extrair_periodo(texto: str):
    datas = re.findall(r"\d{4}-\d{2}-\d{2}", texto)
    if len(datas) >= 2:
        return {"startDate": datas[0], "endDate": datas[1]}
    if len(datas) == 1:
        return {"startDate": datas[0]}
    return {}

def extrair_empresa(texto: str):
    m = re.search(r"empresa\s+(\d+)", texto)
    if m:
        return {"enterpriseId": m.group(1)}
    return {}

def filtros_do_usuario(user: str):
    return usuarios_contexto.get(user, {}).get("filtros", {})

def atualizar_filtros(user: str, novos: dict):
    ctx = usuarios_contexto.setdefault(user, {})
    atuais = ctx.get("filtros", {})
    atuais.update({k: v for k, v in novos.items() if v})
    ctx["filtros"] = atuais
    return atuais

# ============================================================
# 🔎 HELPERS FINANCEIROS EM CIMA DO gerar_relatorio_json
# ============================================================
def resumo_financeiro(**filtros) -> str:
    rel = gerar_relatorio_json(**filtros)
    dre_fmt = rel.get("dre", {}).get("formatado", {})
    if not dre_fmt:
        return "⚠️ Sem dados para o período/empresa informados."

    receita = dre_fmt.get("Receita Líquida") or dre_fmt.get("Receita", 0)
    custos = dre_fmt.get("Custo") or dre_fmt.get("Custos", 0)
    despesas = dre_fmt.get("Despesas") or dre_fmt.get("Despesas Operacionais", 0)
    resultado = dre_fmt.get("Lucro Líquido") or dre_fmt.get("Resultado", 0)

    linhas = [
        "📊 *Resumo Financeiro (DRE)*",
        f"• Receita: {money(receita)}",
        f"• Custos: {money(custos)}",
        f"• Despesas: {money(despesas)}",
        f"• Resultado: {money(resultado)}",
    ]
    return "\n".join(linhas)

def gastos_por_obra(**filtros) -> str:
    rel = gerar_relatorio_json(**filtros)
    obras = rel.get("por_obra") or rel.get("gastos_por_obra") or []
    if not obras:
        return "⚠️ Nenhum gasto por obra encontrado."

    linhas = ["🏗️ *Gastos por obra*"]
    for o in obras[:20]:
        nome = o.get("obra") or o.get("obra_nome") or o.get("descricao") or "-"
        valor = o.get("valor") or o.get("total") or 0
        linhas.append(f"• {nome}: {money(valor)}")
    return "\n".join(linhas)

def gastos_por_centro_custo(**filtros) -> str:
    rel = gerar_relatorio_json(**filtros)
    centros = rel.get("por_centro_custo") or rel.get("gastos_por_centro_custo") or []
    if not centros:
        return "⚠️ Nenhum gasto por centro de custo encontrado."

    linhas = ["📂 *Gastos por centro de custo*"]
    for c in centros[:20]:
        nome = c.get("centro_custo") or c.get("descricao") or "-"
        valor = c.get("valor") or c.get("total") or 0
        linhas.append(f"• {nome}: {money(valor)}")
    return "\n".join(linhas)

# ============================================================
# 🧠 INTERPRETAÇÃO DE INTENÇÃO
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()

    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}
    if "pedido" in t and "pendente" in t:
        return {"acao": "listar_pedidos_pendentes"}
    if re.search(r"itens\s+do\s+pedido\s+\d+", t):
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "itens_pedido", "parametros": {"pedido_id": int(pid)}}
    if "autorizar pedido" in t:
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "autorizar_pedido", "parametros": {"pedido_id": int(pid)}}
    if "reprovar pedido" in t:
        pid = re.findall(r"\d+", t)[-1]
        return {"acao": "reprovar_pedido", "parametros": {"pedido_id": int(pid)}}
    if "pdf" in t or "relatorio" in t or "relatório" in t:
        nums = re.findall(r"\d+", t)
        return {"acao": "relatorio_pdf", "parametros": {"pedido_id": int(nums[-1])}} if nums else {}
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        return {"acao": "buscar_boletos_cpf"}
    if re.search(r"\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}
    if re.search(r"\d{14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}
    if "confirmar" in t:
        return {"acao": "confirmar"}
    if "resumo" in t or "dre" in t or "resultado" in t:
        return {"acao": "resumo_financeiro"}
    if "gasto" in t and "obra" in t:
        return {"acao": "gastos_por_obra"}
    if "centro de custo" in t:
        return {"acao": "gastos_por_centro_custo"}
    if "análise" in t or "analise" in t:
        return {"acao": "analise_financeira"}
    if "apresentacao" in t or "slides" in t or "gamma" in t:
        return {"acao": "apresentacao_gamma"}
    if "cobrança" in t or "cobranca" in t or "vencendo" in t:
        return {"acao": "relatorio_cobrancas"}
    if "empresa" in t or re.search(r"\d{4}-\d{2}-\d{2}", t):
        return {"acao": "definir_filtros"}
    return {"acao": None}

# ============================================================
# 💬 ENDPOINT PRINCIPAL DE MENSAGENS (JÁ FUNCIONAVA)
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")
    texto = (msg.text or "").strip()

    # Atualiza filtros
    if "empresa" in texto.lower() or re.search(r"\d{4}-\d{2}-\d{2}", texto):
        novos = {}
        novos.update(extrair_periodo(texto))
        novos.update(extrair_empresa(texto))
        if novos:
            atualizados = atualizar_filtros(msg.user, novos)
            return {
                "text": "🧭 Filtros definidos.\n"
                        + (f"• Início: {atualizados.get('startDate')}\n" if atualizados.get("startDate") else "")
                        + (f"• Fim: {atualizados.get("endDate")}\n" if atualizados.get("endDate") else "")
                        + (f"• Empresa: {atualizados.get('enterpriseId')}\n" if atualizados.get("enterpriseId") else ""),
                "buttons": [
                    {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
                    {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
                    {"label": "📂 Gastos por Centro de Custo", "action": "gastos_por_centro_custo"},
                ],
            }

    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}
    filtros = filtros_do_usuario(msg.user)

    menu_inicial = [
        {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
        {"label": "💳 Segunda Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
        {"label": "🏗️ Gastos por Obra", "action": "gastos_por_obra"},
        {"label": "🔔 Relatório de Cobranças", "action": "relatorio_cobrancas"},
        {"label": "🎬 Relatório Gamma Dark Mode", "action": "apresentacao_gamma"},
    ]

    if not texto or acao == "saudacao":
        return {
            "text": "👋 Olá! Sou a Constru.IA.\n"
                    "Posso te ajudar com: Pedidos, Boletos, Resumo Financeiro, Gastos e Relatórios com IA.\n"
                    "Dica: defina filtros com: `empresa 1 2024-01-01 a 2024-12-31`",
            "buttons": menu_inicial,
        }

    try:
        # ========================================================
        # 💳 BOLETOS / CPF/CNPJ
        # ========================================================
        if acao == "cpf_digitado":
            doc = re.sub(r"\D", "", parametros.get("cpf", ""))
            doc_tipo = "CPF" if len(doc) == 11 else "CNPJ" if len(doc) == 14 else "documento"
            if len(doc) not in [11, 14]:
                return {"text": "⚠️ Documento inválido. Digite CPF (11 dígitos) ou CNPJ (14 dígitos)."}
            resultado = buscar_boletos_por_documento(doc)
            
            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu_inicial}
            
            nome = resultado.get("nome", "Cliente não identificado")
            
            # Se não encontrou boletos, ainda mostra o nome do cliente
            if "boletos" not in resultado or not resultado["boletos"]:
                usuarios_contexto[msg.user] = {"documento": doc, "nome": nome, "aguardando_confirmacao": True}
                return {
                    "text": f"🔎 Localizei o cliente *{nome}*.\n\n⚠️ Nenhum boleto disponível para segunda via no momento.",
                    "buttons": menu_inicial,
                }
            
            usuarios_contexto[msg.user] = {"documento": doc, "nome": nome, "aguardando_confirmacao": True}
            return {
                "text": f"🔎 Localizei o cliente *{nome}*. Confirmar para listar as 2ª vias?",
                "buttons": [
                    {"label": "✅ Confirmar", "action": "confirmar"},
                    {"label": "❌ Corrigir documento", "action": "buscar_boletos_cpf"},
                ],
            }

        if acao == "buscar_boletos_cpf":
            return {"text": "💳 Digite o CPF ou CNPJ do titular dos boletos.", "buttons": menu_inicial}

        # ========================================================
        # 💳 CONFIRMAR BOLETOS
        # ========================================================
        if texto.lower() == "confirmar" or acao == "confirmar":
            ctx = usuarios_contexto.get(msg.user, {})
            documento = ctx.get("documento")
            if not documento:
                return {"text": "⚠️ Nenhum documento armazenado. Digite novamente.", "buttons": menu_inicial}

            resultado = buscar_boletos_por_documento(documento)
            if "erro" in resultado:
                return {"text": resultado["erro"], "buttons": menu_inicial}

            nome = resultado.get("nome")
            boletos = resultado.get("boletos", [])
            if not boletos:
                return {"text": f"📭 Nenhum boleto disponível para {nome}.", "buttons": menu_inicial}

            linhas, botoes = [], []
            for b in boletos:
                titulo, parcela = b["titulo_id"], b["parcela_id"]
                valor, venc, desc = b.get("valor", 0.0), b.get("vencimento"), b.get("descricao", "-")
                linhas.append(
                    f"📄 *Título {titulo} / Parcela {parcela}*\n"
                    f"💰 Valor: R$ {valor:,.2f}\n"
                    f"📅 Vencimento: {venc}\n"
                    f"📝 {desc}"
                )
                botoes.append(
                    {
                        "label": f"📥 Gerar boleto {titulo}/{parcela}",
                        "action": f"boleto {titulo} {parcela}",
                    }
                )

            usuarios_contexto[msg.user] = {}
            return {
                "text": f"✅ *Boletos disponíveis para {nome}:*\n\n" + "\n\n".join(linhas[:15]),
                "buttons": botoes
                + [
                    {"label": "💳 Nova busca por CPF", "action": "buscar_boletos_cpf"},
                    {"label": "📋 Pedidos Pendentes", "action": "listar_pedidos_pendentes"},
                    {"label": "📊 Resumo Financeiro", "action": "resumo_financeiro"},
                ],
            }

        if acao == "link_boleto":
            t, p = parametros.get("titulo_id"), parametros.get("parcela_id")
            return {"text": gerar_link_boleto(t, p), "buttons": menu_inicial}

        # ========================================================
        # 📦 PEDIDOS
        # ========================================================
        if acao == "listar_pedidos_pendentes":
            pedidos = listar_pedidos_pendentes()
            if not pedidos:
                return {"text": "📭 Nenhum pedido pendente."}
            linhas = [f"📦 Pedido {p['id']} — {money(p.get('totalAmount', 0))}" for p in pedidos]
            botoes = [{"label": f"Itens {p['id']}", "action": f"itens do pedido {p['id']}"} for p in pedidos]
            return {"text": "\n".join(linhas), "buttons": botoes}

        if acao == "itens_pedido":
            pid = parametros.get("pedido_id")
            itens = itens_pedido(pid)
            linhas = [f"• {i.get('description', 'Item')} — {money(i.get('totalAmount', 0))}" for i in itens]
            return {
                "text": f"📦 Itens do pedido {pid}:\n" + "\n".join(linhas),
                "buttons": [
                    {"label": "✅ Autorizar", "action": f"autorizar pedido {pid}"},
                    {"label": "❌ Reprovar", "action": f"reprovar pedido {pid}"},
                    {"label": "📄 PDF", "action": f"gerar pdf pedido {pid}"},
                ],
            }

        if acao == "autorizar_pedido":
            return {"text": autorizar_pedido(parametros["pedido_id"])}
        if acao == "reprovar_pedido":
            return {"text": reprovar_pedido(parametros["pedido_id"])}
        if acao == "relatorio_pdf":
            pid = parametros.get("pedido_id")
            pdf = gerar_relatorio_pdf_bytes(pid)
            if not pdf:
                return {"text": "⚠️ Erro ao gerar PDF."}
            return {
                "text": f"📄 PDF do pedido {pid} gerado com sucesso.",
                "pdf_base64": base64.b64encode(pdf).decode(),
                "filename": f"pedido_{pid}.pdf",
            }

        # ========================================================
        # 💰 FINANCEIRO / IA
        # ========================================================
        if acao == "resumo_financeiro":
            return {"text": resumo_financeiro(**filtros), "buttons": menu_inicial}
        if acao == "gastos_por_obra":
            return {"text": gastos_por_obra(**filtros), "buttons": menu_inicial}
        if acao == "gastos_por_centro_custo":
            return {"text": gastos_por_centro_custo(**filtros), "buttons": menu_inicial}
        if acao == "analise_financeira":
            rel = gerar_relatorio_json(**filtros)
            df = pd.DataFrame(rel.get("todas_despesas", []))
            if df.empty:
                return {"text": "⚠️ Sem dados para análise."}
            return {"text": gerar_analise_financeira("Relatório Financeiro", df), "buttons": menu_inicial}
        if acao == "apresentacao_gamma":
            rel = gerar_relatorio_json(**filtros)
            df = pd.DataFrame(rel.get("todas_despesas", []))
            dre = rel.get("dre", {}).get("formatado", {})
            if df.empty:
                return {"text": "⚠️ Sem dados para gerar relatório."}
            link = gerar_relatorio_gamma(df, dre, filtros, msg.user)
            return {
                "text": f"🎬 Relatório Gamma (Dark Mode) gerado!\n\n[📊 Acessar Relatório]({link})",
                "buttons": menu_inicial,
            }
        
        if acao == "relatorio_cobrancas":
            # Verificar boletos vencendo baseado nas configurações
            relatorio = gerar_relatorio_cobrancas()
            return {
                "text": relatorio,
                "buttons": menu_inicial,
            }

        return {
            "text": "🤖 Não entendi. Dica: `empresa 1 2024-01-01 a 2024-12-31`",
            "buttons": menu_inicial,
        }

    except Exception as e:
        logging.exception("❌ Erro geral:")
        return {"text": f"Ocorreu um erro: {e}", "buttons": menu_inicial}

# ============================================================
# 🌐 WEBHOOK WHATSAPP CLOUD API (VERIFICAÇÃO)
# ============================================================
@app.get("/webhook-whatsapp")
async def verify_whatsapp(request: Request):
    """
    Endpoint de verificação do Meta (GET)
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logging.info("✅ Webhook WhatsApp verificado pelo Meta.")
        return PlainTextResponse(challenge or "")
    else:
        logging.warning("⚠️ Webhook WhatsApp verificação falhou.")
        return PlainTextResponse("Verification failed", status_code=403)

# ============================================================
# 💬 WEBHOOK WHATSAPP CLOUD API (RECEBIMENTO)
# ============================================================
def send_whatsapp_cloud_message(to_number: str, body: str):
    """
    Envia mensagem de texto usando WhatsApp Cloud API.
    to_number: número sem 'whatsapp:', ex: 559193808761
    """
    if not (WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN):
        logging.error("❌ WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN não configurados.")
        return

    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        logging.info(f"📤 Enviando mensagem Cloud API → {to_number}: {body}")
        logging.info(f"Resposta Meta: {resp.status_code} - {resp.text}")
    except Exception as e:
        logging.error(f"❌ Erro ao enviar mensagem via Cloud API: {e}")

@app.post("/webhook-whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Recebe mensagens do WhatsApp Cloud API (POST)
    """
    data = await request.json()
    logging.info(f"📲 Webhook WhatsApp recebido: {data}")

    try:
        entry_list = data.get("entry", [])
        if not entry_list:
            return {"status": "no_entry"}

        changes = entry_list[0].get("changes", [])
        if not changes:
            return {"status": "no_changes"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        from_number = msg.get("from")             # ex: "559193808761"
        text = msg.get("text", {}).get("body", "")

        user_id = f"whatsapp:{from_number}"

        # Usa a MESMA lógica do backend normal
        resposta_construia = await mensagem(Message(user=user_id, text=text))
        texto_resposta = resposta_construia.get("text", "Constru.IA: não consegui gerar resposta.")

        # Envia resposta via Cloud API
        send_whatsapp_cloud_message(from_number, texto_resposta)

    except Exception as e:
        logging.exception("❌ Erro ao processar webhook WhatsApp:")
        return {"status": "error", "detail": str(e)}

    return {"status": "ok"}

# ============================================================
# 🤖 WEBHOOK WHATSAPP VIA TWILIO
# ============================================================
@app.post("/webhook-twilio", response_class=PlainTextResponse)
async def webhook_twilio(
    From: str = Form(...),   # Número do usuário no WhatsApp (ex: whatsapp:+5591...)
    Body: str = Form(...),   # Texto da mensagem
):
    logging.info(f"📲 WhatsApp de {From}: {Body}")

    # Usa a MESMA lógica do backend normal
    resposta_construia = await mensagem(
        Message(user=From, text=Body)
    )

    texto_resposta = resposta_construia.get("text", "Constru.IA: não consegui gerar resposta.")
    logging.info(f"💬 Resposta para {From}: {texto_resposta}")

    # Envia resposta via API da Twilio (em vez de TwiML)
    if twilio_client:
        try:
            twilio_client.messages.create(
                from_=TWILIO_WHATSAPP_FROM,
                to=From,
                body=texto_resposta,
            )
            logging.info("✅ Mensagem enviada via Twilio.")
        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem WhatsApp via Twilio: {e}")
    else:
        logging.error("❌ twilio_client não inicializado. Verifique TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN.")

    # Twilio só precisa de 200 OK aqui
    return PlainTextResponse("OK")

# ============================================================
# 🌐 TESTE FINANCEIRO
# ============================================================
@app.get("/teste-financeiro")
def teste_financeiro():
    filtros = {"startDate": "2024-01-01", "endDate": "2024-12-31", "enterpriseId": "1"}
    rel = gerar_relatorio_json(**filtros)
    return {
        "resumo": rel.get("dre", {}).get("formatado", {}),
        "amostra": rel.get("todas_despesas", [])[:5],
    }

# ============================================================
# 🌍 STATUS
# ============================================================
@app.get("/")
def root():
    return {"ok": True, "service": "constru-ai-connect", "status": "running"}

# ============================================================
# ⚙️ ENDPOINTS DE CONFIGURAÇÃO SIENGE
# ============================================================
@app.get("/config")
def get_config():
    """Retorna configurações atuais do Sienge"""
    from sienge.sienge_config import subdominio, usuario
    # Não retornamos a senha por segurança
    return {
        "subdomain": subdominio,
        "username": usuario,
        "password": ""  # Não expor a senha
    }

@app.post("/config")
def save_config(config: SiengeConfig):
    """Salva novas configurações do Sienge"""
    try:
        # Salva no arquivo JSON
        from sienge.sienge_config import salvar_configuracoes
        sucesso = salvar_configuracoes(config.subdomain, config.username, config.password)
        
        if not sucesso:
            return {"success": False, "error": "Erro ao salvar configurações no arquivo"}
        
        # Atualizar variáveis de ambiente
        os.environ["SIENGE_SUBDOMINIO"] = config.subdomain
        os.environ["SIENGE_USUARIO"] = config.username
        os.environ["SIENGE_SENHA"] = config.password
        
        # Recarregar configurações
        import importlib
        from sienge import sienge_config
        importlib.reload(sienge_config)
        
        # Recarregar todos os módulos que dependem do sienge_config
        from sienge import sienge_boletos, sienge_pedidos, sienge_financeiro, sienge_cobranca
        importlib.reload(sienge_boletos)
        importlib.reload(sienge_pedidos)
        importlib.reload(sienge_financeiro)
        importlib.reload(sienge_cobranca)
        
        logging.info(f"✅ Configurações atualizadas e persistidas: {config.subdomain}")
        return {"success": True, "message": "Configurações salvas com sucesso"}
    except Exception as e:
        logging.error(f"❌ Erro ao salvar configurações: {e}")
        return {"success": False, "error": str(e)}

# ============================================================
# 🔔 CONFIGURAÇÕES DE COBRANÇA AUTOMÁTICA
# ============================================================
COBRANCA_CONFIG_FILE = Path(__file__).parent / "cobranca_config.json"

def carregar_configuracao_cobranca():
    """Carrega configurações de cobrança do arquivo JSON"""
    if COBRANCA_CONFIG_FILE.exists():
        try:
            with open(COBRANCA_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
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

def salvar_configuracao_cobranca(config: dict):
    """Salva configurações de cobrança no arquivo JSON"""
    try:
        with open(COBRANCA_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ Configuração de cobrança salva")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao salvar configuração de cobrança: {e}")
        return False

@app.get("/cobranca-config")
def get_cobranca_config():
    """Retorna configurações atuais de cobrança automática"""
    config = carregar_configuracao_cobranca()
    return config

@app.post("/cobranca-config")
def save_cobranca_config(config: ConfiguracaoCobranca):
    """Salva novas configurações de cobrança automática"""
    try:
        config_dict = {
            "ativo": config.ativo,
            "lembretes": [
                {
                    "dias_antes": l.dias_antes,
                    "mensagem": l.mensagem,
                    "enviar_segunda_via": l.enviar_segunda_via
                }
                for l in config.lembretes
            ]
        }
        
        sucesso = salvar_configuracao_cobranca(config_dict)
        if not sucesso:
            return {"success": False, "error": "Erro ao salvar configurações"}
        
        # Recarregar módulo de cobrança
        import importlib
        from sienge import sienge_cobranca
        importlib.reload(sienge_cobranca)
        
        logging.info(f"✅ Configuração de cobrança atualizada")
        return {"success": True, "message": "Configurações de cobrança salvas com sucesso"}
    except Exception as e:
        logging.error(f"❌ Erro ao salvar configuração de cobrança: {e}")
        return {"success": False, "error": str(e)}

@app.post("/test-sienge")
def test_sienge_connection(config: SiengeConfig):
    """Testa conexão com o Sienge usando as configurações fornecidas"""
    try:
        from base64 import b64encode
        import requests
        
        BASE_URL = f"https://api.sienge.com.br/{config.subdomain}/public/api/v1"
        _token = b64encode(f"{config.username}:{config.password}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {_token}",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        
        # Testar conexão buscando clientes
        response = requests.get(f"{BASE_URL}/customers", headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {"success": True, "message": "Conexão estabelecida com sucesso"}
        elif response.status_code == 401:
            return {"success": False, "error": "Credenciais inválidas"}
        else:
            return {"success": False, "error": f"Erro na conexão: {response.status_code}"}
    except Exception as e:
        logging.error(f"❌ Erro ao testar conexão: {e}")
        return {"success": False, "error": str(e)}
