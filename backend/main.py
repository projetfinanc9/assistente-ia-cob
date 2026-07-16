from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, HTMLResponse, StreamingResponse
import io
from pydantic import BaseModel
from typing import List, Optional
import logging, re, base64, os
import json
from pathlib import Path
import pandas as pd
import requests  # <-- para chamar a API do WhatsApp Cloud
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# ============================================================
# ⏰ SISTEMA DE AGENDAMENTO
# =================================================<arg_value># Configurar scheduler com timezone de Brasília
brasilia_tz = timezone('America/Sao_Paulo')
scheduler = AsyncIOScheduler(timezone=brasilia_tz)

# ============================================================
# 🔄 DEDUPLICAÇÃO DE MENSAGENS WHATSAPP
# ============================================================
processed_messages = set()  # Armazena IDs de mensagens já processadas

async def executar_cobranca_agendada():
    """Função executada pelo scheduler para verificar boletos vencendo"""
    logging.warning("⏰ Executando verificação agendada de cobranças...")
    try:
        from sienge.sienge_cobranca import verificar_boletos_vencendo, gerar_mensagem_cobranca
        from supabase_client import salvar_historico_cobranca, atualizar_historico_cobranca
        from datetime import datetime
        boletos = verificar_boletos_vencendo()
        
        if not boletos:
            logging.warning("✅ Nenhum boleto para cobrança")
            return
        
        logging.warning(f"📊 {len(boletos)} boletos encontrados para cobrança")
        
        for boleto in boletos:
            mensagem = gerar_mensagem_cobranca(boleto)
            
            # Salvar registro no histórico antes de tentar enviar
            try:
                dados_historico = {
                    "cliente_id": boleto.get("cliente_id"),
                    "cliente_nome": boleto.get("cliente_nome"),
                    "cliente_telefone": boleto.get("cliente_telefone"),
                    "titulo_id": boleto.get("titulo_id"),
                    "parcela_id": boleto.get("parcela_id"),
                    "vencimento": boleto.get("vencimento"),
                    "valor": boleto.get("valor"),
                    "dias_antes": boleto.get("dias_antes"),
                    "mensagem_template": boleto.get("mensagem_template"),
                    "mensagem_enviada": mensagem,
                    "status": "pendente",
                    "tipo_envio": "pdf" if boleto.get("envio_pdf") else "texto"
                }
                logging.warning(f"💾 Salvando histórico com cliente_id: {boleto.get('cliente_id')}")
                logging.warning(f"💾 Dados completos: {dados_historico}")
                historico_salvo = salvar_historico_cobranca(dados_historico)
                historico_id = historico_salvo.get("id") if isinstance(historico_salvo, dict) else historico_salvo
                logging.warning(f"💾 Histórico salvo no Supabase: {historico_id}")
            except Exception as e:
                logging.warning(f"⚠️ Erro ao salvar histórico: {e}")
                historico_id = None
            
            # Verificar se há telefone válido
            if not boleto.get("cliente_telefone"):
                erro_msg = f"Cliente {boleto.get('cliente_nome')} não possui telefone cadastrado"
                logging.warning(f"⚠️ {erro_msg}")
                if historico_id:
                    try:
                        atualizar_historico_cobranca(historico_id, {
                            "status": "erro",
                            "erro_mensagem": erro_msg
                        })
                        logging.warning(f"✅ Status atualizado para erro")
                    except Exception as e:
                        logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                continue
                
            # Enviar via WhatsApp Cloud API se configurado
            if WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN:
                numero = re.sub(r"\D", "", boleto["cliente_telefone"])
                
                # Normalizar número de telefone
                # Adicionar código do país se não tiver
                if not numero.startswith("55"):
                    numero = "55" + numero
                
                # Validar e ajustar número de telefone
                # Brasil: código país (55) + DDD (2 dígitos) + número (8 ou 9 dígitos)
                # Total: 12 ou 13 dígitos
                if len(numero) == 12:
                    # Número de 8 dígitos (antigo), pode precisar adicionar o 9
                    logging.warning(f"⚠️ Número com 8 dígitos detectado: {numero}")
                    # Tentar adicionar o 9 após o DDD
                    ddd = numero[:4]  # 55 + DDD
                    numero_final = ddd + "9" + numero[4:]
                    logging.warning(f"📱 Ajustando para 9 dígitos: {numero_final}")
                    numero = numero_final
                elif len(numero) == 13:
                    # Número de 9 dígitos (padrão atual)
                    pass
                else:
                    erro_msg = f"Cliente {boleto.get('cliente_nome')} com número de telefone inválido: {numero}"
                    logging.warning(f"⚠️ {erro_msg}")
                    if historico_id:
                        try:
                            atualizar_historico_cobranca(historico_id, {
                                "status": "erro",
                                "erro_mensagem": erro_msg
                            })
                            logging.warning(f"✅ Status atualizado para erro")
                        except Exception as e:
                            logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                    continue
                
                if numero.startswith("55"):
                    # Verificar se deve enviar PDF do boleto
                    if boleto.get("envio_pdf"):
                        from sienge.sienge_cobranca import baixar_pdf_boleto
                        titulo_id = boleto.get("titulo_id")
                        parcela_id = boleto.get("parcela_id")
                        pdf_url = boleto.get("pdf_url")  # URL da verificação de aptidão
                        
                        # Baixar PDF do boleto (usando URL da verificação para evitar requisição duplicada)
                        pdf_content = baixar_pdf_boleto(titulo_id, parcela_id, pdf_url)
                        
                        if pdf_content:
                            # Enviar PDF como documento
                            filename = f"boleto_{titulo_id}_{parcela_id}.pdf"
                            logging.warning(f"📤 Enviando PDF via WhatsApp para {numero}")
                            logging.warning(f"🆔 histórico_id: {historico_id}")
                            try:
                                message_id = send_whatsapp_document(numero, pdf_content, filename, mensagem)
                                logging.warning(f"✅ PDF enviado com sucesso para {numero}")
                                logging.warning(f"🆔 message_id retornado: {message_id}")
                                
                                # Salvar log de mensagem enviada com message_id
                                if message_id:
                                    logging.warning(f"💾 Tentando salvar log de mensagem com message_id: {message_id}")
                                    try:
                                        from supabase_client import salvar_log_mensagem
                                        resultado = salvar_log_mensagem({
                                            "usuario_id": f"whatsapp:{numero}",
                                            "telefone": numero,
                                            "mensagem_recebida": None,
                                            "mensagem_enviada": mensagem,
                                            "tipo": "enviada",
                                            "status": "sent",
                                            "whatsapp_message_id": message_id
                                        })
                                        logging.warning(f"💾 Log de mensagem salvo com message_id: {message_id} - Resultado: {resultado}")
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                                else:
                                    logging.warning(f"⚠️ message_id é None, não salvando log")
                                
                                # Atualizar status no histórico
                                if historico_id:
                                    try:
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "enviado",
                                            "enviado_em": datetime.now().isoformat()
                                        })
                                        logging.warning(f"✅ Status atualizado para enviado")
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                            except Exception as e:
                                logging.warning(f"❌ Erro ao enviar PDF via WhatsApp: {e}")
                                # Atualizar status como erro
                                if historico_id:
                                    try:
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "erro",
                                            "erro_mensagem": gerar_mensagem_erro_estruturada(e, "envio de PDF", boleto.get("cliente_nome"))
                                        })
                                    except Exception as e2:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico: {e2}")
                        else:
                            # Se não conseguir baixar PDF, enviar apenas texto
                            logging.warning(f"⚠️ Não foi possível baixar PDF, enviando apenas texto")
                            message_id = send_whatsapp_cloud_message(numero, mensagem)
                            logging.warning(f"✅ Mensagem enviada para {boleto['cliente_nome']}")
                            
                            # Salvar log de mensagem enviada com message_id
                            try:
                                from supabase_client import salvar_log_mensagem
                                salvar_log_mensagem({
                                    "usuario_id": f"whatsapp:{numero}",
                                    "telefone": numero,
                                    "mensagem_recebida": None,
                                    "mensagem_enviada": mensagem,
                                    "tipo": "enviada",
                                    "status": "sent",
                                    "whatsapp_message_id": message_id
                                })
                            except Exception as e:
                                logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                            
                            if historico_id:
                                try:
                                    atualizar_historico_cobranca(historico_id, {
                                        "status": "enviado",
                                        "enviado_em": datetime.now().isoformat()
                                    })
                                    logging.warning(f"✅ Status atualizado para enviado")
                                except Exception as e:
                                    logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                    else:
                        # Enviar apenas texto
                        message_id = send_whatsapp_cloud_message(numero, mensagem)
                        logging.warning(f"✅ Mensagem enviada para {boleto['cliente_nome']}")
                        
                        # Salvar log de mensagem enviada com message_id
                        try:
                            from supabase_client import salvar_log_mensagem
                            salvar_log_mensagem({
                                "usuario_id": f"whatsapp:{numero}",
                                "telefone": numero,
                                "mensagem_recebida": None,
                                "mensagem_enviada": mensagem,
                                "tipo": "enviada",
                                "status": "sent",
                                "whatsapp_message_id": message_id
                            })
                        except Exception as e:
                            logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                        
                        # Atualizar status no histórico
                        if historico_id:
                            try:
                                atualizar_historico_cobranca(historico_id, {
                                    "status": "enviado",
                                    "enviado_em": datetime.now().isoformat()
                                })
                                logging.warning(f"✅ Status atualizado para enviado")
                            except Exception as e:
                                logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
    except Exception as e:
        logging.error(f"❌ Erro na execução agendada: {e}", exc_info=True)

def atualizar_agendamento(horario: str):
    """Atualiza o agendamento com novo horário"""
    global scheduler
    
    # Remover job existente se houver
    remover_agendamento()
    
    # Parse horário (formato HH:MM)
    try:
        hora, minuto = map(int, horario.split(":"))
        logging.warning(f"⏰ Configurando agendamento para {hora}:{minuto} (timezone: {brasilia_tz})")
        
        # Adicionar novo job
        scheduler.add_job(
            executar_cobranca_agendada,
            CronTrigger(hour=hora, minute=minuto, timezone=brasilia_tz),
            id="cobranca_agendada",
            replace_existing=True
        )
        
        # Listar jobs agendados
        jobs = scheduler.get_jobs()
        logging.warning(f"📋 Jobs agendados: {[job.id for job in jobs]}")
        if jobs:
            for job in jobs:
                logging.warning(f"📋 Job {job.id}: próxima execução em {job.next_run_time}")
        
        # Iniciar scheduler se não estiver rodando
        if not scheduler.running:
            scheduler.start()
            logging.warning("✅ Scheduler iniciado")
        else:
            logging.warning("✅ Agendamento atualizado")
    except Exception as e:
        logging.error(f"❌ Erro ao configurar agendamento: {e}", exc_info=True)

def remover_agendamento():
    """Remove o agendamento de cobrança"""
    try:
        scheduler.remove_job("cobranca_agendada")
        logging.warning("✅ Agendamento removido")
    except Exception:
        pass  # Job não existe

# Twilio
from twilio.rest import Client

# === MÓDULOS LOCAIS ===
from sienge.sienge_boletos import buscar_boletos_por_documento, gerar_link_boleto
from sienge.sienge_cobranca import (
    verificar_boletos_vencendo,
    gerar_mensagem_cobranca,
    gerar_relatorio_cobrancas,
)

# ============================================================
# 🚀 CONFIGURAÇÃO DO SERVIDOR FASTAPI
# ============================================================
logging.basicConfig(level=logging.INFO)
logging.warning("🔄 MAIN.PY CARREGADO - VERSÃO COM LOGS WARNING NO TESTAR-COBRANCA")
app = FastAPI()

# ============================================================
# 🌐 CONFIGURAÇÃO CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",
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
                    
                    # Normalizar número de telefone
                    if not numero.startswith("55"):
                        numero = "55" + numero
                    
                    # Ajustar para 9 dígitos se necessário
                    if len(numero) == 12:
                        ddd = numero[:4]
                        numero = ddd + "9" + numero[4:]
                    
                    message_id = send_whatsapp_cloud_message(numero, mensagem)
                    
                    # Salvar log de mensagem enviada com message_id
                    try:
                        from supabase_client import salvar_log_mensagem
                        salvar_log_mensagem({
                            "usuario_id": f"whatsapp:{numero}",
                            "telefone": numero,
                            "mensagem_recebida": None,
                            "mensagem_enviada": mensagem,
                            "tipo": "enviada",
                            "status": "sent",
                            "whatsapp_message_id": message_id
                        })
                    except Exception as e:
                        logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
        logging.info(f"✅ Job de cobrança concluído. {len(boletos)} boletos processados.")
    except Exception as e:
        logging.error(f"❌ Erro no job de cobrança: {e}")

# Job hardcoded removido - usar apenas agendamento dinâmico via configuracao

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
    logging.warning(f"📋 Timezone do scheduler: {scheduler.timezone}")
    jobs = scheduler.get_jobs()
    logging.warning(f"📋 Jobs ativos no startup: {[job.id for job in jobs]}")
    if jobs:
        for job in jobs:
            logging.warning(f"📋 Job {job.id}: próxima execução em {job.next_run_time}")

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

# Log para debug - mostrar configurações do WhatsApp
print(f"📱 WhatsApp Config - Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
print(f"📱 WhatsApp Config - Token configurado: {'✅' if WHATSAPP_TOKEN else '❌'}")
print(f"📱 WhatsApp Config - Verify Token: {WHATSAPP_VERIFY_TOKEN}")
logging.info(f"📱 WhatsApp Config - Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
logging.info(f"📱 WhatsApp Config - Token configurado: {'✅' if WHATSAPP_TOKEN else '❌'}")
logging.info(f"📱 WhatsApp Config - Verify Token: {WHATSAPP_VERIFY_TOKEN}")

# ============================================================
# 📩 MODELOS DE DADOS
# ============================================================
class Message(BaseModel):
    user: str
    text: str


def gerar_mensagem_erro_estruturada(erro: Exception, contexto: str = "", cliente_nome: str = "") -> str:
    """
    Gera mensagem de erro estruturada e descritiva
    """
    erro_str = str(erro).lower()
    
    # Erros específicos de telefone
    if "telefone" in erro_str or "phone" in erro_str or "celular" in erro_str:
        return f"Cliente {cliente_nome} sem telefone cadastrado ou inválido"
    
    # Erros específicos de PDF
    if "pdf" in erro_str or "documento" in erro_str:
        return f"Erro ao processar PDF: {erro}"
    
    # Erros específicos de WhatsApp
    if "whatsapp" in erro_str or "meta" in erro_str:
        return f"Erro ao enviar via WhatsApp: {erro}"
    
    # Erros específicos de Sienge
    if "sienge" in erro_str or "api" in erro_str:
        return f"Erro ao buscar dados no Sienge: {erro}"
    
    # Erros específicos de Supabase
    if "supabase" in erro_str or "banco" in erro_str or "database" in erro_str:
        return f"Erro ao salvar no banco de dados: {erro}"
    
    # Erro genérico com contexto
    if contexto:
        return f"Erro em {contexto}: {erro}"
    
    # Erro genérico
    return f"Erro: {erro}"

class SiengeConfig(BaseModel):
    subdomain: str
    username: str
    password: str

class LembreteCobranca(BaseModel):
    dias_antes: int
    mensagem: str
    enviar_segunda_via: bool
    envio_pdf: bool = False

class ConfiguracaoCobranca(BaseModel):
    ativo: bool
    horario_execucao: str = "09:00"
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

# ============================================================
#  INTERPRETAÇÃO DE INTENÇÃO
# ============================================================
def entender_intencao(texto: str):
    t = (texto or "").strip().lower()
    logging.warning(f"🔍 Analisando intenção para texto: '{t}'")

    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"]:
        return {"acao": "saudacao"}
    
    # Verificar se é comando de boleto com formato "boleto X Y"
    if re.match(r"^boleto\s+\d+\s+\d+$", t):
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            logging.warning(f"✅ Intenção reconhecida: link_boleto com titulo_id={nums[-2]}, parcela_id={nums[-1]}")
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
    
    if "segunda via" in t or "boleto" in t:
        nums = re.findall(r"\d+", t)
        if len(nums) >= 2:
            logging.warning(f"✅ Intenção reconhecida: link_boleto com titulo_id={nums[-2]}, parcela_id={nums[-1]}")
            return {"acao": "link_boleto", "parametros": {"titulo_id": int(nums[-2]), "parcela_id": int(nums[-1])}}
        return {"acao": "buscar_boletos_cpf"}
    
    if re.search(r"\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}
    if re.search(r"\d{14}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", t):
        return {"acao": "cpf_digitado", "parametros": {"cpf": t}}
    if "confirmar" in t:
        return {"acao": "confirmar"}
    if "cobrança" in t or "cobranca" in t or "vencendo" in t:
        return {"acao": "relatorio_cobrancas"}
    
    logging.warning(f"⚠️ Nenhuma intenção reconhecida para: '{t}'")
    return {"acao": None}

# ============================================================
# 💬 ENDPOINT PRINCIPAL DE MENSAGENS (JÁ FUNCIONAVA)
# ============================================================
@app.post("/mensagem")
async def mensagem(msg: Message):
    logging.info(f"📩 Mensagem recebida: {msg.user} -> {msg.text}")
    texto = (msg.text or "").strip()

    intencao = entender_intencao(texto)
    acao = intencao.get("acao")
    parametros = intencao.get("parametros", {}) or {}

    menu_inicial = [
        {"label": "2ª Via de Boletos", "action": "buscar_boletos_cpf"},
        {"label": " Relatório de Cobranças", "action": "relatorio_cobrancas"},
    ]

    if not texto or acao == "saudacao" or acao == "menu_inicial":
        return {
            "text": "👋 Olá! Sou a Constru.IA.\n"
                    "Posso te ajudar com: Segunda via de boletos e Relatório de cobranças.\n"
                    "Digite seu CPF ou CNPJ para começar.",
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
            return {
                "text": "💳 Digite o CPF ou CNPJ do titular dos boletos:",
                "buttons": [{"label": "⬅️ Voltar ao menu", "action": "menu_inicial"}]
            }

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

            # Se houver muitos boletos, usa list message
            if len(boletos) > 3:
                list_items = []
                for b in boletos[:10]:  # Limite de 10 itens
                    titulo, parcela = b["titulo_id"], b["parcela_id"]
                    valor, venc, desc = b.get("valor", 0.0), b.get("vencimento"), b.get("descricao", "-")
                    list_items.append({
                        "titulo_id": titulo,
                        "parcela_id": parcela,
                        "title": f"Boleto {titulo}/{parcela}",
                        "description": f"R$ {valor:,.2f} - Venc: {venc}"
                    })
                
                # Armazena boletos no contexto para recuperar quando selecionar
                usuarios_contexto[msg.user] = {
                    "documento": documento,
                    "nome": nome,
                    "boletos_disponiveis": list_items
                }
                
                return {
                    "text": f"✅ *Encontrei {len(boletos)} boletos para {nome}.*\n\nSelecione um boleto abaixo para gerar a segunda via:",
                    "list_items": list_items,
                    "buttons": [{"label": "⬅️ Voltar ao menu", "action": "menu_inicial"}],
                }
            
            # Se houver poucos boletos, usa botões
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

            # Manter documento e nome no contexto para uso posterior
            usuarios_contexto[msg.user] = {
                "documento": documento,
                "nome": nome
            }
            return {
                "text": f"✅ *Boletos disponíveis para {nome}:*\n\n" + "\n\n".join(linhas[:15]),
                "buttons": botoes
                + [
                    {"label": "Nova busca por CPF", "action": "buscar_boletos_cpf"},
                    {"label": "⬅️ Voltar ao menu", "action": "menu_inicial"},
                ],
            }

        if acao == "link_boleto":
            t, p = parametros.get("titulo_id"), parametros.get("parcela_id")
            logging.warning(f"🔍 Processando link_boleto: titulo_id={t}, parcela_id={p}")
            
            # Baixar PDF do boleto e enviar como anexo
            try:
                from sienge.sienge_cobranca import baixar_pdf_boleto, tem_boleto_apto
                # Verificar aptidão e obter URL do PDF em uma requisição
                apta, pdf_url = tem_boleto_apto(t, p)
                logging.warning(f"🔍 Aptidão: {apta}, pdf_url: {pdf_url}")
                if not apta:
                    return {"text": "❌ Boleto não disponível para download", "buttons": menu_inicial}
                pdf_content = baixar_pdf_boleto(t, p, pdf_url)
                logging.warning(f"🔍 PDF baixado: {pdf_content is not None}, tamanho: {len(pdf_content) if pdf_content else 0}")
                
                if pdf_content:
                    # Extrair número do usuário do contexto (quem está enviando a mensagem)
                    ctx = usuarios_contexto.get(msg.user, {})
                    documento = ctx.get("documento", "")
                    logging.warning(f"🔍 Documento do contexto: {documento}")
                    
                    # Usar o número do WhatsApp do usuário que está enviando a mensagem
                    # msg.user está no formato "whatsapp:559193808761"
                    numero = msg.user.replace("whatsapp:", "")
                    logging.warning(f"🔍 Usando número do usuário: {numero}")
                    
                    # Enviar PDF
                    filename = f"boleto_{t}_{p}.pdf"
                    message_id = send_whatsapp_document(numero, pdf_content, filename, f"📄 Segunda via do boleto {t}/{p}")
                    logging.warning(f"🔍 message_id retornado: {message_id}")
                    
                    # Salvar log de mensagem enviada
                    try:
                        from supabase_client import salvar_log_mensagem
                        dados_log = {
                            "usuario_id": f"whatsapp:{numero}",
                            "telefone": numero,
                            "mensagem_recebida": None,
                            "mensagem_enviada": f"PDF do boleto {t}/{p}",
                            "tipo": "enviada",
                            "status": "sent"
                        }
                        if message_id:
                            dados_log["whatsapp_message_id"] = message_id
                            logging.info(f"💾 Log de mensagem salvo com message_id: {message_id}")
                        salvar_log_mensagem(dados_log)
                    except Exception as e:
                        logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                    
                    logging.warning(f"✅ Retornando sucesso")
                    return {
                        "text": f"✅ *PDF do boleto {t}/{p} enviado com sucesso!*",
                        "buttons": menu_inicial
                    }
                else:
                    logging.warning(f"⚠️ PDF content vazio")
                    return {"text": "❌ Erro ao baixar PDF do boleto", "buttons": menu_inicial}
            except Exception as e:
                logging.warning(f"⚠️ Erro ao baixar/enviar PDF: {e}")
                import traceback
                logging.warning(traceback.format_exc())
                return {"text": f"❌ Erro ao gerar boleto: {e}", "buttons": menu_inicial}

        # ========================================================
        # 🔔 COBRANÇA
        # ========================================================
        if acao == "relatorio_cobrancas":
            # Verificar boletos vencendo baseado nas configurações
            relatorio = gerar_relatorio_cobrancas()
            return {
                "text": relatorio,
                "buttons": menu_inicial,
            }

        return {
            "text": "🤖 Não entendi. Digite seu CPF ou CNPJ para buscar boletos.",
            "buttons": menu_inicial,
        }

    except Exception as e:
        logging.exception("❌ Erro geral:")
        return {"text": f"Ocorreu um erro: {e}", "buttons": menu_inicial}

# ============================================================
# 🧪 ENDPOINT PARA TESTAR COBRANÇA MANUALMENTE
# ============================================================
@app.get("/cobranca-historico")
async def listar_historico_cobrancas(
    data_inicio: str = None,
    data_fim: str = None,
    cliente: str = None
):
    """
    Endpoint para listar histórico de cobranças do Supabase
    Aceita filtros opcionais: data_inicio, data_fim, cliente
    """
    try:
        from supabase_client import buscar_historico_cobrancas
        historico = buscar_historico_cobrancas()
        
        # Aplicar filtros
        if data_inicio or data_fim or cliente:
            historico_filtrado = []
            for item in historico:
                # Filtro de data
                if data_inicio:
                    item_data = item.get("created_at", "")
                    if item_data < data_inicio:
                        continue
                if data_fim:
                    item_data = item.get("created_at", "")
                    if item_data > data_fim:
                        continue
                
                # Filtro de cliente
                if cliente:
                    item_cliente = item.get("cliente_nome", "").lower()
                    if cliente.lower() not in item_cliente:
                        continue
                
                historico_filtrado.append(item)
            historico = historico_filtrado
        
        # Formatar dados para o frontend
        historico_formatado = []
        for item in historico:
            historico_formatado.append({
                "id": item.get("id"),
                "cliente": item.get("cliente_nome"),
                "telefone": item.get("cliente_telefone"),
                "data": item.get("created_at"),
                "status": item.get("status"),
                "mensagem": item.get("mensagem_enviada"),
                "vencimento": item.get("vencimento"),
                "valor": item.get("valor"),
                "tipo_envio": item.get("tipo_envio"),
                "titulo_id": item.get("titulo_id"),
                "parcela_id": item.get("parcela_id"),
                "dias_antes": item.get("dias_antes"),
                "cliente_id": item.get("cliente_id"),
                "erro_mensagem": item.get("erro_mensagem")
            })
        
        return {"historico": historico_formatado}
    except Exception as e:
        logging.error(f"❌ Erro ao buscar histórico de cobranças: {e}")
        return {"historico": []}

def _filtrar_historico(data_inicio=None, data_fim=None, cliente=None):
    from supabase_client import buscar_historico_cobrancas
    historico = buscar_historico_cobrancas() or []
    out = []
    for item in historico:
        item_data = item.get("created_at", "") or ""
        if data_inicio and item_data < data_inicio:
            continue
        if data_fim and item_data > data_fim + "T23:59:59":
            continue
        if cliente and cliente.lower() not in (item.get("cliente_nome") or "").lower():
            continue
        out.append(item)
    return out

@app.get("/logs-mensagens")
async def buscar_logs_mensagens_endpoint(telefone: str = None, tipo: str = None, data_inicio: str = None, data_fim: str = None):
    """Endpoint para buscar logs de mensagens"""
    try:
        from supabase_client import buscar_logs_mensagens
        
        filtros = {}
        if telefone:
            filtros["telefone"] = telefone
        if tipo:
            filtros["tipo"] = tipo
        if data_inicio:
            filtros["data_inicio"] = data_inicio
        if data_fim:
            filtros["data_fim"] = data_fim
        
        logs = buscar_logs_mensagens(filtros)
        return {"logs": logs}
    except Exception as e:
        logging.error(f"❌ Erro ao buscar logs de mensagens: {e}")
        return {"logs": []}

@app.get("/cobranca-historico/export/excel")
async def exportar_historico_excel(data_inicio: str = None, data_fim: str = None, cliente: str = None):
    from openpyxl import Workbook
    historico = _filtrar_historico(data_inicio, data_fim, cliente)
    wb = Workbook()
    ws = wb.active
    ws.title = "Historico Cobrancas"
    headers = ["Data", "Cliente", "Telefone", "Status", "Titulo", "Parcela", "Vencimento", "Valor", "Tipo Envio", "Mensagem"]
    ws.append(headers)
    for it in historico:
        ws.append([
            it.get("created_at", ""),
            it.get("cliente_nome", ""),
            it.get("cliente_telefone", ""),
            it.get("status", ""),
            it.get("titulo_id", ""),
            it.get("parcela_id", ""),
            it.get("vencimento", ""),
            it.get("valor", ""),
            it.get("tipo_envio", ""),
            (it.get("mensagem_enviada") or "")[:500],
        ])
    for col_idx, _ in enumerate(headers, 1):
        ws.column_dimensions[chr(64+col_idx)].width = 20
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=historico_cobrancas.xlsx"},
    )

@app.get("/cobranca-historico/export/pdf")
async def exportar_historico_pdf(data_inicio: str = None, data_fim: str = None, cliente: str = None):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    historico = _filtrar_historico(data_inicio, data_fim, cliente)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    story = [Paragraph("Relatório de Cobranças", styles["Title"])]
    filtros = []
    if data_inicio: filtros.append(f"De: {data_inicio}")
    if data_fim: filtros.append(f"Até: {data_fim}")
    if cliente: filtros.append(f"Cliente: {cliente}")
    if filtros:
        story.append(Paragraph(" | ".join(filtros), styles["Normal"]))
    story.append(Paragraph(f"Total de registros: {len(historico)}", styles["Normal"]))
    story.append(Spacer(1, 12))
    data = [["Data", "Cliente", "Telefone", "Status", "Vencimento", "Valor"]]
    for it in historico:
        valor = it.get("valor")
        valor_str = f"R$ {float(valor):.2f}" if valor else ""
        data.append([
            (it.get("created_at") or "")[:16],
            (it.get("cliente_nome") or "")[:30],
            it.get("cliente_telefone") or "",
            it.get("status") or "",
            (it.get("vencimento") or "")[:10],
            valor_str,
        ])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=historico_cobrancas.pdf"},
    )

@app.post("/testar-cobranca")
async def testar_cobranca():
    """
    Endpoint para testar manualmente o sistema de cobrança
    """
    logging.warning("🧪 Iniciando teste manual de cobrança...")
    logging.warning("🧪 Chamando verificar_boletos_vencendo()...")
    try:
        boletos = verificar_boletos_vencendo()
        logging.warning(f"📋 verificar_boletos_vencendo() retornou {len(boletos)} boletos")
        
        resultados = []
        for boleto in boletos:
            if boleto.get("cliente_telefone"):
                numero = re.sub(r"\D", "", boleto.get("cliente_telefone"))
                mensagem = gerar_mensagem_cobranca(boleto)
                
                # Verificar se cobrança já foi enviada (evitar duplicação via Supabase)
                try:
                    from supabase_client import verificar_cobranca_enviada
                    titulo_id = boleto.get("titulo_id")
                    parcela_id = boleto.get("parcela_id")
                    dias_antes = boleto.get("dias_antes")
                    
                    if verificar_cobranca_enviada(titulo_id, parcela_id, dias_antes):
                        logging.warning(f"⏭️ Cobrança já enviada para {boleto.get('cliente_nome')}, ignorando")
                        resultados.append({
                            "cliente": boleto.get("cliente_nome"),
                            "telefone": numero,
                            "status": "já enviado (duplicado)",
                        })
                        continue
                except Exception as e:
                    logging.warning(f"⚠️ Erro ao verificar duplicação: {e}")
                
                # Salvar registro no histórico antes de enviar
                try:
                    from supabase_client import salvar_historico_cobranca
                    from datetime import datetime
                    historico_salvo = salvar_historico_cobranca({
                        "cliente_id": boleto.get("cliente_id"),
                        "cliente_nome": boleto.get("cliente_nome"),
                        "cliente_telefone": boleto.get("cliente_telefone"),
                        "titulo_id": boleto.get("titulo_id"),
                        "parcela_id": boleto.get("parcela_id"),
                        "vencimento": boleto.get("vencimento"),
                        "valor": boleto.get("valor"),
                        "dias_antes": boleto.get("dias_antes"),
                        "mensagem_template": boleto.get("mensagem_template"),
                        "mensagem_enviada": mensagem,
                        "status": "pendente",
                        "tipo_envio": "pdf" if boleto.get("enviar_segunda_via") else "texto"
                    })
                    # Extrair apenas o UUID do dicionário retornado
                    historico_id = historico_salvo.get("id") if isinstance(historico_salvo, dict) else historico_salvo
                    logging.warning(f"💾 Histórico salvo no Supabase: {historico_id}")
                except Exception as e:
                    logging.warning(f"⚠️ Erro ao salvar histórico: {e}")
                
                # Enviar via WhatsApp Cloud API se configurado
                if WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN:
                    numero = re.sub(r"\D", "", boleto["cliente_telefone"])
                    # Adicionar código do país 55 se for número brasileiro (10 ou 11 dígitos)
                    if len(numero) == 11 or len(numero) == 10:
                        numero = "55" + numero
                    if numero.startswith("55"):
                        # Verificar se deve enviar PDF do boleto
                        if boleto.get("envio_pdf"):
                            from sienge.sienge_cobranca import baixar_pdf_boleto
                            titulo_id = boleto.get("titulo_id")
                            parcela_id = boleto.get("parcela_id")
                            pdf_url = boleto.get("pdf_url")  # URL da verificação de aptidão
                            
                            # Baixar PDF do boleto (usando URL da verificação para evitar requisição duplicada)
                            pdf_content = baixar_pdf_boleto(titulo_id, parcela_id, pdf_url)
                            
                            if pdf_content:
                                # Enviar PDF como documento
                                filename = f"boleto_{titulo_id}_{parcela_id}.pdf"
                                logging.warning(f"📤 Enviando PDF via WhatsApp para {numero}")
                                logging.warning(f"🆔 histórico_id: {historico_id}")
                                try:
                                    message_id = send_whatsapp_document(numero, pdf_content, filename, mensagem)
                                    logging.warning(f"✅ PDF enviado com sucesso para {numero}")
                                    
                                    # Salvar log de mensagem enviada com message_id
                                    if message_id:
                                        try:
                                            from supabase_client import salvar_log_mensagem
                                            salvar_log_mensagem({
                                                "usuario_id": f"whatsapp:{numero}",
                                                "telefone": numero,
                                                "mensagem_recebida": None,
                                                "mensagem_enviada": mensagem,
                                                "tipo": "enviada",
                                                "status": "sent",
                                                "whatsapp_message_id": message_id
                                            })
                                            logging.info(f"💾 Log de mensagem salvo com message_id: {message_id}")
                                        except Exception as e:
                                            logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                                    
                                    # Atualizar status no histórico
                                    logging.warning(f"🔄 Atualizando status no Supabase...")
                                    try:
                                        from supabase_client import atualizar_historico_cobranca
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "enviado",
                                            "enviado_em": datetime.now().isoformat()
                                        })
                                        logging.warning(f"✅ Status atualizado para enviado")
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                                    resultados.append({
                                        "cliente": boleto.get("cliente_nome"),
                                        "telefone": numero,
                                        "status": "enviado (PDF)",
                                        "mensagem": mensagem[:100]
                                    })
                                except Exception as e:
                                    logging.warning(f"❌ Erro ao enviar PDF via WhatsApp: {e}")
                                    # Atualizar status como erro
                                    try:
                                        from supabase_client import atualizar_historico_cobranca
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "erro",
                                            "erro_mensagem": gerar_mensagem_erro_estruturada(e, "envio de PDF", boleto.get("cliente_nome"))
                                        })
                                    except Exception as e2:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico com erro: {e2}")
                            else:
                                # Se falhar ao baixar PDF, enviar apenas mensagem
                                logging.warning(f"📤 Enviando mensagem de texto para {numero}")
                                try:
                                    message_id = send_whatsapp_cloud_message(numero, mensagem)
                                    logging.warning(f"✅ Mensagem enviada com sucesso para {numero}")
                                    
                                    # Salvar log de mensagem enviada com message_id
                                    try:
                                        from supabase_client import salvar_log_mensagem
                                        salvar_log_mensagem({
                                            "usuario_id": f"whatsapp:{numero}",
                                            "telefone": numero,
                                            "mensagem_recebida": None,
                                            "mensagem_enviada": mensagem,
                                            "tipo": "enviada",
                                            "status": "sent",
                                            "whatsapp_message_id": message_id
                                        })
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                                    
                                    # Atualizar status no histórico
                                    try:
                                        from supabase_client import atualizar_historico_cobranca
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "enviado",
                                            "tipo_envio": "texto",
                                            "erro_mensagem": "PDF falhou, enviado como texto",
                                            "enviado_em": datetime.now().isoformat()
                                        })
                                    except Exception as e:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                                    resultados.append({
                                        "cliente": boleto.get("cliente_nome"),
                                        "telefone": numero,
                                        "status": "enviado (texto apenas - PDF falhou)",
                                        "mensagem": mensagem[:100]
                                    })
                                except Exception as e:
                                    logging.warning(f"❌ Erro ao enviar mensagem via WhatsApp: {e}")
                                    # Atualizar status como erro
                                    try:
                                        from supabase_client import atualizar_historico_cobranca
                                        atualizar_historico_cobranca(historico_id, {
                                            "status": "erro",
                                            "erro_mensagem": gerar_mensagem_erro_estruturada(e, "envio de mensagem", boleto.get("cliente_nome"))
                                        })
                                    except Exception as e2:
                                        logging.warning(f"⚠️ Erro ao atualizar histórico com erro: {e2}")
                        else:
                            # Enviar apenas mensagem de texto
                            logging.warning(f"📤 Enviando mensagem de texto para {numero}")
                            try:
                                message_id = send_whatsapp_cloud_message(numero, mensagem)
                                logging.warning(f"✅ Mensagem enviada com sucesso para {numero}")
                                
                                # Salvar log de mensagem enviada com message_id
                                try:
                                    from supabase_client import salvar_log_mensagem
                                    salvar_log_mensagem({
                                        "usuario_id": f"whatsapp:{numero}",
                                        "telefone": numero,
                                        "mensagem_recebida": None,
                                        "mensagem_enviada": mensagem,
                                        "tipo": "enviada",
                                        "status": "sent",
                                        "whatsapp_message_id": message_id
                                    })
                                except Exception as e:
                                    logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
                                
                                # Atualizar status no histórico
                                try:
                                    from supabase_client import atualizar_historico_cobranca
                                    atualizar_historico_cobranca(historico_id, {
                                        "status": "enviado",
                                        "enviado_em": datetime.now().isoformat()
                                    })
                                    logging.warning(f"✅ Status atualizado para enviado")
                                except Exception as e:
                                    logging.warning(f"⚠️ Erro ao atualizar histórico: {e}")
                                resultados.append({
                                    "cliente": boleto.get("cliente_nome"),
                                    "telefone": numero,
                                    "status": "enviado (texto)",
                                    "mensagem": mensagem[:100]
                                })
                            except Exception as e:
                                logging.warning(f"❌ Erro ao enviar mensagem via WhatsApp: {e}")
                                # Atualizar status como erro
                                try:
                                    from supabase_client import atualizar_historico_cobranca
                                    atualizar_historico_cobranca(historico_id, {
                                        "status": "erro",
                                        "erro_mensagem": gerar_mensagem_erro_estruturada(e, "envio de mensagem", boleto.get("cliente_nome"))
                                    })
                                except Exception as e2:
                                    logging.warning(f"⚠️ Erro ao atualizar histórico com erro: {e2}")
                    else:
                        resultados.append({
                            "cliente": boleto.get("cliente_nome"),
                            "telefone": numero,
                            "status": "ignorado (não brasileiro)",
                        })
                else:
                    resultados.append({
                        "cliente": boleto.get("cliente_nome"),
                        "telefone": boleto.get("cliente_telefone"),
                        "status": "não enviado (WhatsApp não configurado)",
                        "mensagem": mensagem[:100]
                    })
            else:
                resultados.append({
                    "cliente": boleto.get("cliente_nome"),
                    "status": "sem telefone",
                })
        
        logging.warning(f"🧪 Teste concluído: {len(resultados)} resultados")
        return {
            "total_boletos": len(boletos),
            "enviados": len([r for r in resultados if r.get("status") == "enviado"]),
            "resultados": resultados
        }
    except Exception as e:
        logging.exception("❌ Erro ao testar cobrança:")
        return {"error": str(e)}


@app.get("/cobranca-config")
async def carregar_configuracao_cobranca_api():
    """
    Carrega configurações de cobrança do Supabase
    """
    try:
        from supabase_client import buscar_configuracao_cobranca
        config_supabase = buscar_configuracao_cobranca()
        
        if config_supabase:
            logging.info(f"✅ Configuração carregada do Supabase: {len(config_supabase.get('lembretes', []))} lembretes")
            return {
                "ativo": config_supabase.get("ativo", False),
                "horario_execucao": config_supabase.get("horario_execucao", "09:00"),
                "lembretes": config_supabase.get("lembretes", [])
            }
    except Exception as e:
        logging.warning(f"⚠️ Erro ao carregar configuração do Supabase: {e}")
    
    # Fallback para arquivo JSON
    import json
    from pathlib import Path
    
    config_file = Path(__file__).parent / "cobranca_config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"✅ Configuração carregada do JSON: {len(config.get('lembretes', []))} lembretes")
                return config
        except Exception as e:
            logging.error(f"❌ Erro ao carregar configuração de cobrança: {e}")
            return {"ativo": False, "lembretes": []}
    
    # Configuração padrão
    return {"ativo": False, "horario_execucao": "09:00", "lembretes": []}


@app.post("/invalidar-cache")
async def invalidar_cache_api(cache_key: str = "lista_clientes"):
    """
    Invalida um cache específico manualmente
    Útil quando dados são atualizados no Sienge e precisam ser recarregados
    """
    try:
        from sienge.sienge_cobranca import invalidar_cache
        resultado = invalidar_cache(cache_key)
        if resultado:
            return {"status": "success", "message": f"Cache {cache_key} invalidado com sucesso"}
        else:
            return {"status": "error", "message": f"Cache {cache_key} não existe ou erro ao invalidar"}
    except Exception as e:
        logging.error(f"❌ Erro ao invalidar cache: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/atualizar-cliente-sienge")
async def atualizar_cliente_sienge(cliente_id: str = None, cliente_nome: str = None, historico_id: str = None):
    """
    Atualiza dados de um cliente específico do Sienge
    Invalida o cache e busca dados atualizados
    Aceita cliente_id ou cliente_nome como parâmetro
    Se historico_id for fornecido, atualiza o registro no Supabase
    """
    logging.warning(f"🔄 Iniciando atualização do cliente - ID: {cliente_id}, Nome: {cliente_nome}, Histórico: {historico_id}")
    try:
        from sienge.sienge_cobranca import invalidar_cache
        from sienge.sienge_config import BASE_URL, json_headers
        from supabase_client import atualizar_historico_cobranca
        import requests
        
        # Invalidar cache de clientes
        logging.warning(f"🗑️ Invalidando cache de clientes...")
        invalidar_cache("lista_clientes")
        
        # Buscar dados atualizados do cliente
        if cliente_id:
            logging.warning(f"📡 Buscando dados do cliente por ID {cliente_id} no Sienge...")
            url = f"{BASE_URL}/customers/{cliente_id}"
        elif cliente_nome:
            logging.warning(f"📡 Buscando dados do cliente por nome {cliente_nome} no Sienge...")
            url = f"{BASE_URL}/customers?name={cliente_nome}"
        else:
            return {"status": "error", "message": "cliente_id ou cliente_nome é obrigatório"}
        
        logging.warning(f"📡 URL: {url}")
        r = requests.get(url, headers=json_headers, timeout=30)
        logging.warning(f"📡 Status code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            # Se busca por nome, pegar o primeiro resultado
            if cliente_nome and isinstance(data, dict) and "results" in data:
                cliente_data = data["results"][0] if data["results"] else None
            else:
                cliente_data = data
            
            if cliente_data:
                logging.warning(f"✅ Dados do cliente atualizados: {cliente_data}")
                # Se busca por nome, usar o ID retornado para buscar novamente os dados atualizados
                if cliente_nome and cliente_data.get("id"):
                    logging.warning(f"📡 Buscando novamente dados do cliente por ID {cliente_data['id']} para garantir dados atualizados...")
                    url_id = f"{BASE_URL}/customers/{cliente_data['id']}"
                    r_id = requests.get(url_id, headers=json_headers, timeout=30)
                    if r_id.status_code == 200:
                        cliente_data = r_id.json()
                        logging.warning(f"✅ Dados do cliente atualizados por ID: {cliente_data}")
                
                # Extrair telefone dos dados do cliente
                telefone = None
                phones = cliente_data.get("phones", [])
                if phones:
                    for phone in phones:
                        if phone.get("main"):
                            telefone = phone.get("number")
                            break
                    if not telefone:
                        telefone = phones[0].get("number")
                
                logging.warning(f"📱 Telefone extraído: {telefone}")
                
                # Se historico_id foi fornecido, atualizar o registro no Supabase
                if historico_id:
                    logging.warning(f"💾 Atualizando histórico {historico_id} no Supabase...")
                    dados_atualizacao = {
                        "cliente_id": cliente_data.get("id"),
                        "cliente_telefone": telefone
                    }
                    atualizar_historico_cobranca(historico_id, dados_atualizacao)
                    logging.warning(f"✅ Histórico atualizado no Supabase")
                
                return {
                    "status": "success",
                    "message": "Dados do cliente atualizados com sucesso",
                    "cliente": cliente_data,
                    "telefone": telefone
                }
            else:
                return {"status": "error", "message": "Cliente não encontrado"}
        else:
            logging.warning(f"⚠️ Erro ao buscar dados do cliente: {r.status_code} - {r.text}")
            return {
                "status": "error",
                "message": f"Erro ao buscar dados do cliente: {r.status_code}"
            }
    except Exception as e:
        logging.error(f"❌ Erro ao atualizar cliente do Sienge: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/reenviar-cobranca")
async def reenviar_cobranca(historico_id: str):
    """
    Reenvia cobrança para um cliente específico baseado no histórico
    Atualiza o status do histórico existente em vez de criar um novo
    """
    try:
        from supabase_client import buscar_historico_por_id, atualizar_historico_cobranca, salvar_log_mensagem
        from datetime import datetime
        
        # Buscar histórico da cobrança
        historico = buscar_historico_por_id(historico_id)
        
        if not historico:
            return {"status": "error", "message": "Histórico não encontrado"}
        
        # Preparar dados do boleto
        boleto = {
            "cliente_id": historico.get("cliente_id"),
            "cliente_nome": historico.get("cliente_nome"),
            "cliente_telefone": historico.get("cliente_telefone"),
            "titulo_id": historico.get("titulo_id"),
            "parcela_id": historico.get("parcela_id"),
            "vencimento": historico.get("vencimento"),
            "valor": historico.get("valor"),
            "dias_antes": historico.get("dias_antes"),
            "mensagem_template": historico.get("mensagem_template"),
            "envio_pdf": historico.get("tipo_envio") == "pdf"
        }
        
        # Invalidar cache para garantir dados atualizados
        from sienge.sienge_cobranca import invalidar_cache
        invalidar_cache("lista_clientes")
        
        # Gerar mensagem
        mensagem = gerar_mensagem_cobranca(boleto)
        
        # Verificar telefone
        if not boleto.get("cliente_telefone"):
            return {"status": "error", "message": "Cliente não possui telefone cadastrado"}
        
        numero = re.sub(r"\D", "", boleto["cliente_telefone"])
        if len(numero) == 11 or len(numero) == 10:
            numero = "55" + numero
        
        if not numero.startswith("55"):
            return {"status": "error", "message": "Número de telefone inválido"}
        
        # Enviar via WhatsApp
        if WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN:
            try:
                message_id = None
                if boleto.get("envio_pdf"):
                    from sienge.sienge_cobranca import baixar_pdf_boleto
                    pdf_url = boleto.get("pdf_url")  # URL da verificação de aptidão
                    pdf_content = baixar_pdf_boleto(boleto["titulo_id"], boleto["parcela_id"], pdf_url)
                    
                    if pdf_content:
                        filename = f"boleto_{boleto['titulo_id']}_{boleto['parcela_id']}.pdf"
                        message_id = send_whatsapp_document(numero, pdf_content, filename, mensagem)
                    else:
                        # Se não conseguir baixar PDF, não enviar (mesma lógica da cobrança automática)
                        logging.warning(f"⚠️ Não foi possível baixar o PDF para título {boleto['titulo_id']}, parcela {boleto['parcela_id']}")
                        return {"status": "error", "message": "Não foi possível baixar o PDF do boleto. A cobrança não pode ser reenviada."}
                else:
                    message_id = send_whatsapp_cloud_message(numero, mensagem)
                
                # Atualizar histórico existente
                logging.warning(f"💾 Atualizando histórico {historico_id} no Supabase...")
                atualizar_historico_cobranca(historico_id, {
                    "status": "enviado",
                    "enviado_em": datetime.now().isoformat()
                })
                logging.warning(f"✅ Histórico atualizado no Supabase")
                
                if message_id:
                    salvar_log_mensagem({
                        "usuario_id": f"whatsapp:{numero}",
                        "telefone": numero,
                        "mensagem_recebida": None,
                        "mensagem_enviada": mensagem,
                        "tipo": "enviada",
                        "status": "sent",
                        "whatsapp_message_id": message_id
                    })
                
                return {
                    "status": "success",
                    "message": "Cobrança reenviada com sucesso",
                    "historico_id": historico_id
                }
            except Exception as e:
                logging.error(f"❌ Erro ao reenviar cobrança: {e}")
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "error", "message": "WhatsApp não configurado"}
    except Exception as e:
        logging.error(f"❌ Erro ao reenviar cobrança: {e}")
        return {"status": "error", "message": str(e)}

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

@app.get("/webhook-cobranca")
async def verify_whatsapp_cobranca(request: Request):
    """
    Endpoint de verificação do Meta específico para cobrança (GET)
    """
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        logging.info("✅ Webhook Cobrança verificado pelo Meta.")
        return PlainTextResponse(challenge or "")
    else:
        logging.warning("⚠️ Webhook Cobrança verificação falhou.")
        return PlainTextResponse("Verification failed", status_code=403)

# ============================================================
# 💬 WEBHOOK WHATSAPP CLOUD API (RECEBIMENTO)
# ============================================================
def send_whatsapp_cloud_message(to_number: str, body: str, buttons: list = None, list_items: list = None):
    """
    Envia mensagem de texto usando WhatsApp Cloud API.
    to_number: número sem 'whatsapp:', ex: 559193808761
    buttons: lista de botões interativos
    list_items: lista de itens para list message com links
    """
    if not (WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN):
        logging.error("❌ WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN não configurados.")
        return

    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Se houver itens de lista, usa list message com links
    if list_items and len(list_items) > 0:
        # WhatsApp suporta até 10 itens na lista
        list_items = list_items[:10]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": "📄 Boletos Disponíveis"
                },
                "body": {
                    "text": body
                },
                "action": {
                    "button": "Ver Opções",
                    "sections": [
                        {
                            "title": "Segunda Via",
                            "rows": [
                                {
                                    "id": f"item_{i}",
                                    "title": item.get("title", "")[:24],  # Limite de 24 caracteres
                                    "description": item.get("description", "")[:72],  # Limite de 72 caracteres
                                }
                                for i, item in enumerate(list_items)
                            ]
                        }
                    ]
                }
            }
        }
    # Se houver botões, usa mensagem interativa
    elif buttons and len(buttons) > 0:
        # WhatsApp suporta até 3 botões
        button_items = buttons[:3]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"btn_{i}",
                                "title": btn["label"][:20]  # WhatsApp limita a 20 caracteres
                            }
                        }
                        for i, btn in enumerate(button_items)
                    ]
                }
            }
        }
    else:
        # Mensagem de texto simples
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": body},
        }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        logging.warning(f"📤 Enviando mensagem Cloud API → {to_number}: {body[:100]}...")
        logging.warning(f"Resposta Meta: {resp.status_code} - {resp.text}")
        
        # Verificar se houve erro na resposta
        if resp.status_code != 200:
            logging.error(f"❌ Erro ao enviar mensagem: Status {resp.status_code}")
            return False
        
        # Extrair message_id da resposta para rastrear status
        try:
            resp_data = resp.json()
            message_id = resp_data.get("messages", [{}])[0].get("id")
            if message_id:
                logging.info(f"🆔 Message ID: {message_id}")
                return message_id
            else:
                logging.warning(f"⚠️ message_id não encontrado na resposta")
                return None
        except Exception as e:
            logging.warning(f"⚠️ Erro ao extrair message_id: {e}")
            return None
    except Exception as e:
        logging.error(f"❌ Erro ao enviar mensagem via Cloud API: {e}")
        return False


def send_whatsapp_document(to_number: str, file_content: bytes, filename: str, caption: str = None):
    """
    Envia documento (PDF, etc.) via WhatsApp Cloud API.
    to_number: número sem 'whatsapp:', ex: 559193808761
    file_content: conteúdo do arquivo em bytes
    filename: nome do arquivo
    caption: legenda opcional do documento
    Retorna: message_id se sucesso, None se falha
    """
    import time
    
    if not (WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN):
        logging.error("❌ WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN não configurados.")
        return None

    # Primeiro, fazer upload do documento com retry para 429
    upload_url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/media"
    upload_headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    }
    
    files = {
        "file": (filename, file_content, "application/pdf"),
        "messaging_product": (None, "whatsapp")
    }
    
    max_retries = 5
    
    for tentativa in range(1, max_retries + 1):
        try:
            upload_resp = requests.post(upload_url, headers=upload_headers, files=files)
            upload_data = upload_resp.json()
            
            if upload_resp.status_code == 200:
                break
            elif upload_resp.status_code == 429:
                wait_time = 2 ** tentativa  # Backoff exponencial: 2, 4, 8, 16, 32 segundos
                logging.warning(f"⚠️ Erro 429 ao upload documento. Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
                continue
            else:
                logging.error(f"❌ Erro ao upload documento: {upload_resp.status_code} - {upload_data}")
                return None
        except Exception as e:
            logging.error(f"❌ Erro ao fazer upload: {e}")
            return None
    
    media_id = upload_data.get("id")
    logging.warning(f"✅ Documento uploadado: {media_id}")
    
    # Enviar documento usando media_id com retry para 429
    message_url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    message_headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename,
        }
    }
    
    if caption:
        payload["document"]["caption"] = caption
    
    for tentativa in range(1, max_retries + 1):
        try:
            message_resp = requests.post(message_url, headers=message_headers, json=payload)
            logging.warning(f"📤 Enviando documento → {to_number}: {filename}")
            logging.warning(f"Resposta Meta: {message_resp.status_code} - {message_resp.text}")
            
            if message_resp.status_code == 200:
                break
            elif message_resp.status_code == 429:
                wait_time = 2 ** tentativa  # Backoff exponencial: 2, 4, 8, 16, 32 segundos
                logging.warning(f"⚠️ Erro 429 ao enviar mensagem. Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
                continue
            else:
                logging.error(f"❌ Erro ao enviar documento: Status {message_resp.status_code}")
                return None
        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem: {e}")
            return None
    
    # Extrair message_id da resposta para rastrear status
    try:
        resp_data = message_resp.json()
        message_id = resp_data.get("messages", [{}])[0].get("id")
        if message_id:
            logging.info(f"🆔 Documento Message ID: {message_id}")
            return message_id
    except Exception as e:
        logging.warning(f"⚠️ Erro ao extrair message_id do documento: {e}")
    
    return None

@app.post("/webhook-whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Recebe mensagens e status do WhatsApp Cloud API (POST)
    """
    data = await request.json()
    print(f"📲 [WEBHOOK] Webhook WhatsApp recebido: {data}")
    logging.info(f"📲 Webhook WhatsApp recebido: {data}")

    try:
        entry_list = data.get("entry", [])
        if not entry_list:
            return {"status": "no_entry"}

        changes = entry_list[0].get("changes", [])
        if not changes:
            return {"status": "no_changes"}

        value = changes[0].get("value", {})
        
        # Verificar se é webhook de status (mensagens enviadas)
        statuses = value.get("statuses", [])
        if statuses:
            print(f"📊 [WEBHOOK] Processando {len(statuses)} status updates")
            # Processar status de mensagens enviadas (sent/delivered/read)
            for status in statuses:
                message_id = status.get("id")
                status_type = status.get("status")  # sent, delivered, read
                recipient_id = status.get("recipient_id")
                timestamp = status.get("timestamp")
                
                print(f"📊 [WEBHOOK] Status da mensagem {message_id}: {status_type} para {recipient_id}")
                logging.info(f"📊 Status da mensagem {message_id}: {status_type} para {recipient_id}")
                
                # Atualizar status no banco de dados
                try:
                    from supabase_client import atualizar_status_mensagem
                    resultado = atualizar_status_mensagem(message_id, status_type)
                    print(f"✅ [WEBHOOK] Status atualizado no banco: {resultado}")
                except Exception as e:
                    print(f"⚠️ [WEBHOOK] Erro ao atualizar status da mensagem: {e}")
                    logging.warning(f"⚠️ Erro ao atualizar status da mensagem: {e}")
            
            return {"status": "status_processed"}
        
        # Verificar se é webhook de mensagens recebidas
        messages = value.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        from_number = msg.get("from")             # ex: "559193808761"
        message_id = msg.get("id")               # ID único da mensagem para deduplicação
        
        # Deduplicação: verificar se já processamos esta mensagem
        if message_id and message_id in processed_messages:
            logging.warning(f"⚠️ Mensagem {message_id} já processada, ignorando")
            return {"status": "duplicate"}
        
        # Marcar mensagem como processada
        if message_id:
            processed_messages.add(message_id)
            # Manter apenas os últimos 1000 IDs para evitar crescimento infinito
            if len(processed_messages) > 1000:
                processed_messages.clear()
        
        # Inicializar text com valor padrão (proteção contra UnboundLocalError)
        text = msg.get("text", {}).get("body", "")
        
        # Salvar log de mensagem recebida no Supabase
        try:
            from supabase_client import salvar_log_mensagem
            salvar_log_mensagem({
                "usuario_id": f"whatsapp:{from_number}",
                "telefone": from_number,
                "mensagem_recebida": text,
                "mensagem_enviada": None,
                "tipo": "recebida",
                "status": "sucesso"
            })
        except Exception as e:
            logging.warning(f"⚠️ Erro ao salvar log de mensagem recebida: {e}")
        
        # Verifica se é uma resposta de botão interativo
        interactive = msg.get("interactive")
        if interactive and interactive.get("type") == "button_reply":
            button_reply = interactive.get("button_reply", {})
            button_id = button_reply.get("id", "")
            button_title = button_reply.get("title", "")
            text = button_title  # Usa o título do botão como texto
            logging.info(f"🔘 Botão clicado: {button_id} - {button_title}")
        elif interactive and interactive.get("type") == "list_reply":
            list_reply = interactive.get("list_reply", {})
            item_id = list_reply.get("id", "")
            item_title = list_reply.get("title", "")
            logging.info(f"📋 List reply recebido: item_id={item_id}, item_title={item_title}")
            
            # Se for um item de lista, extrai o comando do ID
            if item_id.startswith("item_"):
                # Recupera o contexto para saber qual boleto foi selecionado
                user_id = f"whatsapp:{from_number}"
                ctx = usuarios_contexto.get(user_id, {})
                logging.info(f"🔍 Contexto do usuário {user_id}: {ctx}")
                
                boletos = ctx.get("boletos_disponiveis", [])
                logging.info(f"📋 Boletos disponíveis no contexto: {len(boletos)}")
                
                item_index = int(item_id.replace("item_", ""))
                logging.info(f"🔢 Índice do item: {item_index}")
                
                if item_index < len(boletos):
                    boleto = boletos[item_index]
                    texto = f"boleto {boleto['titulo_id']} {boleto['parcela_id']}"
                    text = texto  # Atualiza text com o comando do boleto
                    logging.info(f"✅ Item da lista selecionado: {item_title} -> {texto}")
                else:
                    logging.warning(f"⚠️ Índice {item_index} fora do range (total: {len(boletos)})")
                    text = item_title if item_title else ""
            else:
                logging.warning(f"⚠️ item_id não começa com 'item_': {item_id}")
                text = item_title if item_title else ""
        
        # Proteção final: garantir que text sempre tem valor
        if not text:
            text = ""
            logging.warning("⚠️ text está vazio após processamento, usando string vazia")

        user_id = f"whatsapp:{from_number}"
        
        # Processar a mensagem usando o endpoint de mensagem existente
        from pydantic import BaseModel
        class MessageWrapper(BaseModel):
            user: str
            text: str
        
        msg_wrapper = MessageWrapper(user=user_id, text=text)
        resposta_construia = await mensagem(msg_wrapper)
        texto_resposta = resposta_construia.get("text", "Constru.IA: não consegui gerar resposta.")
        
        # Gerar botões e lista de itens se necessário
        botoes = None
        list_items = None
        
        # Verifica se a resposta contém botões
        if isinstance(texto_resposta, dict):
            botoes = texto_resposta.get("buttons")
            list_items = texto_resposta.get("list_items")
            texto_resposta = texto_resposta.get("text", texto_resposta)
        
        # Envia resposta via Cloud API com botões ou lista
        logging.info(f"📤 Enviando resposta para {from_number}...")
        message_id = send_whatsapp_cloud_message(from_number, texto_resposta, botoes, list_items)
        logging.info(f"✅ Resposta enviada com sucesso")
        logging.warning(f"🆔 message_id retornado pelo send_whatsapp_cloud_message: {message_id}")
        
        # Salvar log de mensagem enviada no Supabase
        try:
            from supabase_client import salvar_log_mensagem
            dados_log = {
                "usuario_id": user_id,
                "telefone": from_number,
                "mensagem_recebida": text,
                "mensagem_enviada": texto_resposta,
                "tipo": "enviada",
                "status": "sent"
            }
            # Salvar whatsapp_message_id se disponível
            if message_id:
                dados_log["whatsapp_message_id"] = message_id
                logging.warning(f"💾 Salvando message_id no log: {message_id}")
            else:
                logging.warning(f"⚠️ message_id é None, não será salvo")
            
            resultado = salvar_log_mensagem(dados_log)
            logging.warning(f"💾 Log de mensagem salvo: {resultado}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")
        
        return {"status": "success"}
    
    except Exception as e:
        logging.error(f"❌ Erro ao processar webhook WhatsApp: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/webhook-cobranca")
async def webhook_cobranca(request: Request):
    """
    Recebe mensagens e status do WhatsApp Cloud API específico para cobrança (POST)
    """
    data = await request.json()
    print(f"📲 [COBRANÇA] Webhook Cobrança recebido: {data}")
    logging.info(f"📲 Webhook Cobrança recebido: {data}")

    try:
        entry_list = data.get("entry", [])
        if not entry_list:
            return {"status": "no_entry"}

        changes = entry_list[0].get("changes", [])
        if not changes:
            return {"status": "no_changes"}

        value = changes[0].get("value", {})
        
        # Verificar se é webhook de status (mensagens enviadas)
        statuses = value.get("statuses", [])
        if statuses:
            print(f"📊 [COBRANÇA] Processando {len(statuses)} status updates")
            # Processar status de mensagens enviadas (sent/delivered/read)
            for status in statuses:
                message_id = status.get("id")
                status_type = status.get("status")  # sent, delivered, read
                recipient_id = status.get("recipient_id")
                timestamp = status.get("timestamp")
                
                print(f"📊 [COBRANÇA] Status da mensagem {message_id}: {status_type} para {recipient_id}")
                logging.info(f"📊 [Cobrança] Status da mensagem {message_id}: {status_type} para {recipient_id}")
                
                # Atualizar status no banco de dados
                try:
                    from supabase_client import atualizar_status_mensagem
                    resultado = atualizar_status_mensagem(message_id, status_type)
                    print(f"✅ [COBRANÇA] Status atualizado no banco: {resultado}")
                except Exception as e:
                    print(f"⚠️ [COBRANÇA] Erro ao atualizar status da mensagem: {e}")
                    logging.warning(f"⚠️ Erro ao atualizar status da mensagem: {e}")
            
            return {"status": "status_processed"}
        
        # Verificar se é webhook de mensagens recebidas
        messages = value.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        from_number = msg.get("from")             # ex: "559193808761"
        message_id = msg.get("id")               # ID único da mensagem para deduplicação
        
        # Deduplicação: verificar se já processamos esta mensagem
        if message_id and message_id in processed_messages:
            logging.warning(f"⚠️ [Cobrança] Mensagem {message_id} já processada, ignorando")
            return {"status": "duplicate"}
        
        # Marcar mensagem como processada
        if message_id:
            processed_messages.add(message_id)
            # Manter apenas os últimos 1000 IDs para evitar crescimento infinito
            if len(processed_messages) > 1000:
                processed_messages.clear()
        
        # Inicializar text com valor padrão (proteção contra UnboundLocalError)
        text = msg.get("text", {}).get("body", "")
        
        # Salvar log de mensagem recebida no Supabase
        try:
            from supabase_client import salvar_log_mensagem
            salvar_log_mensagem({
                "usuario_id": f"whatsapp:{from_number}",
                "telefone": from_number,
                "mensagem_recebida": text,
                "mensagem_enviada": None,
                "tipo": "recebida",
                "status": "sucesso"
            })
        except Exception as e:
            logging.warning(f"⚠️ Erro ao salvar log de mensagem recebida: {e}")
        
        # Responder com mensagem de atendimento (este número é apenas para envio automático)
        texto_resposta = "Olá, esse número é usado apenas para envio automático. Caso tenha alguma dúvida, fale com um de nossos atendentes pelo número (91) 9999-9999"
        
        # Envia resposta via Cloud API
        logging.info(f"📤 Enviando resposta de atendimento para {from_number}...")
        message_id = send_whatsapp_cloud_message(from_number, texto_resposta, None, None)
        logging.info(f"✅ Resposta enviada com sucesso")
        logging.warning(f"🆔 message_id retornado pelo send_whatsapp_cloud_message: {message_id}")
        
        # Salvar log de mensagem enviada no Supabase
        try:
            from supabase_client import salvar_log_mensagem
            dados_log = {
                "usuario_id": f"whatsapp:{from_number}",
                "telefone": from_number,
                "mensagem_recebida": text,
                "mensagem_enviada": texto_resposta,
                "tipo": "enviada",
                "status": "sucesso"
            }
            # Salvar whatsapp_message_id se disponível
            if message_id:
                dados_log["whatsapp_message_id"] = message_id
                logging.warning(f"💾 Salvando message_id no log: {message_id}")
            else:
                logging.warning(f"⚠️ message_id é None, não será salvo")
            
            resultado = salvar_log_mensagem(dados_log)
            logging.warning(f"💾 Log de mensagem salvo: {resultado}")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao salvar log de mensagem enviada: {e}")

    except Exception as e:
        logging.exception("❌ Erro ao processar webhook WhatsApp:")
        return {"status": "error", "detail": str(e)}

    return {"status": "ok"}


# ============================================================
# 📄 POLÍTICA DE PRIVACIDADE
# ============================================================
@app.get("/privacy-policy")
async def privacy_policy():
    """
    Endpoint de Política de Privacidade para publicação do app no Meta
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Política de Privacidade - Constru.IA Connect</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1 {
                color: #333;
            }
            h2 {
                color: #555;
                margin-top: 30px;
            }
        </style>
    </head>
    <body>
        <h1>Política de Privacidade - Constru.IA Connect</h1>
        <p><strong>Última atualização:</strong> 10 de Julho de 2026</p>
        
        <h2>1. Informações que Coletamos</h2>
        <p>O Constru.IA Connect coleta as seguintes informações:</p>
        <ul>
            <li>Número de telefone do WhatsApp (para envio de mensagens)</li>
            <li>CPF ou CNPJ (para busca de boletos e cobranças)</li>
            <li>Dados de boletos e cobranças (obtidos da API Sienge)</li>
        </ul>
        
        <h2>2. Como Usamos as Informações</h2>
        <p>Usamos as informações coletadas para:</p>
        <ul>
            <li>Enviar lembretes de cobrança via WhatsApp</li>
            <li>Buscar e gerar segundas vias de boletos</li>
            <li>Gerenciar contas a receber</li>
        </ul>
        
        <h2>3. Compartilhamento de Informações</h2>
        <p>Não compartilhamos suas informações pessoais com terceiros, exceto quando necessário para:</p>
        <ul>
            <li>Integração com a API Sienge (para dados de cobranças)</li>
            <li>Integração com a API WhatsApp Cloud (para envio de mensagens)</li>
        </ul>
        
        <h2>4. Segurança dos Dados</h2>
        <p>Implementamos medidas de segurança para proteger suas informações, incluindo:</p>
        <ul>
            <li>Criptografia de dados em trânsito</li>
            <li>Controle de acesso restrito</li>
            <li>Monitoramento de segurança</li>
        </ul>
        
        <h2>5. Seus Direitos</h2>
        <p>Você tem o direito de:</p>
        <ul>
            <li>Acessar suas informações pessoais</li>
            <li>Solicitar a exclusão de seus dados</li>
            <li>Corrigir informações incorretas</li>
        </ul>
        
        <h2>6. Contato</h2>
        <p>Para questões sobre esta política de privacidade, entre em contato:</p>
        <p>Email: projetfinanc9@gmail.com</p>
        
        <h2>7. Alterações a esta Política</h2>
        <p>Reservamos o direito de atualizar esta política de privacidade. Notificaremos os usuários sobre alterações significativas.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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
    try:
        from supabase_client import buscar_configuracao_sienge
        config = buscar_configuracao_sienge()
        
        if config:
            # Não retornamos a senha por segurança
            return {
                "subdomain": config.get("subdomain"),
                "username": config.get("username"),
                "password": ""  # Não expor a senha
            }
        else:
            # Retorna configurações padrão se não existir
            from sienge.sienge_config import subdominio, usuario
            return {
                "subdomain": subdominio,
                "username": usuario,
                "password": ""  # Não expor a senha
            }
    except Exception as e:
        return {"error": str(e)}

@app.post("/config")
def save_config(config: SiengeConfig):
    """Salva novas configurações do Sienge no Supabase"""
    try:
        from supabase_client import salvar_configuracao_sienge
        
        # Salva no Supabase
        resultado = salvar_configuracao_sienge({
            "subdomain": config.subdomain,
            "username": config.username,
            "password": config.password
        })
        
        if not resultado:
            return {"success": False, "error": "Erro ao salvar configurações no Supabase"}
        
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
        
        logging.info(f"✅ Configurações atualizadas e persistidas no Supabase: {config.subdomain}")
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

@app.post("/testar-cobranca")
async def testar_cobranca():
    """Endpoint para testar manualmente o job de cobrança"""
    try:
        logging.warning("🧪 Iniciando teste manual de cobrança...")
        await executar_cobranca_agendada()
        return {"success": True, "message": "Teste de cobrança executado"}
    except Exception as e:
        logging.error(f"❌ Erro no teste de cobrança: {e}")
        return {"success": False, "error": str(e)}

@app.post("/limpar-cache")
async def limpar_cache():
    """Endpoint para limpar todo o cache"""
    try:
        from pathlib import Path
        cache_dir = Path(__file__).parent / "cache"
        if cache_dir.exists():
            # Remover todos os arquivos de cache
            for file in cache_dir.glob("*.json"):
                file.unlink()
                logging.warning(f"🗑️ Cache removido: {file.name}")
            return {"success": True, "message": "Cache limpo completamente"}
        else:
            return {"success": False, "message": "Diretório de cache não existe"}
    except Exception as e:
        logging.error(f"❌ Erro ao limpar cache: {e}")
        return {"success": False, "error": str(e)}

@app.get("/cobranca-relatorio-pdf")
async def gerar_relatorio_pdf(
    data_inicio: str = None,
    data_fim: str = None,
    cliente: str = None
):
    """Endpoint para gerar relatório PDF do histórico de cobranças"""
    try:
        from supabase_client import buscar_historico_cobrancas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from io import BytesIO
        
        # Buscar histórico com filtros
        historico = buscar_historico_cobrancas()
        
        # Aplicar filtros
        if data_inicio or data_fim or cliente:
            historico_filtrado = []
            for item in historico:
                if data_inicio:
                    item_data = item.get("created_at", "")
                    if item_data < data_inicio:
                        continue
                if data_fim:
                    item_data = item.get("created_at", "")
                    if item_data > data_fim:
                        continue
                if cliente:
                    item_cliente = item.get("cliente_nome", "").lower()
                    if cliente.lower() not in item_cliente:
                        continue
                historico_filtrado.append(item)
            historico = historico_filtrado
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph("Relatório de Cobranças", styles["Title"])
        elements.append(title)
        
        # Subtítulo com período
        periodo_texto = f"Período: {data_inicio or 'Início'} a {data_fim or 'Fim'}"
        if cliente:
            periodo_texto += f" | Cliente: {cliente}"
        subtitle = Paragraph(periodo_texto, styles["Normal"])
        elements.append(subtitle)
        elements.append(Paragraph("<br/><br/>", styles["Normal"]))
        
        # Tabela de dados
        data = [
            ["Data", "Cliente", "Telefone", "Status", "Valor", "Vencimento"]
        ]
        
        for item in historico:
            data.append([
                item.get("created_at", "")[:10],
                item.get("cliente_nome", ""),
                item.get("cliente_telefone", ""),
                item.get("status", ""),
                str(item.get("valor", 0)),
                item.get("vencimento", "")
            ])
        
        table = Table(data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 0.8*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        from fastapi.responses import Response
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=relatorio_cobrancas.pdf"}
        )
    except Exception as e:
        logging.error(f"❌ Erro ao gerar relatório PDF: {e}")
        return {"error": str(e)}

@app.post("/cobranca-config")
def save_cobranca_config(config: ConfiguracaoCobranca):
    """Salva novas configurações de cobrança automática no Supabase"""
    try:
        logging.warning(f"📝 Recebendo configuração: ativo={config.ativo}, horario={config.horario_execucao}, lembretes={len(config.lembretes)}")
        
        config_dict = {
            "ativo": config.ativo,
            "horario_execucao": config.horario_execucao,
            "lembretes": [
                {
                    "dias_antes": l.dias_antes,
                    "mensagem": l.mensagem,
                    "enviar_segunda_via": l.enviar_segunda_via,
                    "envio_pdf": l.envio_pdf
                }
                for l in config.lembretes
            ]
        }
        
        logging.warning(f"📦 Config dict preparado: {config_dict}")
        
        # Salvar no Supabase
        try:
            logging.warning("🔄 Tentando importar supabase_client...")
            from supabase_client import salvar_configuracao_cobranca
            logging.warning("✅ Importação bem-sucedida, chamando salvar_configuracao_cobranca...")
            resultado = salvar_configuracao_cobranca(config_dict)
            logging.warning(f"📊 Resultado do Supabase: {resultado}")
            if not resultado:
                logging.warning("⚠️ Falha ao salvar no Supabase, tentando salvar localmente")
                sucesso = salvar_configuracao_cobranca(config_dict)
            else:
                sucesso = True
                logging.info("✅ Configuração salva no Supabase")
        except Exception as e:
            logging.warning(f"⚠️ Erro ao salvar no Supabase: {e}, tentando salvar localmente")
            sucesso = salvar_configuracao_cobranca(config_dict)
        
        if not sucesso:
            return {"success": False, "error": "Erro ao salvar configurações"}
        
        # Recarregar módulo de cobrança
        import importlib
        from sienge import sienge_cobranca
        importlib.reload(sienge_cobranca)
        
        # Atualizar agendamento se estiver ativo
        if config.ativo:
            atualizar_agendamento(config.horario_execucao)
        else:
            remover_agendamento()
        
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
