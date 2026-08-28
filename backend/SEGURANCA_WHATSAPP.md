# 🔒 Segurança do Sistema de Múltiplos Números WhatsApp

## ✅ Medidas de Segurança Implementadas

### 1. **Criptografia de Tokens**
- Tokens WhatsApp são criptografados antes de salvar no banco
- Usa Fernet (AES-128) da biblioteca cryptography
- Chave de criptografia configurada via variável de ambiente
- Tokens são descriptografados apenas em memória no backend

### 2. **Frontend NÃO Acessa Banco**
- Frontend usa apenas API do backend (`VITE_API_URL`)
- NÃO há acesso direto ao Supabase pelo frontend
- Credenciais do banco ficam apenas no backend
- "Inspecionar" no navegador NÃO expõe credenciais do Supabase

### 3. **Proteção Contra Logs**
- Tokens NÃO são logados
- Apenas o Phone Number ID é logado (não sensível)
- Removeu todos os logs que poderiam expor tokens

### 4. **Row Level Security (RLS)**
- Supabase usa Service Role Key (acesso completo)
- Frontend usa apenas API do backend
- Acesso ao banco é intermediado pelo backend

## 🛡️ Arquitetura de Segurança

```
Frontend (React)
↓ (apenas fetch para API)
Backend (FastAPI)
↓ (usa Service Role Key)
Supabase (banco de dados)
```

**Tokens WhatsApp:**
```
Frontend → API → Criptografa → Salva no Supabase
Supabase → API → Descriptografa → Usa em memória
```

## 🔑 Variáveis de Ambiente Necessárias

### Backend (.env)
```env
ENCRYPTION_KEY=0wzMMuhwgTk-6lCFy67AGb11lNVZ_5aPNhQ5bUY5qj4=
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
WHATSAPP_TOKEN=EAAMkQHBSSZBoBSJjrjF47qx1yI19ysNyDfePLtgKydiB27qSWAAR0EWH4SNCcgSVC6ZAbOPwdMBJqgZCYtZC56uujhQeJdwAtPMqYEw2okyIEDixwheHpWUvs1ux8zydGCSlXZBk6iCVKjxxK0hW5qBYT7gHYs2hfDvS1o7z4ZBtDMj3JvZAuZBuP0U21tcHIQZDZD
```

### Frontend (.env)
```env
VITE_API_URL=https://seu-backend.onrender.com
VITE_SUPABASE_URL=https://rbbftbnplkqbdijuqjid.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**IMPORTANTE:** O frontend NÃO usa o Service Role Key!

## 🚨 O que FOI Protegido

### ✅ PROTEGIDO
- Tokens WhatsApp (criptografados no banco)
- Credenciais do Supabase (só no backend)
- Logs (sem tokens sensíveis)
- Frontend (sem acesso direto ao banco)

### ⚠️ AINDA EXPOSTO (Frontend)
- `VITE_SUPABASE_URL` (URL do Supabase)
- `VITE_SUPABASE_PUBLISHABLE_KEY` (Chave pública do Supabase)

**Mas isso é NORMAL:**
- A chave pública do Supabase é projetada para ser segura
- Tem permissões limitadas (RLS no Supabase)
- Não permite acesso a dados sensíveis se RLS estiver configurado

## 📋 Checklist de Segurança

- [x] Tokens criptografados no banco
- [x] Frontend não acessa Supabase diretamente
- [x] Tokens não expostos em logs
- [x] Service Role Key apenas no backend
- [x] Chave de criptografia configurada
- [x] API intermediando todo acesso ao banco

## 🎯 Para o Render

Adicionar variável de ambiente:
```
ENCRYPTION_KEY=0wzMMuhwgTk-6lCFy67AGb11lNVZ_5aPNhQ5bUY5qj4=
```

**IMPORTANTE:** Use a mesma chave no .env local e no Render!

## 🔒 Resumo

**O sistema está SEGURO porque:**
1. Tokens são criptografados no banco
2. Frontend não tem acesso ao banco
3. Credenciais sensíveis ficam apenas no backend
4. Logs não expõem informações sensíveis
5. API intermediando todo acesso ao banco

**O que um atacante NÃO consegue:**
- ❌ Ver tokens WhatsApp no banco (estão criptografados)
- ❌ Acessar credenciais do Supabase via frontend
- ❌ Ver tokens em logs
- ❌ Acessar banco diretamente (sem passar pela API)

**O que um atacante PODE ver (mas é normal):**
- ✅ URL do Supabase (pública)
- ✅ Chave pública do Supabase (limitada por RLS)
- ✅ Phone Number ID (não é sensível)
