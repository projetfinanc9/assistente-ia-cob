"""Prévia de cobrança e teste interno da integração Zenvia."""

import argparse
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from hmac import compare_digest
import json
import os
from pathlib import Path
import re
from typing import Annotated
from zoneinfo import ZoneInfo

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

router = APIRouter(prefix="/zenvia", tags=["Zenvia"])
MESSAGES_URL = "https://api.zenvia.com/v2/channels/whatsapp/messages"


def autorizar_previa(
    chave: Annotated[str | None, Header(alias="X-Zenvia-Preview-Key")] = None,
) -> None:
    esperada = os.getenv("ZENVIA_PREVIEW_KEY")
    if not esperada:
        raise HTTPException(503, "A chave de consulta de cobrança ainda não foi configurada.")
    if not chave or not compare_digest(chave.encode(), esperada.encode()):
        raise HTTPException(401, "Chave de prévia inválida.")


def saldo_aberto(valor: object) -> bool:
    try:
        saldo = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return False
    return saldo.is_finite() and saldo > 0


def consultar_parcelas(centro_custo: int, inicio: date, fim: date) -> list[dict]:
    if not 0 <= (fim - inicio).days < 31:
        raise HTTPException(422, "Informe um período de até 31 dias.")
    from sienge.sienge_cobranca import listar_parcelas_por_periodo_bulk

    try:
        return listar_parcelas_por_periodo_bulk(
            inicio.isoformat(), fim.isoformat(), [centro_custo], somente_consulta=True
        )
    except (requests.RequestException, ValueError, AttributeError):
        raise HTTPException(502, "O Sienge não retornou uma lista válida de parcelas.") from None


@router.get("/previa", dependencies=[Depends(autorizar_previa)])
def previa(response: Response, centro_custo: Annotated[int, Query(gt=0)], inicio: date, fim: date):
    response.headers["Cache-Control"] = "no-store"
    parcelas = consultar_parcelas(centro_custo, inicio, fim)

    candidatas = [
        {
            "cliente": item.get("clientName"),
            "titulo": item["billId"],
            "parcela": item["installmentId"],
            "vencimento": item.get("dueDate"),
            "saldo": item["balanceAmount"],
        }
        for item in parcelas
        if item.get("billId") and item.get("installmentId") and saldo_aberto(item.get("balanceAmount"))
    ]
    campos_situacao = sorted({
        campo for item in parcelas for campo in item
        if re.search(r"status|situation|delinquen|default|collection|bank", campo, re.I)
    })
    return {
        "consultadas": len(parcelas),
        "em_aberto": len(candidatas),
        "parcelas": candidatas[:200],
        "campos_situacao": campos_situacao,
    }


@router.get("/cobranca-manual/clientes", dependencies=[Depends(autorizar_previa)])
def clientes_cobranca(
    response: Response,
    centro_custo: Annotated[int, Query(gt=0)],
    inicio: date,
    fim: date,
    apenas_vencidas: bool = False,
):
    response.headers["Cache-Control"] = "no-store"
    return listar_clientes_cobranca(centro_custo, inicio, fim, apenas_vencidas)


def listar_clientes_cobranca(centro_custo: int, inicio: date, fim: date, apenas_vencidas: bool) -> list[dict]:
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    clientes = {}
    for item in consultar_parcelas(centro_custo, inicio, fim):
        cliente_id = item.get("clientId")
        titulo = item.get("billId")
        parcela = item.get("installmentId")
        saldo = item.get("balanceAmount")
        if not cliente_id or not titulo or not parcela or not saldo_aberto(saldo):
            continue
        try:
            vencimento = date.fromisoformat(str(item.get("dueDate"))[:10])
        except ValueError:
            continue
        if not inicio <= vencimento <= fim or (apenas_vencidas and vencimento >= hoje):
            continue
        cliente = clientes.setdefault(str(cliente_id), {
            "id": str(cliente_id),
            "nome": str(item.get("clientName") or f"Cliente {cliente_id}"),
            "parcelas": {},
        })
        chave_parcela = (str(titulo), str(parcela))
        cliente["parcelas"][chave_parcela] = {
            "titulo": str(titulo),
            "parcela": str(parcela),
            "vencimento": vencimento.isoformat(),
            "saldo": Decimal(str(saldo)),
        }

    resultado = []
    for cliente in clientes.values():
        parcelas = sorted(
            cliente["parcelas"].values(),
            key=lambda item: (item["vencimento"], item["titulo"], item["parcela"]),
        )
        parcelas = [{**parcela, "saldo": format(parcela["saldo"], ".2f")} for parcela in parcelas]
        versao = sha256(json.dumps(parcelas, sort_keys=True).encode()).hexdigest()
        resultado.append({
            "id": cliente["id"],
            "nome": cliente["nome"],
            "saldo": format(sum(Decimal(parcela["saldo"]) for parcela in parcelas), "f"),
            "parcelas": parcelas,
            "versao": versao,
        })
    return sorted(resultado, key=lambda cliente: (cliente["nome"].casefold(), cliente["id"]))


def enviar_teste(sender_id: str, template_id: str, campos: dict[str, str]) -> str:
    token = os.getenv("ZENVIA_API_TOKEN")
    destino = os.getenv("ZENVIA_TEST_PHONE", "")
    if not token or not re.fullmatch(r"55[1-9][0-9]{9,10}", destino):
        raise ValueError("Configure o token e um número interno com DDI e DDD.")
    return enviar_template(token, sender_id, template_id, destino, campos)


class RespostaZenvia(ValueError):
    def __init__(self, mensagem: str, status: str):
        super().__init__(mensagem)
        self.status = status


def enviar_template(token: str, sender_id: str, template_id: str, destino: str, campos: dict[str, str]) -> str:
    if not sender_id.strip() or not template_id.strip():
        raise ValueError("Informe o Sender ID e o ID do template aprovado.")
    try:
        resposta = requests.post(
            MESSAGES_URL,
            headers={"X-API-TOKEN": token},
            json={
                "from": sender_id,
                "to": destino,
                "contents": [{"type": "template", "templateId": template_id, "fields": campos}],
            },
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise RespostaZenvia("A Zenvia não respondeu. Confira o envio antes de repetir.", "incerto") from None
    if not resposta.ok:
        status = "incerto" if resposta.status_code >= 500 or resposta.status_code == 408 else "recusado"
        raise RespostaZenvia(f"A Zenvia retornou HTTP {resposta.status_code}.", status)
    try:
        identificador = resposta.json().get("id")
    except (ValueError, AttributeError):
        identificador = None
    if not isinstance(identificador, str) or not identificador:
        raise RespostaZenvia("Resposta sem ID da mensagem. Confira o envio antes de repetir.", "incerto")
    return identificador


def main() -> None:
    parser = argparse.ArgumentParser(description="Envie um template Zenvia para um número interno.")
    parser.add_argument("--sender-id", required=True)
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--campos", type=Path, required=True, help="Arquivo JSON com valores fictícios.")
    args = parser.parse_args()
    try:
        campos = json.loads(args.campos.read_text(encoding="utf-8"))
        if not isinstance(campos, dict) or any(not isinstance(valor, str) for valor in campos.values()):
            raise ValueError("Informe um objeto JSON com os campos do template como texto.")
        identificador = enviar_teste(args.sender_id, args.template_id, campos)
    except (ValueError, OSError) as erro:
        parser.exit(1, f"{erro}\n")
    print(f"Mensagem aceita pela Zenvia. ID: {identificador}")


if __name__ == "__main__":
    main()
