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
import { Search, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface CobrancaHistory {
  id: string;
  cliente: string;
  telefone: string;
  data: string;
  status: string;
  mensagem: string;
}

const History = () => {
  const [histories, setHistories] = useState<CobrancaHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

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
                    <TableRow key={history.id}>
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
    </div>
  );
};

export default History;
