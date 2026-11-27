import { useState, type FormEvent } from "react";
import { ClipboardList, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Parcela = { titulo: string; parcela: string; vencimento: string; saldo: string };
type Cliente = { id: string; nome: string; saldo: string; parcelas: Parcela[]; versao: string };
type Modelo = { id: string; nome: string };
type Opcoes = { habilitado: boolean; remetentes: { id: string; nome: string; modelos: Modelo[] }[] };
type Resultado = { id: string; status: string; detalhe: string | null };
type Consulta = { centro_custo: number; inicio: string; fim: string; apenas_vencidas: boolean; chave: string };
const statusEnvio: Record<string, string> = {
  aceito: "Aceito pela Zenvia", recusado: "Recusado", ignorado: "Não enviado",
  incerto: "Aguardando conferência", processando: "Registrado para conferência",
};

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const formatarData = (data: string) => data.split("-").reverse().join("/");
const normalizar = (texto: string) => texto.toLocaleLowerCase("pt-BR").normalize("NFD").replace(/\p{Diacritic}/gu, "");

export default function CobrancaConfig() {
  const [clientes, setClientes] = useState<Cliente[] | null>(null);
  const [selecionados, setSelecionados] = useState(new Set<string>());
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [revisar, setRevisar] = useState(false);
  const [consulta, setConsulta] = useState<Consulta | null>(null);
  const [opcoes, setOpcoes] = useState<Opcoes | null>(null);
  const [remetente, setRemetente] = useState("");
  const [modelo, setModelo] = useState("");
  const [chaveEnvio, setChaveEnvio] = useState("");
  const [lote, setLote] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [resultados, setResultados] = useState<Resultado[]>([]);
  const [erroEnvio, setErroEnvio] = useState("");
  const modelos = opcoes?.remetentes.find(item => item.id === remetente)?.modelos ?? [];

  const visiveis = (clientes ?? []).filter((cliente) => {
    const termo = normalizar(busca.trim());
    return normalizar(cliente.nome).includes(termo) || cliente.id.includes(termo) ||
      cliente.parcelas.some(({ titulo }) => titulo.includes(termo));
  });
  const selecao = (clientes ?? []).filter(({ id }) => selecionados.has(id));
  const totalSelecionado = selecao.reduce((total, cliente) => total + Number(cliente.saldo), 0);
  const todosVisiveis = visiveis.length > 0 && visiveis.every(({ id }) => selecionados.has(id));

  function selecionar(ids: string[], marcado: boolean) {
    setSelecionados((anteriores) => {
      const atualizados = new Set(anteriores);
      ids.forEach((id) => {
        if (marcado) atualizados.add(id);
        else atualizados.delete(id);
      });
      return atualizados;
    });
  }

  async function consultar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const campos = new FormData(event.currentTarget);
    const selecionada = {
      centro_custo: Number(campos.get("centro_custo")),
      inicio: String(campos.get("inicio")),
      fim: String(campos.get("fim")),
      apenas_vencidas: campos.has("apenas_vencidas"),
      chave: String(campos.get("chave")),
    };
    const query = new URLSearchParams({
      centro_custo: String(selecionada.centro_custo),
      inicio: selecionada.inicio,
      fim: selecionada.fim,
      apenas_vencidas: String(selecionada.apenas_vencidas),
    });
    const headers = { "X-Zenvia-Preview-Key": selecionada.chave };
    setCarregando(true);
    setErro("");
    setClientes(null);
    setConsulta(null);
    setOpcoes(null);
    setRemetente("");
    setModelo("");
    setBusca("");
    setSelecionados(new Set());
    try {
      const resposta = await fetch(`${apiUrl}/zenvia/cobranca-manual/clientes?${query}`, {
        headers,
        cache: "no-store",
      });
      if (!resposta.ok) {
        const dados = await resposta.json();
        setErro(typeof dados.detail === "string" ? dados.detail : "Confira os filtros da consulta.");
        return;
      }
      setClientes(await resposta.json());
      setConsulta(selecionada);
      const catalogo = await fetch(`${apiUrl}/zenvia/cobranca-manual/opcoes`, { headers, cache: "no-store" });
      if (catalogo.ok) setOpcoes(await catalogo.json());
    } catch {
      setErro("Não foi possível concluir a consulta.");
    } finally {
      setCarregando(false);
    }
  }

  function abrirRevisao() {
    setLote(crypto.randomUUID());
    setResultados([]);
    setErroEnvio("");
    setChaveEnvio("");
    setRevisar(true);
  }

  async function enviarSelecionados(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!consulta || !modelo || !remetente || enviando || !opcoes?.habilitado || !chaveEnvio) return;
    const { chave, ...filtros } = consulta;
    const concluidos = new Set(resultados.map(({ id }) => id));
    const pendentes = selecao.filter(({ id }) => !concluidos.has(id));
    const headers = {
      "Content-Type": "application/json",
      "X-Zenvia-Preview-Key": chave,
      "X-Zenvia-Send-Key": chaveEnvio,
    };
    setEnviando(true);
    setErroEnvio("");
    try {
      for (let i = 0; i < pendentes.length; i += 5) {
        const clientes = pendentes.slice(i, i + 5).map(({ id, versao }) => ({ id, versao }));
        const resposta = await fetch(`${apiUrl}/zenvia/cobranca-manual/enviar`, {
          method: "POST",
          headers,
          body: JSON.stringify({ ...filtros, id: lote, remetente, modelo, clientes }),
        });
        const dados = await resposta.json();
        if (!resposta.ok) {
          setErroEnvio(typeof dados.detail === "string" ? dados.detail : "Não foi possível concluir o lote.");
          return;
        }
        setResultados(anteriores => [...anteriores, ...dados.resultados]);
      }
      setChaveEnvio("");
    } catch {
      setErroEnvio("O envio foi interrompido. Retome o mesmo lote para conferir os envios já registrados.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Cobrança manual</h1>
        <p className="mt-1 text-muted-foreground">Consulte as parcelas em aberto no Sienge e escolha os clientes da cobrança.</p>
      </header>

      <Card>
        <CardHeader><CardTitle>Consultar clientes</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={consultar} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1">
                <Label htmlFor="centro">ID do centro de custo</Label>
                <Input id="centro" name="centro_custo" type="number" min="1" required />
              </div>
              <div className="space-y-1">
                <Label htmlFor="inicio">Vencimento de</Label>
                <Input id="inicio" name="inicio" type="date" required />
              </div>
              <div className="space-y-1">
                <Label htmlFor="fim">Vencimento até</Label>
                <Input id="fim" name="fim" type="date" required />
              </div>
              <div className="space-y-1">
                <Label htmlFor="chave">Chave de acesso</Label>
                <Input id="chave" name="chave" type="password" autoComplete="off" required />
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <Label className="flex items-center gap-2">
                <input name="apenas_vencidas" type="checkbox" className="accent-primary" />
                Apenas parcelas vencidas
              </Label>
              <Button type="submit" disabled={carregando}>
                <Search className="mr-2 h-4 w-4" />{carregando ? "Consultando…" : "Buscar no Sienge"}
              </Button>
            </div>
          </form>
          {erro && <p className="mt-4 text-sm text-destructive" role="alert">{erro}</p>}
        </CardContent>
      </Card>

      {clientes && (
        <Card>
          <CardHeader><CardTitle>Clientes com parcelas em aberto</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-52 flex-1 space-y-1">
                <Label htmlFor="buscar-cliente">Buscar por cliente, código ou título</Label>
                <Input id="buscar-cliente" value={busca} onChange={(event) => setBusca(event.target.value)} />
              </div>
              <Button variant="outline" disabled={!visiveis.length}
                onClick={() => selecionar(visiveis.map(({ id }) => id), !todosVisiveis)}>
                {todosVisiveis ? "Desmarcar resultados" : "Selecionar todos os resultados"}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground" role="status">
              {visiveis.length} de {clientes.length} clientes · {selecao.length} selecionados · {moeda.format(totalSelecionado)}
            </p>
            {visiveis.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Selecionar</TableHead><TableHead>Cliente</TableHead><TableHead>Parcelas</TableHead><TableHead>Saldo em aberto</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {visiveis.map((cliente) => (
                    <TableRow key={cliente.id} data-state={selecionados.has(cliente.id) ? "selected" : undefined}>
                      <TableCell>
                        <Checkbox aria-label={`Selecionar ${cliente.nome}, código ${cliente.id}`}
                          checked={selecionados.has(cliente.id)}
                          onCheckedChange={(marcado) => selecionar([cliente.id], marcado === true)} />
                      </TableCell>
                      <TableCell className="font-medium">{cliente.nome} <span className="text-muted-foreground">#{cliente.id}</span></TableCell>
                      <TableCell>{cliente.parcelas.length}</TableCell>
                      <TableCell>{moeda.format(Number(cliente.saldo))}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : <p className="py-4 text-sm text-muted-foreground">Nenhum cliente encontrado com esses filtros.</p>}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="remetente-zenvia">Número remetente</Label>
                <select id="remetente-zenvia" className="w-full rounded-md border bg-background p-2 text-sm"
                  disabled={!opcoes?.remetentes.length} value={remetente} onChange={(event) => {
                    setRemetente(event.target.value);
                    setModelo("");
                  }}>
                  <option value="">Escolher número</option>
                  {opcoes?.remetentes.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="modelo-zenvia">Modelo de mensagem</Label>
                <select id="modelo-zenvia" className="w-full rounded-md border bg-background p-2 text-sm"
                  disabled={!modelos.length} value={modelo} onChange={(event) => setModelo(event.target.value)}>
                  <option value="">Escolher modelo</option>
                  {modelos.map(item => <option key={item.id} value={item.id}>{item.nome}</option>)}
                </select>
              </div>
            </div>
            {!opcoes?.habilitado && <p className="text-sm text-muted-foreground">
              O envio está disponível após configurar o remetente, os modelos aprovados e as credenciais da Zenvia no backend.
            </p>}
            <Button disabled={!selecao.length} onClick={abrirRevisao}>
              <ClipboardList className="mr-2 h-4 w-4" /> Revisar clientes selecionados
            </Button>
          </CardContent>
        </Card>
      )}

      <Dialog open={revisar} onOpenChange={(aberto) => { if (!enviando) setRevisar(aberto); }}>
        <DialogContent className="max-h-[85vh] overflow-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Revisão da cobrança</DialogTitle>
            <DialogDescription>
              {selecao.length} clientes · {moeda.format(totalSelecionado)} em aberto.
              {remetente && modelo && ` Remetente: ${opcoes?.remetentes.find(item => item.id === remetente)?.nome}. Modelo: ${modelos.find(item => item.id === modelo)?.nome}.`}
            </DialogDescription>
          </DialogHeader>
          <ul className="divide-y">
            {selecao.map((cliente) => (
              <li key={cliente.id} className="py-3">
                <p className="font-medium">{cliente.nome} · {moeda.format(Number(cliente.saldo))}</p>
                <ul className="mt-1 text-sm text-muted-foreground">
                  {cliente.parcelas.map((parcela) => (
                    <li key={`${parcela.titulo}-${parcela.parcela}`}>
                      Título {parcela.titulo}, parcela {parcela.parcela} · {formatarData(parcela.vencimento)} · {moeda.format(Number(parcela.saldo))}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
          {opcoes?.habilitado && remetente && modelo && (
            <form onSubmit={enviarSelecionados} className="space-y-3 border-t pt-4">
              {resultados.length < selecao.length && (
                <>
                  <Label htmlFor="chave-envio">Chave de autorização de envio</Label>
                  <Input id="chave-envio" type="password" autoComplete="off" required value={chaveEnvio}
                    disabled={enviando} onChange={(event) => setChaveEnvio(event.target.value)} />
                  <Button type="submit" disabled={enviando}>
                    {enviando ? "Enviando…" : erroEnvio ? "Retomar o mesmo lote" : "Confirmar envio pela Zenvia"}
                  </Button>
                </>
              )}
              {erroEnvio && <p role="alert" className="text-sm text-destructive">{erroEnvio}</p>}
              {resultados.length > 0 && (
                <ul className="space-y-1 text-sm" aria-label="Resultado dos envios">
                  {resultados.map(item => (
                    <li key={item.id}>
                      {selecao.find(cliente => cliente.id === item.id)?.nome} · {statusEnvio[item.status] ?? item.status}
                      {item.detalhe && ` · ${item.detalhe}`}
                    </li>
                  ))}
                </ul>
              )}
            </form>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
}
