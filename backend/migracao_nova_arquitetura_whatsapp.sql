-- ============================================
-- NOVA ARQUITETURA: Configurações WhatsApp Centralizadas
-- ============================================

-- 1. Criar tabela de configurações WhatsApp
CREATE TABLE IF NOT EXISTS configuracoes_whatsapp (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    whatsapp_phone_number_id TEXT NOT NULL,
    whatsapp_token TEXT NOT NULL,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Adicionar comentários
COMMENT ON TABLE configuracoes_whatsapp IS 'Configurações centralizadas de números WhatsApp Business API';
COMMENT ON COLUMN configuracoes_whatsapp.nome IS 'Nome descritivo da configuração (ex: Residencial Alfa, Comercial Beta)';
COMMENT ON COLUMN configuracoes_whatsapp.whatsapp_phone_number_id IS 'WhatsApp Phone Number ID do Meta';
COMMENT ON COLUMN configuracoes_whatsapp.whatsapp_token IS 'WhatsApp Token do Meta (criptografado)';
COMMENT ON COLUMN configuracoes_whatsapp.ativo IS 'Status da configuração (ativa/inativa)';

-- 2. Adicionar campo whatsapp_config_id em empreendimentos_cobranca
ALTER TABLE empreendimentos_cobranca 
ADD COLUMN IF NOT EXISTS whatsapp_config_id INTEGER REFERENCES configuracoes_whatsapp(id);

COMMENT ON COLUMN empreendimentos_cobranca.whatsapp_config_id IS 'ID da configuração WhatsApp vinculada (FK para configuracoes_whatsapp)';

-- 3. Remover campos antigos (opcional - depois de migrar dados)
-- Descomente depois de migrar os dados
-- ALTER TABLE empreendimentos_cobranca DROP COLUMN IF EXISTS whatsapp_phone_number_id;
-- ALTER TABLE empreendimentos_cobranca DROP COLUMN IF EXISTS whatsapp_token;

-- 4. Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_configuracoes_whatsapp_ativo ON configuracoes_whatsapp(ativo);
CREATE INDEX IF NOT EXISTS idx_empreendimentos_whatsapp_config ON empreendimentos_cobranca(whatsapp_config_id);
