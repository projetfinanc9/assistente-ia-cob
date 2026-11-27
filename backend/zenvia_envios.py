"""Envios de cobrança iniciados manualmente no painel."""

from datetime import date, datetime
from decimal import Decimal
from hmac import compare_digest
import json
import os
import re
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field, StringConstraints, ValidationError
import requests

from zenvia_piloto import RespostaZenvia, autorizar_previa, enviar_template, listar_clientes_cobranca

router = APIRouter(prefix="/zenvia/cobranca-manual", tags=["Cobrança manual"])
TABELA = "zenvia_envios_manuais"
SegredoEnvio = Annotated[str | None, Header(alias="X-Zenvia-Send-Key")]
IdCliente = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]


class Modelo(BaseModel):
    id: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    campos: dict[str, Literal["cliente", "saldo", "vencimento", "quantidade"]] = Field(default_factory=dict)


class Remetente(BaseModel):
    id: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    modelos: list[Modelo] = Field(min_length=1)


class Catalogo(BaseModel):
    remetentes: list[Remetente] = Field(min_length=1)


class Destinatario(BaseModel):
    id: IdCliente
    versao: str = Field(pattern=r"^[a-f0-9]{64}$")


class Lote(BaseModel):
    id: UUID
    centro_custo: int = Field(gt=0)
    inicio: date
    fim: date
    apenas_vencidas: bool = False
    remetente: str = Field(min_length=1, max_length=200)
    modelo: str = Field(min_length=1, max_length=200)
    clientes: list[Destinatario] = Field(min_length=1, max_length=5)


def ler_catalogo() -> Catalogo | None:
    valor = os.getenv("ZENVIA_CATALOGO_WHATSAPP")
    if not valor:
        return None
    try:
        return Catalogo.model_validate_json(valor)
    except ValidationError:
        raise HTTPException(503, "Revise o catálogo de números e modelos no backend.") from None


@router.get("/opcoes", dependencies=[Depends(autorizar_previa)])
def opcoes(response: Response):
    response.headers["Cache-Control"] = "no-store"
    catalogo = ler_catalogo()
    habilitado = bool(catalogo and all(os.getenv(chave) for chave in (
        "ZENVIA_API_TOKEN", "ZENVIA_SEND_KEY", "SUPABASE_SERVICE_ROLE_KEY"
    )))
    return {"habilitado": habilitado, "remetentes": catalogo.remetentes if catalogo else []}


def telefone_sienge(cliente_id: str) -> str | None:
    from sienge.sienge_config import BASE_URL, json_headers

    resposta = requests.get(f"{BASE_URL}/customers/{cliente_id}", headers=json_headers, timeout=10)
    resposta.raise_for_status()
    telefones = resposta.json().get("phones") or []
    for telefone in sorted(telefones, key=lambda item: not item.get("main")):
        texto = str(telefone.get("number") or "").strip()
        if not re.fullmatch(r"[+0-9 ()-]+", texto):
            continue
        numero = re.sub(r"\D", "", texto)
        if len(numero) in (10, 11):
            numero = "55" + numero
        if re.fullmatch(r"55[1-9][0-9][2-9][0-9]{7,8}", numero):
            return numero
    return None


def campos_modelo(modelo: Modelo, cliente: dict) -> dict[str, str]:
    total = f"{Decimal(cliente['saldo']):,.2f}".translate(str.maketrans(",.", ".,"))
    valores = {
        "cliente": cliente["nome"],
        "saldo": f"R$ {total}",
        "quantidade": str(len(cliente["parcelas"])),
        "vencimento": date.fromisoformat(cliente["parcelas"][0]["vencimento"]).strftime("%d/%m/%Y"),
    }
    return {campo: valores[origem] for campo, origem in modelo.campos.items()}


def resposta_cliente(id_cliente: str, status: str, detalhe: str | None = None) -> dict:
    return {"id": id_cliente, "status": status, "detalhe": detalhe}


def enviar_cliente(db, lote: Lote, destino: Destinatario, cliente: dict | None, modelo: Modelo, token: str, dia: str):
    id_cliente = destino.id
    registro = {
        "lote_id": str(lote.id), "cliente_id": id_cliente, "remetente": lote.remetente,
        "modelo": modelo.id, "versao": destino.versao, "dia": dia, "status": "processando",
    }
    def buscar_registro():
        return db.table(TABELA).select("status,detalhe").eq(
            "lote_id", str(lote.id)
        ).eq("cliente_id", id_cliente).execute().data

    existente = buscar_registro()
    if existente:
        return resposta_cliente(id_cliente, existente[0]["status"], existente[0].get("detalhe"))
    if not cliente or cliente["versao"] != destino.versao:
        return resposta_cliente(id_cliente, "ignorado", "O saldo mudou no Sienge. Atualize a consulta.")
    try:
        telefone = telefone_sienge(id_cliente)
    except (requests.RequestException, ValueError, AttributeError):
        return resposta_cliente(id_cliente, "ignorado", "Não foi possível consultar o telefone no Sienge.")
    if not telefone:
        return resposta_cliente(id_cliente, "ignorado", "O cliente não possui telefone brasileiro válido.")

    try:
        db.table(TABELA).insert(registro).execute()
    except APIError as erro:
        if erro.code != "23505":
            raise
        existente = buscar_registro()
        if existente:
            return resposta_cliente(id_cliente, existente[0]["status"], existente[0].get("detalhe"))
        return resposta_cliente(id_cliente, "ignorado", "Já existe um envio para esse modelo e saldo nesta data.")

    try:
        mensagem_id = enviar_template(token, lote.remetente, modelo.id, telefone, campos_modelo(modelo, cliente))
        status, detalhe = "aceito", None
    except RespostaZenvia as erro:
        mensagem_id, status, detalhe = None, erro.status, str(erro)
    gravacao = {"status": status, "detalhe": detalhe, "mensagem_id": mensagem_id}
    db.table(TABELA).update(gravacao).eq("lote_id", str(lote.id)).eq("cliente_id", id_cliente).execute()
    return resposta_cliente(id_cliente, status, detalhe)


@router.post("/enviar", dependencies=[Depends(autorizar_previa)])
def enviar(lote: Lote, chave_envio: SegredoEnvio = None):
    esperada = os.getenv("ZENVIA_SEND_KEY")
    token = os.getenv("ZENVIA_API_TOKEN")
    catalogo = ler_catalogo()
    if not esperada or not token or not catalogo or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        raise HTTPException(503, "O envio pela Zenvia ainda não foi configurado.")
    if not chave_envio or not compare_digest(chave_envio.encode(), esperada.encode()):
        raise HTTPException(401, "Chave de envio inválida.")
    remetente = next((item for item in catalogo.remetentes if item.id == lote.remetente), None)
    modelo = next((item for item in remetente.modelos if item.id == lote.modelo), None) if remetente else None
    if not modelo:
        raise HTTPException(422, "O modelo escolhido não está vinculado a esse remetente.")
    if len({cliente.id for cliente in lote.clientes}) != len(lote.clientes):
        raise HTTPException(422, "A seleção contém clientes repetidos.")

    from supabase_client import supabase

    if supabase is None:
        raise HTTPException(503, "O registro de envios está indisponível.")
    clientes = {
        item["id"]: item for item in listar_clientes_cobranca(
            lote.centro_custo, lote.inicio, lote.fim, lote.apenas_vencidas
        )
    }
    dia = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    try:
        return {"resultados": [
            enviar_cliente(supabase, lote, destino, clientes.get(destino.id), modelo, token, dia)
            for destino in lote.clientes
        ]}
    except (APIError, requests.RequestException):
        raise HTTPException(503, "O registro de envios falhou. Consulte o lote antes de repetir.") from None
