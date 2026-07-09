import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Bell, TrendingUp, Clock, CheckCircle } from "lucide-react";
import { useEffect, useState } from "react";

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

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    try {
      const response = await fetch(`${API_URL}/cobranca-historico`);
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

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">
          Visão geral do sistema de cobrança automática
        </p>
      </div>

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
