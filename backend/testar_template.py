import os
from whatsapp_templates import send_whatsapp_template_message

# Configurar as variáveis de ambiente ou coloque direto aqui
# os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "seu_phone_number_id"
# os.environ["WHATSAPP_TOKEN"] = "seu_token"

# Dados de teste
numero_teste = "5591999999999"  # Coloque seu número de teste
boleto_teste = {
    "cliente_nome": "João Silva",
    "valor": 850.00,
    "dias_antes": 3,
    "vencimento": "2026-08-15",
    "pdf_url": "https://url-do-pdf",
    "titulo_id": 123,
    "parcela_id": 456
}

print("🧪 Testando envio de template WhatsApp...")
print(f"📱 Para: {numero_teste}")
print(f"👤 Cliente: {boleto_teste['cliente_nome']}")
print(f"💰 Valor: R$ {boleto_teste['valor']}")
print()

# Enviar template
message_id = send_whatsapp_template_message(numero_teste, boleto_teste, template_name="auto_pay_reminder_3")

if message_id:
    print(f"✅ Template enviado com sucesso!")
    print(f"🆔 Message ID: {message_id}")
else:
    print("❌ Erro ao enviar template")
