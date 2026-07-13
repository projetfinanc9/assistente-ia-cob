import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Bell, TrendingUp, Clock, CheckCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface Stats {
  totalEnvios: number;
  enviadosSucesso: number;
  taxaSucesso: number;
}

const Dashboard = () => {
  const [stats, setStats] = useState<Stats>({
    totalEnvios: 0,
    enviadosSucesso: 0,
    taxaSucesso: 0,
  });
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const params = new URLSearchParams();
      if (dataInicio) params.append("data_inicio", dataInicio);
      if (dataFim) params.append("data_fim", dataFim);
      const qs = params.toString();
      const response = await fetch(`${API_URL}/cobranca-historico${qs ? `?${qs}` : ""}`);
      const data = await response.json();
      const historico = data.historico || [];
      
      const total = historico.length;
      const sucesso = historico.filter((h: any) => h.status === "enviado").length;

      setStats({
        totalEnvios: total,
        enviadosSucesso: sucesso,
        taxaSucesso: total > 0 ? Math.round((sucesso / total) * 100) : 0,
      });
    } catch (error) {
      console.error("Erro ao carregar estatísticas:", error);
    }
  };

  const limpar = () => {
    setDataInicio("");
    setDataFim("");
    setTimeout(loadStats, 0);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">
          Visão geral do sistema de cobrança automática
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <Label htmlFor="dash-inicio" className="text-xs">Data início</Label>
              <Input id="dash-inicio" type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} className="w-40" />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="dash-fim" className="text-xs">Data fim</Label>
              <Input id="dash-fim" type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} className="w-40" />
            </div>
            <Button onClick={loadStats}>Aplicar</Button>
            <Button variant="outline" onClick={limpar}>Limpar</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total de Envios
            </CardTitle>
            <Bell className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalEnvios}</div>
            <p className="text-xs text-muted-foreground">
              {stats.totalEnvios === 0
                ? "Nenhum envio registrado ainda"
                : "Total de cobranças enviadas"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Envios com Sucesso
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.enviadosSucesso}</div>
            <p className="text-xs text-muted-foreground">
              {stats.enviadosSucesso === 0
                ? "Aguardando primeiros envios"
                : "Mensagens entregues com sucesso"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Taxa de Sucesso
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.totalEnvios > 0 ? `${stats.taxaSucesso}%` : "--"}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.totalEnvios === 0
                ? "Dados insuficientes"
                : "Taxa de entrega de mensagens"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Status do Sistema
            </CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">Ativo</div>
            <p className="text-xs text-muted-foreground">
              Sistema operacional
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Atividade Recente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8 text-muted-foreground">
              <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>
                {stats.totalEnvios === 0
                  ? "Nenhum envio registrado ainda"
                  : `${stats.totalEnvios} envios registrados`}
              </p>
              <p className="text-sm mt-2">
                Configure suas regras de cobrança em Configurações de Cobrança
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ações Rápidas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <a
              href="/dashboard/cobranca-config"
              className="block p-4 border rounded-lg hover:bg-muted transition"
            >
              <div className="font-medium">Configurar Cobrança</div>
              <div className="text-sm text-muted-foreground">
                Definir regras de lembretes automáticos
              </div>
            </a>
            <a
              href="/dashboard/history"
              className="block p-4 border rounded-lg hover:bg-muted transition"
            >
              <div className="font-medium">Ver Histórico</div>
              <div className="text-sm text-muted-foreground">
                Consultar todos os envios de cobrança
              </div>
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
