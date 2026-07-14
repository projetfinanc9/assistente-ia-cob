# Documentação Técnica - Constru.IA Cobranças

## 📋 Visão Geral

O Constru.IA Cobranças é um sistema automatizado de cobrança via WhatsApp que integra com o Sienge para envio de boletos e acompanhamento de status de entrega e leitura das mensagens.

## 🏗️ Arquitetura do Sistema

### Frontend
- **Plataforma**: Vercel
- **URL**: https://assistente-ia-cob.vercel.app
- **Tecnologia**: React + TypeScript
- **Responsável por**: Interface administrativa, configuração de cobranças, visualização de logs e histórico

### Backend
- **Plataforma**: Render
- **URL**: https://assistente-ia-cob.onrender.com
- **Tecnologia**: Python + FastAPI + Uvicorn
- **Responsável por**: 
  - API REST para comunicação com frontend
  - Integração com WhatsApp Cloud API
  - Integração com Sienge API
  - Processamento de webhooks
  - Agendamento automático de cobranças

### Controle de Versão
- **Plataforma**: GitHub
- **Repositório**: https://github.com/projetfinanc9/assistente-ia-cob
- **Branch Principal**: main
- **Responsável por**: Versionamento do código, CI/CD automático

### Banco de Dados
- **Plataforma**: Supabase
- **Responsável por**: 
  - Armazenamento de configurações de cobrança
  - Histórico de cobranças enviadas
  - Logs de mensagens do WhatsApp
  - Configurações do Sienge

## 🔌 Integrações com APIs Externas

### 1. Sienge API

O sistema utiliza as seguintes APIs do Sienge:

#### Bulk Data API
- **Endpoint**: `https://cctcontrol.sienge.com.br/sienge/bulk-data`
- **Função**: Busca em lote de parcelas e clientes
- **Uso**: Otimização de requisições para reduzir carga na API do Sienge
- **Cache**: Implementação de cache local para evitar requisições duplicadas

#### Visualizar Relatório API
- **Endpoint**: `https://cctcontrol.sienge.com.br/sienge/visualizar-relatorio`
- **Função**: Geração de PDF de boletos
- **Parâmetros**: 
  - `arquivo`: ID do relatório
  - `formato`: Tipo de saída (PDF)
- **Uso**: Download de boletos para envio via WhatsApp

#### Lista de Clientes API
- **Endpoint**: `https://cctcontrol.sienge.com.br/sienge/lista-clientes`
- **Função**: Busca de informações de clientes (telefone, nome, etc.)
- **Uso**: Obtenção de contatos para envio de cobranças

#### Consulta de Parcelas API
- **Endpoint**: `https://cctcontrol.sienge.com.br/sienge/consulta-parcelas`
- **Função**: Busca detalhada de parcelas específicas
- **Uso**: Verificação de status e detalhes de boletos

### 2. Meta/WhatsApp Cloud API

O sistema utiliza as seguintes APIs da Meta:

#### WhatsApp Cloud API - Envio de Mensagens
- **Endpoint**: `https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages`
- **Função**: Envio de mensagens de texto, botões interativos e listas
- **Uso**: Respostas automáticas do assistente via WhatsApp

#### WhatsApp Cloud API - Upload de Mídia
- **Endpoint**: `https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/media`
- **Função**: Upload de arquivos (PDFs de boletos)
- **Uso**: Preparação de boletos para envio como documentos

#### WhatsApp Cloud API - Envio de Documentos
- **Endpoint**: `https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages`
- **Função**: Envio de documentos (PDFs) via WhatsApp
- **Uso**: Envio de boletos em anexo nas cobranças

#### WhatsApp Webhook
- **Endpoint**: `/webhook-cobranca`
- **Função**: Recebimento de eventos do WhatsApp (mensagens recebidas e status de entrega/leitura)
- **Eventos processados**:
  - `messages`: Mensagens recebidas dos clientes
  - `message_status`: Status de mensagens enviadas (sent, delivered, read)
- **Uso**: 
  - Processamento de mensagens dos clientes
  - Atualização de status de entrega e leitura de cobranças

## 🔄 Fluxo de Funcionamento

### 1. Configuração de Cobrança
1. Usuário acessa painel administrativo (Vercel)
2. Configura horário de execução e lembretes
3. Define mensagens personalizadas para cada lembrete
4. Salva configuração no Supabase

### 2. Execução Automática de Cobranças
1. Scheduler no backend verifica horário configurado
2. Busca parcelas via Bulk Data API do Sienge
3. Filtra parcelas baseado em lembretes configurados
4. Verifica se cobrança já foi enviada (evita duplicação)
5. Para cada boleto apto:
   - Busca informações do cliente
   - Baixa PDF do boleto via Sienge API
   - Faz upload do PDF na WhatsApp Cloud API
   - Envia documento via WhatsApp Cloud API
   - Salva `message_id` no Supabase para rastreamento
   - Registra histórico de envio

### 3. Rastreamento de Status
1. WhatsApp envia webhook com status (sent → delivered → read)
2. Backend recebe webhook em `/webhook-cobranca`
3. Busca mensagem no Supabase pelo `message_id`
4. Atualiza status no banco de dados
5. Frontend exibe ícones de status (✓ sent, ✓✓ delivered, ✓✓ azul read)

### 4. Interação Manual via WhatsApp
1. Cliente envia mensagem para o número do bot
2. Webhook recebe mensagem
3. Backend processa intenção (buscar boletos, relatório, etc.)
4. Sistema busca informações no Sienge
5. Envia resposta via WhatsApp Cloud API
6. Salva `message_id` para rastreamento de status

## 🗄️ Estrutura do Banco de Dados (Supabase)

### Tabelas Principais

#### `configuracoes_cobranca`
- Armazena configurações do sistema de cobrança
- Campos: horário_execucao, ativo, etc.

#### `lembretes_cobranca`
- Armazena lembretes configurados
- Campos: dias_antes, mensagem, enviar_segunda_via, envio_pdf

#### `historico_cobrancas`
- Registra cada envio de cobrança
- Campos: cliente_id, titulo_id, parcela_id, status, enviado_em, etc.

#### `logs_mensagens`
- Registra todas as mensagens do WhatsApp
- Campos: usuario_id, telefone, mensagem_enviada, status, whatsapp_message_id

#### `configuracoes_sienge`
- Armazena credenciais do Sienge
- Campos: subdomain, username, password (criptografados)

## 🔐 Segurança

### Variáveis de Ambiente
- `SUPABASE_URL`: URL do banco de dados Supabase
- `SUPABASE_KEY`: Chave de acesso ao Supabase
- `WHATSAPP_PHONE_NUMBER_ID`: ID do número de telefone no WhatsApp
- `WHATSAPP_TOKEN`: Token de acesso à WhatsApp Cloud API
- `WHATSAPP_VERIFY_TOKEN`: Token para verificação do webhook
- Credenciais do Sienge (armazenadas no Supabase)

### Medidas de Segurança
- Credenciais armazenadas em variáveis de ambiente
- Senhas do Sienge criptografadas no banco
- Webhook verificado com token
- HTTPS obrigatório em todas as conexões

## 📊 Monitoramento e Logs

### Logs do Backend (Render)
- Acessível via painel do Render
- Registra:
  - Execução de jobs de cobrança
  - Envio de mensagens WhatsApp
  - Erros e exceções
  - Chamadas de webhook

### Logs de Mensagens (Supabase)
- Tabela `logs_mensagens`
- Registra todas as interações via WhatsApp
- Inclui status de entrega e leitura

## 🚀 Deploy e CI/CD

### Backend (Render)
- Deploy automático via GitHub
- Trigger: Push para branch `main`
- Build: Instalação de dependências + Uvicorn
- Runtime: Python 3.14

### Frontend (Vercel)
- Deploy automático via GitHub
- Trigger: Push para branch `main`
- Build: React + TypeScript
- Runtime: Node.js

## 📞 Suporte e Manutenção

### Atualizações
- Atualizações de código via pull requests no GitHub
- Deploy automático após merge no branch `main`
- Sem downtime durante deploy (Render/Vercel)

### Monitoramento
- Logs em tempo real via painéis Render/Vercel
- Alertas de erro configurados
- Backup automático do Supabase

## 🔧 Tecnologias Utilizadas

### Backend
- Python 3.14
- FastAPI
- Uvicorn
- Requests
- Supabase Python Client
- APScheduler (agendamento)

### Frontend
- React 18
- TypeScript
- Vite
- TailwindCSS
- Lucide Icons
- shadcn/ui

### Infraestrutura
- Render (Backend)
- Vercel (Frontend)
- GitHub (Controle de versão)
- Supabase (Banco de dados)

## 📈 Escalabilidade

O sistema foi projetado para escalar horizontalmente:
- Backend: Render permite aumento de instâncias
- Frontend: Vercel escala automaticamente
- Banco de dados: Supabase suporta alto volume de requisições
- Cache local reduz carga nas APIs externas

## 🎯 Próximas Melhorias

- [ ] Dashboard analítico com métricas de cobrança
- [ ] Relatórios personalizados de cobrança
- [ ] Integração com outros canais (email, SMS)
- [ ] IA para personalização de mensagens
- [ ] Automação avançada com regras customizáveis

---

**Versão**: 1.0  
**Última Atualização**: Julho 2026  
**Contato**: [Seu Contato]
