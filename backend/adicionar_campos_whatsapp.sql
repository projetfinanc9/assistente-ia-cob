-- Adicionar campos de WhatsApp na tabela empreendimentos_cobranca
-- Para executar no SQL Editor do Supabase

-- Adicionar campo whatsapp_phone_number_id
ALTER TABLE empreendimentos_cobranca 
ADD COLUMN IF NOT EXISTS whatsapp_phone_number_id TEXT;

-- Adicionar campo whatsapp_token
ALTER TABLE empreendimentos_cobranca 
ADD COLUMN IF NOT EXISTS whatsapp_token TEXT;

-- Adicionar comentário aos campos
COMMENT ON COLUMN empreendimentos_cobranca.whatsapp_phone_number_id IS 'WhatsApp Phone Number ID do Meta para este empreendimento';
COMMENT ON COLUMN empreendimentos_cobranca.whatsapp_token IS 'WhatsApp Token do Meta para este empreendimento (opcional, usa o global se não configurado)';
