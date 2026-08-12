import os
import requests
import logging
import json
from typing import Optional
import io

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")

logging.warning("Modulo whatsapp_templates.py carregado")

def formatar_dias_texto(dias: int) -> str:
    """Formata o número de dias em texto amigável"""
    if dias < 0:
        dias_abs = abs(dias)
        if dias_abs == 1:
            return "falta 1 dia"
        else:
            return f"falta {dias_abs} dias"
    elif dias > 0:
        if dias == 1:
            return "venceu há 1 dia"
        else:
            return f"venceu há {dias} dias"
    else:
        return "vence hoje"

def formatar_dias_numero(dias: int) -> str:
    """Retorna apenas o número absoluto de dias (para templates que já têm o texto)"""
    return str(abs(dias))

def formatar_valor(valor) -> str:
    """Formata o valor monetário"""
    try:
        valor_float = float(valor)
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {valor}"

def formatar_vencimento(vencimento_str: str) -> str:
    """Formata a data de vencimento para DD/MM/YYYY"""
    try:
        from datetime import datetime
        # Remover hora se presente
        if "T" in vencimento_str:
            vencimento_str = vencimento_str.split("T")[0]
        
        data = datetime.strptime(vencimento_str, "%Y-%m-%d")
        return data.strftime("%d/%m/%Y")
    except:
        return vencimento_str

def fazer_upload_pdf(pdf_content: bytes, filename: str) -> Optional[str]:
    """
    Faz upload do PDF para a API do WhatsApp e retorna o media_id
    
    Args:
        pdf_content: Conteúdo binário do PDF
        filename: Nome do arquivo
    
    Returns:
        media_id se sucesso, None se falhar
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        logging.error("WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN nao configurados")
        return None
    
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    try:
        files = {
            "file": (filename, io.BytesIO(pdf_content), "application/pdf"),
            "type": (None, "application/pdf"),
            "messaging_product": (None, "whatsapp")
        }
        
        logging.warning(f"Fazendo upload do PDF {filename}...")
        response = requests.post(url, headers=headers, files=files, timeout=60)
        
        if response.status_code != 200:
            logging.error(f"Erro ao fazer upload do PDF: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        media_id = data.get("id")
        
        if media_id:
            logging.warning(f"Upload do PDF realizado com sucesso. Media ID: {media_id}")
            return media_id
        else:
            logging.error("Media ID nao encontrado na resposta do upload")
            return None
            
    except Exception as e:
        logging.error(f"Erro ao fazer upload do PDF: {e}")
        return None

def send_whatsapp_template_message(numero: str, boleto: dict, template_name: str = "lembrete_de_vencimento") -> Optional[str]:
    """
    Envia mensagem usando template aprovado da Meta
    
    Args:
        numero: Numero de telefone (sem 'whatsapp:', apenas digitos)
        boleto: Dicionario com dados do boleto
        template_name: Nome do template a usar (default: auto_pay_reminder_3)
    
    Returns:
        message_id se sucesso, None se falhar
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        logging.error("WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_TOKEN nao configurados")
        return None
    
    # Normalizar numero
    numero = numero.replace("whatsapp:", "").replace("+", "").replace(" ", "").replace("-", "")
    if not numero.startswith("55"):
        numero = "55" + numero
    
    # Remover caracteres não numéricos
    numero = ''.join(filter(str.isdigit, numero))
    
    # Garantir formato correto (55 + DDD + numero)
    if len(numero) == 12 or len(numero) == 13:
        if not numero.startswith("55"):
            numero = "55" + numero
    
    logging.warning(f"Numero normalizado: {numero}")
    
    # Extrair dados do boleto
    cliente = boleto.get("cliente_nome", "Cliente")
    valor = boleto.get("valor", 0)
    dias = boleto.get("dias_antes", 0)
    vencimento = boleto.get("vencimento", "")
    pdf_url = boleto.get("pdf_url")
    titulo_id = boleto.get("titulo_id")
    parcela_id = boleto.get("parcela_id")
    
    # Formatar parametros
    cliente_texto = cliente
    valor_texto = formatar_valor(valor)
    # Para template lembrete_de_vencimento, usar apenas o numero (template ja tem o texto)
    if template_name == "lembrete_de_vencimento":
        dias_texto = formatar_dias_numero(dias)
    else:
        dias_texto = formatar_dias_texto(dias)
    vencimento_texto = formatar_vencimento(vencimento)
    
    logging.warning(f"Enviando template {template_name} para {numero}")
    logging.warning(f"Parametros: cliente={cliente_texto}, valor={valor_texto}, dias={dias_texto}, vencimento={vencimento_texto}")
    
    # Construir payload do template
    components = []
    
    # Header com documento (PDF) - sempre fazer upload
    media_id = None
    if pdf_url and titulo_id and parcela_id:
        from sienge.sienge_cobranca import baixar_pdf_boleto
        pdf_content = baixar_pdf_boleto(titulo_id, parcela_id, pdf_url)
        
        if pdf_content:
            media_id = fazer_upload_pdf(pdf_content, f"boleto_{titulo_id}_{parcela_id}.pdf")
            
            if media_id:
                header_component = {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "document",
                            "document": {
                                "id": media_id,
                                "filename": f"boleto_{titulo_id}_{parcela_id}.pdf"
                            }
                        }
                    ]
                }
                components.append(header_component)
            else:
                logging.warning("Nao foi possivel fazer upload do PDF, enviando sem header")
        else:
            logging.warning("Nao foi possivel baixar o PDF, enviando sem header")
    else:
        logging.warning("PDF URL ou IDs nao disponiveis, enviando sem header")
    
    # Body com os 4 parametros (sempre usar 4 para auto_pay_reminder_3)
    body_component = {
        "type": "body",
        "parameters": [
            {"type": "text", "text": cliente_texto},
            {"type": "text", "text": valor_texto},
            {"type": "text", "text": dias_texto},
            {"type": "text", "text": vencimento_texto}
        ]
    }
    components.append(body_component)
    
    # Payload completo
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "pt_BR"},
            "components": components
        }
    }
    
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        logging.warning(f"Enviando template para {numero}...")
        logging.warning(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logging.warning(f"Status: {response.status_code}")
        logging.warning(f"Response: {response.text}")
        
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "")
            error_type = error_data.get("error", {}).get("type", "")
            error_code = error_data.get("error", {}).get("code", "")
            
            logging.error(f"Erro ao enviar template: {error_message}")
            logging.error(f"Tipo: {error_type}, Codigo: {error_code}")
            return None
        
        data = response.json()
        message_id = data.get("messages", [{}])[0].get("id")
        
        if message_id:
            logging.warning(f"Template enviado com sucesso. Message ID: {message_id}")
            return message_id
        else:
            logging.error("Message ID nao encontrado na resposta")
            return None
            
    except Exception as e:
        logging.error(f"Erro ao enviar template: {e}")
        import traceback
        traceback.print_exc()
        return None
