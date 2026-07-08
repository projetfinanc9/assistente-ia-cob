# sienge/sienge_ia.py
import logging
import os
from openai import OpenAI
import pandas as pd

logging.warning("🤖 Rodando módulo sienge_ia.py (análises automáticas de dados financeiros)")

# ⚙️ Inicializa o cliente OpenAI — precisa da variável OPENAI_API_KEY configurada no Render
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI()
    logging.info("✅ Cliente OpenAI inicializado")
else:
    logging.warning("⚠️ OPENAI_API_KEY não configurada - funcionalidades de IA estarão desabilitadas")

# ==========================================================
# 🔍 Função base de análise financeira (resumo executivo)
# ==========================================================
def gerar_analise_financeira(titulo: str, dados: pd.DataFrame) -> str:
    """Gera uma análise executiva com base no DataFrame de despesas/receitas."""
    try:
        if not client:
            return "⚠️ Funcionalidade de IA não disponível - configure OPENAI_API_KEY"
        if dados is None or len(dados) == 0:
            return "⚠️ Nenhum dado encontrado para análise."

        # Amostra compacta para contexto
        preview = dados.head(40).to_markdown(index=False)

        prompt = f"""
Você é um analista financeiro especialista em empresas de construção civil.
Com base nos dados abaixo, gere uma **análise executiva inteligente**, contendo:
1️⃣ Principais destaques (receitas, despesas, lucro ou prejuízo);
2️⃣ Obras, centros de custo e fornecedores de maior impacto;
3️⃣ Alertas de risco ou anomalias (valores concentrados, sazonalidade, etc.);
4️⃣ Recomendações práticas (redução de custos, otimização, renegociação, priorização de obras);
5️⃣ Um pequeno resumo de tendência geral (positivo, neutro, negativo).

Formate em Markdown, com subtítulos e bullet points, estilo relatório profissional.
Título do relatório: **{titulo}**

Amostra de dados (até 40 linhas):
{preview}
        """

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um consultor financeiro sênior e especialista em obras e construção civil."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1000,
        )
        return resp.choices[0].message.content

    except Exception as e:
        logging.exception("❌ Erro na IA (gerar_analise_financeira):")
        return f"❌ Erro ao gerar análise financeira: {e}"


# ==========================================================
# 🎞️ Geração de Apresentação Estilo Gamma (slide por slide)
# ==========================================================
def gerar_apresentacao_gamma(titulo: str, dados: pd.DataFrame) -> str:
    """
    Gera uma apresentação executiva (modo 'Gamma') em formato de slides markdown.
    Ideal para ser exibida no dashboard Streamlit com st.markdown().
    """
    try:
        if not client:
            return "⚠️ Funcionalidade de IA não disponível - configure OPENAI_API_KEY"
        if dados is None or len(dados) == 0:
            return "⚠️ Nenhum dado encontrado para apresentação."

        # Resumo simples de dados (colunas mais relevantes)
        if "obra" in dados.columns:
            top_obras = dados["obra"].value_counts().head(5).to_dict()
        else:
            top_obras = {}

        if "fornecedor" in dados.columns:
            top_fornecedores = dados["fornecedor"].value_counts().head(5).to_dict()
        else:
            top_fornecedores = {}

        resumo_texto = f"""
Top Obras: {', '.join([f"{k} ({v})" for k, v in top_obras.items()]) if top_obras else '—'}
Top Fornecedores: {', '.join([f"{k} ({v})" for k, v in top_fornecedores.items()]) if top_fornecedores else '—'}
"""

        preview = dados.head(30).to_markdown(index=False)

        prompt = f"""
Você é um analista financeiro sênior e precisa montar uma **apresentação estilo Gamma** 
com base nos dados financeiros abaixo.

Crie de 5 a 8 SLIDES no formato Markdown, cada um com:
- Título (ex: "Resumo Geral", "Top Obras", "Análise de Custos", "Recomendações")
- Texto curto e direto (2–4 linhas)
- Use emojis de apoio (💰📈⚠️🏗️💡📊)

Título principal: {titulo}

Resumo dos dados:
{resumo_texto}

Amostra (até 30 linhas):
{preview}

Formate a saída em seções assim:
## Slide 1 — Resumo Geral
texto...

## Slide 2 — Top Obras
texto...

## Slide 3 — Custos e Despesas
texto...
        """

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é um especialista em apresentações corporativas para construção civil."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=1500,
        )

        conteudo = resp.choices[0].message.content
        return conteudo.strip()

    except Exception as e:
        logging.exception("❌ Erro na IA (gerar_apresentacao_gamma):")
        return f"❌ Erro ao gerar apresentação: {e}"


# ==========================================================
# 🔄 Função auxiliar (unifica chamadas)
# ==========================================================
def gerar_apresentacao_financeira(titulo: str, dados: pd.DataFrame, modo="resumo") -> str:
    """
    Função unificada para gerar tanto relatórios resumidos quanto apresentações completas.
    modo="resumo" → análise textual (executiva)
    modo="gamma" → slides estilo apresentação
    """
    if modo == "gamma":
        return gerar_apresentacao_gamma(titulo, dados)
    else:
        return gerar_analise_financeira(titulo, dados)
