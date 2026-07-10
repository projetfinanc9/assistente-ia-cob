-- ============================================================
-- MIGRATIONS SUPABASE PARA CONSTRU.IA CONNECT
-- ============================================================

-- Habilitar extensão UUID se não estiver habilitada
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABELA: configuracoes_cobranca
-- Armazena configurações do sistema de cobrança automática
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracoes_cobranca (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ativo BOOLEAN NOT NULL DEFAULT false,
    horario_execucao VARCHAR(5) NOT NULL DEFAULT '09:00',
    lembretes JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- TABELA: historico_cobrancas
-- Armazena histórico de cobranças enviadas
-- ============================================================
CREATE TABLE IF NOT EXISTS historico_cobrancas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id INTEGER,
    cliente_nome VARCHAR(255),
    cliente_telefone VARCHAR(20),
    titulo_id INTEGER,
    parcela_id INTEGER,
    vencimento DATE,
    valor DECIMAL(10, 2),
    dias_antes INTEGER,
    mensagem_template TEXT,
    mensagem_enviada TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pendente', -- pendente, enviado, erro
    tipo_envio VARCHAR(50) DEFAULT 'texto', -- texto, pdf
    enviado_em TIMESTAMP WITH TIME ZONE,
    erro_mensagem TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- TABELA: logs_mensagens
-- Armazena logs de mensagens enviadas/recebidas via WhatsApp
-- ============================================================
CREATE TABLE IF NOT EXISTS logs_mensagens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id VARCHAR(255),
    telefone VARCHAR(20),
    mensagem_recebida TEXT,
    mensagem_enviada TEXT,
    tipo VARCHAR(50) NOT NULL, -- recebida, enviada
    status VARCHAR(50) NOT NULL DEFAULT 'sucesso', -- sucesso, erro
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- TABELA: clientes_cache
-- Cache de clientes da API Sienge (opcional)
-- ============================================================
CREATE TABLE IF NOT EXISTS clientes_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id INTEGER UNIQUE NOT NULL,
    nome VARCHAR(255),
    documento VARCHAR(20),
    telefones JSONB DEFAULT '[]'::jsonb,
    dados_completos JSONB,
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_historico_cobrancas_cliente_id ON historico_cobrancas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_historico_cobrancas_vencimento ON historico_cobrancas(vencimento);
CREATE INDEX IF NOT EXISTS idx_historico_cobrancas_status ON historico_cobrancas(status);
CREATE INDEX IF NOT EXISTS idx_historico_cobrancas_enviado_em ON historico_cobrancas(enviado_em);
CREATE INDEX IF NOT EXISTS idx_logs_mensagens_usuario_id ON logs_mensagens(usuario_id);
CREATE INDEX IF NOT EXISTS idx_logs_mensagens_created_at ON logs_mensagens(created_at);
CREATE INDEX IF NOT EXISTS idx_clientes_cache_cliente_id ON clientes_cache(cliente_id);

-- ============================================================
-- TRIGGER: atualizar updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_configuracoes_cobranca_updated_at
    BEFORE UPDATE ON configuracoes_cobranca
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_updated_at();

CREATE TRIGGER trigger_historico_cobrancas_updated_at
    BEFORE UPDATE ON historico_cobrancas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_updated_at();

-- ============================================================
-- DADOS INICIAIS
-- ============================================================
INSERT INTO configuracoes_cobranca (ativo, horario_execucao, lembretes)
VALUES (
    true,
    '09:00',
    '[
        {
            "dias_antes": 10,
            "mensagem": "Olá {cliente}, seu boleto vence em {dias} dias. Valor: R$ {valor}",
            "enviar_segunda_via": true
        }
    ]'::jsonb
) ON CONFLICT DO NOTHING;

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================
ALTER TABLE configuracoes_cobranca ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_cobrancas ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs_mensagens ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes_cache ENABLE ROW LEVEL SECURITY;

-- Políticas RLS (ajuste conforme necessário)
CREATE POLICY "Permitir leitura pública" ON configuracoes_cobranca FOR SELECT USING (true);
CREATE POLICY "Permitir inserção pública" ON configuracoes_cobranca FOR INSERT WITH CHECK (true);
CREATE POLICY "Permitir atualização pública" ON configuracoes_cobranca FOR UPDATE USING (true);

CREATE POLICY "Permitir leitura pública" ON historico_cobrancas FOR SELECT USING (true);
CREATE POLICY "Permitir inserção pública" ON historico_cobrancas FOR INSERT WITH CHECK (true);
CREATE POLICY "Permitir atualização pública" ON historico_cobrancas FOR UPDATE USING (true);

CREATE POLICY "Permitir leitura pública" ON logs_mensagens FOR SELECT USING (true);
CREATE POLICY "Permitir inserção pública" ON logs_mensagens FOR INSERT WITH CHECK (true);

CREATE POLICY "Permitir leitura pública" ON clientes_cache FOR SELECT USING (true);
CREATE POLICY "Permitir inserção pública" ON clientes_cache FOR INSERT WITH CHECK (true);
CREATE POLICY "Permitir atualização pública" ON clientes_cache FOR UPDATE USING (true);
