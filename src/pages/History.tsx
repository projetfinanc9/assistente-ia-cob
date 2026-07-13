import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Loader2, X, FileText, FileSpreadsheet } from "lucide-react";
import { useEffect, useState } from "react";
import { Label } from "@/components/ui/label";
import { formatDistanceToNow, format } from "date-fns";
import { ptBR } from "date-fns/locale";

interface CobrancaHistory {
  id: string;
  cliente: string;
  telefone: string;
  data: string;
  status: string;
  mensagem: string;
  vencimento?: string;
  valor?: number;
  tipo_envio?: string;
  titulo_id?: number;
  parcela_id?: number;
  dias_antes?: number;
}

const History = () => {
  const [histories, setHistories] = useState<CobrancaHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedHistory, setSelectedHistory] = useState<CobrancaHistory | null>(null);

  useEffect(() => {
    loadHistories();
  }, []);

  const loadHistories = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/cobranca-historico`);
      const data = await response.json();
      setHistories(data.historico || []);
    } catch (error) {
      console.error("Erro ao carregar histórico:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredHistories = histories.filter(
    (h) =>
      h.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.telefone.includes(searchTerm)
  );

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "destructive" | "secondary"> = {
      enviado: "default",
      erro: "destructive",
      pendente: "secondary",
    };

    const labels: Record<string, string> = {
      enviado: "Enviado",
      erro: "Erro",
      pendente: "Pendente",
    };

    return (
      <Badge variant={variants[status] || "secondary"}>
        {labels[status] || status}
      </Badge>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Histórico de Cobranças</h1>
        <p className="text-muted-foreground">
          Consulte todos os envios de cobrança via WhatsApp
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Envios de Cobrança</CardTitle>
          <div className="flex items-center gap-2 mt-4">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por cliente, telefone..."
              className="max-w-sm"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data/Hora</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Mensagem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredHistories.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="text-center py-8 text-muted-foreground"
                    >
                      {searchTerm
                        ? "Nenhum resultado encontrado"
                        : "Nenhum envio registrado ainda"}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredHistories.map((history) => (
                    <TableRow 
                      key={history.id} 
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelectedHistory(history)}
                    >
                      <TableCell className="text-sm">
                        {formatDistanceToNow(new Date(history.data), {
                          addSuffix: true,
                          locale: ptBR,
                        })}
                      </TableCell>
                      <TableCell className="font-medium">{history.cliente}</TableCell>
                      <TableCell className="font-mono text-sm">{history.telefone}</TableCell>
                      <TableCell>{getStatusBadge(history.status)}</TableCell>
                      <TableCell className="text-sm max-w-md truncate">
                        {history.mensagem}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Modal de Detalhes */}
      {selectedHistory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Detalhes da Cobrança</CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedHistory(null)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Cliente</p>
                  <p className="font-semibold">{selectedHistory.cliente}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Telefone</p>
                  <p className="font-mono">{selectedHistory.telefone}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Data/Hora do Envio</p>
                  <p>{format(new Date(selectedHistory.data), "dd/MM/yyyy HH:mm:ss", { locale: ptBR })}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Status</p>
                  {getStatusBadge(selectedHistory.status)}
                </div>
                {selectedHistory.titulo_id && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Número do Título</p>
                    <p className="font-mono">{selectedHistory.titulo_id}</p>
                  </div>
                )}
                {selectedHistory.parcela_id && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Número da Parcela</p>
                    <p className="font-mono">{selectedHistory.parcela_id}</p>
                  </div>
                )}
                {selectedHistory.vencimento && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Vencimento</p>
                    <p>{format(new Date(selectedHistory.vencimento), "dd/MM/yyyy", { locale: ptBR })}</p>
                  </div>
                )}
                {selectedHistory.valor && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Valor</p>
                    <p className="font-semibold">R$ {selectedHistory.valor.toFixed(2)}</p>
                  </div>
                )}
                {selectedHistory.dias_antes !== undefined && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Dias Antes/Depois</p>
                    <p>{selectedHistory.dias_antes} dias</p>
                  </div>
                )}
                {selectedHistory.tipo_envio && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Tipo de Envio</p>
                    <p>{selectedHistory.tipo_envio}</p>
                  </div>
                )}
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Mensagem Enviada</p>
                <div className="bg-muted p-4 rounded-md text-sm whitespace-pre-wrap">
                  {selectedHistory.mensagem}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default History;
