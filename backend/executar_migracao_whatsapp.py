"""
Instrucoes para adicionar campos WhatsApp na tabela empreendimentos_cobranca
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")

print("=" * 60)
print("MIGRACAO: Adicionar campos WhatsApp aos empreendimentos")
print("=" * 60)
print(f"\n1. Acesse o SQL Editor do Supabase:")
print(f"   {SUPABASE_URL}")
print(f"\n2. Cole e execute o seguinte SQL:")
print("\n-- Adicionar campo whatsapp_phone_number_id")
print("ALTER TABLE empreendimentos_cobranca ADD COLUMN IF NOT EXISTS whatsapp_phone_number_id TEXT;")
print("\n-- Adicionar campo whatsapp_token")
print("ALTER TABLE empreendimentos_cobranca ADD COLUMN IF NOT EXISTS whatsapp_token TEXT;")
print("\n3. Apos executar, clique em 'Run'")
print("\nCampos adicionados com sucesso!")
print("=" * 60)
