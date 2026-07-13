import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Search, RefreshCw, MessageSquare, Send, Inbox } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface MessageLog {
  id: string;
  telefone: string;
  tipo: string;
  mensagem_recebida?: string;
  mensagem_enviada?: string;
  status?: string;
  created_at: string;
}

export default function Messages() {
  const [logs, setLogs] = useState<MessageLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<MessageLog[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/logs-mensagens`);
      const data = await response.json();
      setLogs(data.logs || []);
      setFilteredLogs(data.logs || []);
    } catch (error) {
      console.error("Erro ao buscar logs:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = logs.filter(
        (log) =>
          log.telefone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.mensagem_recebida?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          log.mensagem_enviada?.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredLogs(filtered);
    } else {
      setFilteredLogs(logs);
    }
  }, [searchTerm, logs]);

  const getStatusBadge = (tipo: string) => {
    if (tipo === "recebida") {
      return <Badge variant="secondary" className="bg-blue-100 text-blue-800"><Inbox className="h-3 w-3 mr-1" /> Recebida</Badge>;
    }
    return <Badge variant="secondary" className="bg-green-100 text-green-800"><Send className="h-3 w-3 mr-1" /> Enviada</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Logs de Mensagens</h1>
          <p className="text-muted-foreground">
            Monitore todas as mensagens enviadas e recebidas via WhatsApp
          </p>
        </div>
        <Button onClick={fetchLogs} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Histórico de Mensagens
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por telefone, mensagem..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Carregando logs...
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm
                ? "Nenhum resultado encontrado"
                : "Nenhuma mensagem registrada ainda"}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data/Hora</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Mensagem</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm">
                      {formatDistanceToNow(new Date(log.created_at), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </TableCell>
                    <TableCell className="font-mono text-sm">{log.telefone}</TableCell>
                    <TableCell>{getStatusBadge(log.tipo)}</TableCell>
                    <TableCell className="text-sm max-w-md truncate">
                      {log.mensagem_enviada || log.mensagem_recebida || "-"}
                    </TableCell>
                    <TableCell>
                      {log.status ? (
                        <Badge variant={log.status === "sucesso" ? "default" : "destructive"}>
                          {log.status}
                        </Badge>
                      ) : (
                        <Badge variant="outline">-</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
